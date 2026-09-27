"""Read all of a skill's input, in windows sized to the model that serves it (D-16, DEC-9).

Skills used to read at most 4,000 characters per task and fit them into a 4,096-token context, so
an analysis of a study read under 1% of it. Here the whole input is read, split at paragraph
boundaries into windows that fit the serving endpoint's context, and every window is labelled
with the file each passage came from, so nuggets keep their provenance and can be grounded in the
exact source span (``services/finding_grounding.py``).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Conservative characters-per-token for sizing windows before the exact token check.
CHARS_PER_TOKEN = 3.2
SOURCE_HEADER = "=== Source: {name} ==="


@dataclass
class SkillCallBudget:
    context_tokens: int
    max_output_tokens: int
    endpoint_id: str = ""
    basis: str = "settings"


@dataclass
class SkillWindow:
    index: int
    text: str
    sources: list[str] = field(default_factory=list)
    source_chars: dict[str, int] = field(default_factory=dict)

    @property
    def source_label(self) -> str:
        return ", ".join(self.sources) if self.sources else "input"


def read_sources(files: list[str]) -> list[tuple[str, str]]:
    """Full text of every readable input file, as (file name, text). Unreadable files are skipped
    and logged; names stay aligned with their own text."""
    from app.core.file_processor import process_file

    sources: list[tuple[str, str]] = []
    for path_str in files or []:
        path = Path(path_str)
        try:
            result = process_file(path)
        except Exception:
            logger.warning("Skill input %s could not be read", path.name, exc_info=True)
            continue
        if result.error or not result.chunks:
            continue
        text = "\n".join(chunk.text for chunk in result.chunks).strip()
        if text:
            sources.append((path.name, text))
    return sources


def resolve_call_budget(project_id: str | None) -> SkillCallBudget:
    """Context and output tokens for one skill call on the endpoint that will serve it.

    The endpoint's declared context window is used up to ``skill_execute_context_ceiling_tokens``
    and never below ``skill_execute_context_limit_tokens`` (the floor for small local models).
    Output may use the endpoint's ``max_tokens`` up to 8,192: reasoning models spend part of it
    thinking, and a short cap empties their answers.
    """
    floor = max(2048, int(settings.skill_execute_context_limit_tokens))
    ceiling = max(floor, int(getattr(settings, "skill_execute_context_ceiling_tokens", 32768)))
    base_output = max(256, int(settings.skill_execute_max_output_tokens))
    try:
        from app.core.pi_runtime.seams import get_pi_execution_service

        # `model_manager` is the engine's accessor method (D-30: read as an attribute, it raised and
        # every skill silently ran on the settings floor).
        manager = get_pi_execution_service().model_manager()
        resolved = manager.resolve(project_id=project_id)
        window = int(getattr(resolved, "context_window", 0) or 0)
        endpoint_max = int(getattr(resolved, "max_tokens", 0) or 0)
        endpoint_id = str(getattr(resolved, "endpoint_id", "") or "")
    except Exception:
        logger.warning(
            "Skill call budget: serving endpoint not resolved; using the settings floor",
            exc_info=True,
        )
        return SkillCallBudget(context_tokens=floor, max_output_tokens=base_output)
    if window <= 0:
        return SkillCallBudget(
            context_tokens=floor, max_output_tokens=base_output, endpoint_id=endpoint_id
        )
    context = max(floor, min(window, ceiling))
    output = base_output
    if endpoint_max > 0:
        output = max(base_output, min(endpoint_max, 8192, context // 4))
    return SkillCallBudget(
        context_tokens=context,
        max_output_tokens=output,
        endpoint_id=endpoint_id,
        basis="endpoint_context_window",
    )


def content_chars(text: str) -> int:
    """Characters that carry content (whitespace excluded), so re-flowed text still counts."""
    return len(re.sub(r"\s+", "", text or ""))


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _split_long(paragraph: str, limit: int) -> list[str]:
    """Split a paragraph longer than the window at sentence ends (hard cut as a last resort)."""
    if len(paragraph) <= limit:
        return [paragraph]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + 1 + len(sentence) > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def plan_windows(sources: list[tuple[str, str]], max_chars: int) -> list[SkillWindow]:
    """Pack labelled paragraphs into windows of at most ``max_chars`` characters, in order.

    Every character of every source lands in exactly one window (paragraph breaks aside), each
    passage under a header naming its file.
    """
    max_chars = max(1000, int(max_chars))
    windows: list[SkillWindow] = []
    current = SkillWindow(index=0, text="")

    def flush() -> None:
        nonlocal current
        if current.text.strip():
            windows.append(current)
        current = SkillWindow(index=len(windows), text="")

    for name, text in sources:
        header = SOURCE_HEADER.format(name=name)
        body_limit = max(500, max_chars - len(header) - 4)
        for paragraph in _paragraphs(text):
            for piece in _split_long(paragraph, body_limit):
                addition = piece if name in current.sources[-1:] else f"{header}\n{piece}"
                needed = len(addition) + 2
                if current.text and len(current.text) + needed > max_chars:
                    flush()
                    addition = f"{header}\n{piece}"
                current.text = f"{current.text}\n\n{addition}" if current.text else addition
                if name not in current.sources:
                    current.sources.append(name)
                current.source_chars[name] = current.source_chars.get(name, 0) + content_chars(
                    piece
                )
    flush()
    return windows


# Output tokens an extraction window needs per character it reads (D-29): nuggets quote the data,
# so the answer grows with the window. Measured on DeepSeek V4 Flash, Harbor Ledger interviews: a
# 6,000-character window took 5,626 output tokens; 12,000 characters overran the 8,192-token answer.
EXTRACTION_CHARS_PER_OUTPUT_TOKEN = 0.8


def extraction_char_budget(budget: SkillCallBudget, static_tokens: int) -> int:
    """Characters one extraction window may hold: what fits the context AND whose nuggets fit the
    model's output budget. More, smaller windows beat one window whose answer is cut off."""
    by_output = int(budget.max_output_tokens * EXTRACTION_CHARS_PER_OUTPUT_TOKEN)
    return max(1000, min(window_char_budget(budget, static_tokens), by_output))


def window_char_budget(budget: SkillCallBudget, static_tokens: int) -> int:
    """Characters of research data one call can carry after the prompt, schema and output."""
    data_tokens = budget.context_tokens - budget.max_output_tokens - static_tokens - 256
    return max(1000, int(data_tokens * CHARS_PER_TOKEN * 0.9))


def nuggets_as_evidence(nuggets: list[dict], limit_chars: int) -> str:
    """The merged window nuggets, labelled by source, as the input of the synthesis pass."""
    lines = []
    total = 0
    for index, nugget in enumerate(nuggets, start=1):
        line = f"[{index}] ({nugget.get('source') or 'input'}) {nugget.get('text', '').strip()}"
        if total + len(line) > limit_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def merge_window_data(datas: list[dict]) -> dict:
    """Merge per-window JSON answers: lists are concatenated, texts joined, first scalar kept."""
    merged: dict = {}
    for data in datas:
        for key, value in (data or {}).items():
            if isinstance(value, list):
                merged.setdefault(key, []).extend(value)
            elif isinstance(value, str):
                if value and value not in merged.get(key, ""):
                    merged[key] = f"{merged[key]} {value}".strip() if key in merged else value
            else:
                merged.setdefault(key, value)
    return merged


async def analyse_in_windows(
    skill_input,
    *,
    build_prompt,
    schema: dict,
    empty_label: str,
) -> tuple[dict, list[tuple[str, list[dict]]], dict]:
    """Run one structured analysis per window of the input (the custom discover skills).

    Returns the merged answer, each window's nuggets with the window's source label, and a
    coverage report. ``build_prompt(text)`` renders the skill's own prompt around one window.
    """
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    sources = read_sources(skill_input.files) if skill_input.files else []
    if not sources and skill_input.user_context:
        sources = [(empty_label, skill_input.user_context)]
    budget = resolve_call_budget(skill_input.project_id)
    windows = plan_windows(sources, extraction_char_budget(budget, 1500))
    datas, labelled = [], []
    failed = 0
    for window in windows:
        try:
            outcome = await agentic.structured(
                purpose="skill.discover_analyze",
                project_id=skill_input.project_id,
                system=None,
                messages=[{"role": "user", "content": build_prompt(window.text)}],
                schema=schema,
                params=TurnParams(temperature=0.3, max_tokens=budget.max_output_tokens),
                spine_phase="synthesis",
            )
            data = outcome.value if outcome.status == "success" and outcome.value else {}
        except Exception as exc:  # a failed window is reported, never silently skipped
            logger.warning("Window %s of %s failed: %s", window.index + 1, len(windows), exc)
            data = {}
        if not data:
            failed += 1
        datas.append(data)
        labelled.append((window.source_label, list(data.get("nuggets", []))))
    total = sum(content_chars(text) for _, text in sources)
    delivered = sum(sum(w.source_chars.values()) for w in windows)
    coverage = {
        "source_files": len(sources),
        "source_chars": total,
        "delivered_chars": delivered,
        "coverage": round(delivered / total, 4) if total else None,
        "windows": len(windows),
        "windows_failed": failed,
        "context_tokens": budget.context_tokens,
        "budget_basis": budget.basis,
    }
    return merge_window_data(datas), labelled, coverage


def estimated_calls(files: list[str], project_id: str | None) -> int:
    """How many model calls reading these files will take (windows plus one synthesis)."""
    import os

    total = 0
    for path in files or []:
        try:
            total += os.path.getsize(path)
        except OSError:
            continue
    per_window = extraction_char_budget(resolve_call_budget(project_id), 1500)
    return max(1, -(-total // per_window)) + 1


def scaled_timeout(base_seconds: float, files: list[str], project_id: str | None) -> float:
    """A skill's wall-clock budget grows with the calls it must make; each call keeps its own
    liveness in the runtime, so a long, steadily progressing analysis is never cut off early."""
    return float(base_seconds) * estimated_calls(files, project_id)


SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "supporting_nuggets": {"type": "array", "items": {"type": "number"}},
                },
            },
        },
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "supporting_facts": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
                },
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "supporting_insights": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string"},
                    "effort": {"type": "string"},
                },
            },
        },
    },
    "required": [],
}

SYNTHESIS_PROMPT = """You are an expert UX researcher synthesising the findings of a {method}.

The evidence nuggets below were extracted from the source data; each is numbered and names the
file it came from. Use only them: every fact must rest on nuggets you cite by number, every insight
on facts, every recommendation on insights. Do not add claims the nuggets do not support.

{analysis}<nuggets>
{nuggets}
</nuggets>

Return JSON:
{{"facts": [{{"text": "...", "supporting_nuggets": [1, 2]}}],
"insights": [{{"text": "...", "supporting_facts": ["fact text"], "confidence": "high|medium|low"}}],
"recommendations": [{{"text": "...", "supporting_insights": ["insight text"],
"priority": "low|medium|high|critical", "effort": "low|medium|high"}}]}}"""


async def synthesise_findings(
    skill_input, *, method: str, nuggets: list[dict], analysis: dict | None = None
) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Facts, insights and recommendations over a skill's labelled nuggets (SK1).

    Used by the custom discover skills, which extract nuggets per window but promised findings
    too. The synthesis sees only the nuggets (and a compact copy of the skill's own analysis),
    so what it concludes stays tied to evidence. Returns (facts, insights, recommendations,
    errors); a failed call returns no findings and says so, never invented ones.
    """
    if not nuggets:
        return [], [], [], []
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    budget = resolve_call_budget(skill_input.project_id)
    limit = window_char_budget(budget, 1200)
    extra = ""
    if analysis:
        compact = json.dumps(
            {k: v for k, v in analysis.items() if k not in ("nuggets", "summary") and v},
            indent=1,
        )[: limit // 4]
        if compact and compact != "{}":
            extra = f"The skill's own analysis of the data (for context):\n{compact}\n\n"
    prompt = SYNTHESIS_PROMPT.format(
        method=method,
        analysis=extra,
        nuggets=nuggets_as_evidence(nuggets, limit - len(extra)),
    )
    try:
        outcome = await agentic.structured(
            purpose="skill.discover_analyze",
            project_id=skill_input.project_id,
            system=None,
            messages=[{"role": "user", "content": prompt}],
            schema=SYNTHESIS_SCHEMA,
            params=TurnParams(temperature=0.3, max_tokens=budget.max_output_tokens),
            spine_phase="synthesis",
        )
        data = outcome.value if outcome.status == "success" and outcome.value else {}
    except Exception as exc:  # reported, never replaced by invented findings
        logger.warning("Synthesis failed: %s", exc)
        return [], [], [], [f"synthesis: {exc}"]
    if not data:
        return [], [], [], ["synthesis: the model returned no findings"]
    facts = [
        {"text": f["text"], "supporting_nuggets": f.get("supporting_nuggets", [])}
        for f in data.get("facts", [])
        if f.get("text")
    ]
    insights = [
        {
            "text": i["text"],
            "confidence": i.get("confidence", "medium"),
            "supporting_facts": i.get("supporting_facts", []),
        }
        for i in data.get("insights", [])
        if i.get("text")
    ]
    recommendations = [
        {
            "text": r["text"],
            "priority": r.get("priority", "medium"),
            "effort": r.get("effort", "medium"),
            "supporting_insights": r.get("supporting_insights", []),
        }
        for r in data.get("recommendations", [])
        if r.get("text")
    ]
    return facts, insights, recommendations, []
