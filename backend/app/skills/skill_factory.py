"""Skill factory — generate skills from configuration to reduce boilerplate.

Each skill has the same core pattern:
1. plan() — generate a research plan using LLM
2. execute() — process input files + context, extract findings using LLM
3. validate_output() — check quality

This factory creates concrete skill classes from config dicts.
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.ollama import ollama
from app.core.file_processor import process_file
from app.core.llm_schema_adapter import (
    SchemaBudgetResult,
    extract_json_schema,
    openai_json_schema_response_format,
    parse_json_object,
    strip_thinking_markers,
)
from app.core.token_counter import count_tokens
from app.skills.base import BaseSkill, SkillInput, SkillOutput, SkillPhase, SkillType

logger = logging.getLogger(__name__)


_JSON_SCHEMA_TYPES = {
    "array",
    "boolean",
    "integer",
    "null",
    "number",
    "object",
    "string",
}


def _looks_like_json_schema(schema: dict[str, Any]) -> bool:
    """Return True for actual JSON Schema nodes, not examples with a ``type`` field."""
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        return schema_type in _JSON_SCHEMA_TYPES
    if isinstance(schema_type, list):
        return all(item in _JSON_SCHEMA_TYPES for item in schema_type)
    return False


def _truncate_to_token_budget(text: str, token_budget: int, *, suffix: str = "\n...[truncated]") -> str:
    """Approximate token-budget truncation without adding a heavy tokenizer dependency."""
    if token_budget <= 0 or count_tokens(text) <= token_budget:
        return text
    char_budget = max(0, token_budget * 4 - len(suffix))
    return text[:char_budget].rstrip() + suffix


def _make_schema_strict(schema: Any) -> dict:
    """Transform JSON Schema (or example object) to strict mode for local LLMs.
    
    If the input is already a JSON Schema (has 'type'), it adds 'additionalProperties': False
    and 'required' arrays to every object.
    
    If the input is an example object (e.g. {"key": "value"}), it recursively 
    translates it into a valid JSON Schema with strict constraints.
    """
    if not isinstance(schema, (dict, list)):
        # Base case: map python type to JSON schema type
        if isinstance(schema, bool):
            return {"type": "boolean"}
        if isinstance(schema, int):
            return {"type": "integer"}
        if isinstance(schema, float):
            return {"type": "number"}
        return {"type": "string"}

    if isinstance(schema, list):
        # Example array or Schema array
        if len(schema) > 0 and isinstance(schema[0], dict) and "type" in schema[0]:
            # It's a schema array
            return {
                "type": "array",
                "items": _make_schema_strict(schema[0])
            }
        else:
            # It's an example array
            item_example = schema[0] if len(schema) > 0 else "..."
            return {
                "type": "array",
                "items": _make_schema_strict(item_example)
            }

    if isinstance(schema, dict):
        # Check if it's already a JSON Schema
        if _looks_like_json_schema(schema):
            new_schema = schema.copy()
            if new_schema["type"] == "object":
                new_schema["additionalProperties"] = False
                properties = new_schema.get("properties", {})
                required = new_schema.get("required", [])
                
                new_required = list(properties.keys())
                new_properties = {}
                
                for prop_name, prop_schema in properties.items():
                    prop_schema_strict = _make_schema_strict(prop_schema)
                    # Handle optional fields (if they weren't in the original required list)
                    if prop_name not in required:
                        if "type" in prop_schema_strict and isinstance(prop_schema_strict["type"], str):
                            original_type = prop_schema_strict.pop("type")
                            prop_schema_strict["anyOf"] = [{"type": original_type}, {"type": "null"}]
                    new_properties[prop_name] = prop_schema_strict
                
                new_schema["properties"] = new_properties
                new_schema["required"] = new_required
            elif new_schema["type"] == "array":
                if "items" in new_schema:
                    new_schema["items"] = _make_schema_strict(new_schema["items"])
            return new_schema
        
        # It's an example object — translate to Schema
        new_properties = {}
        new_required = []
        for k, v in schema.items():
            new_properties[k] = _make_schema_strict(v)
            new_required.append(k)
            
        return {
            "type": "object",
            "properties": new_properties,
            "required": new_required,
            "additionalProperties": False
        }
    
    return {"type": "string"}


_PI_SCHEMA_KEYS = frozenset({
    "type", "properties", "required", "items", "enum", "const",
    "additionalProperties", "description",
})


def _pi_dispatch_schema(schema: Any) -> dict:
    """Simplify a strict JSON schema into the Pi forced-tool subset.

    ``_make_schema_strict`` can emit constructs the Pi engine rejects before
    any model call (``anyOf`` null-unions for optional fields, ``null`` type
    unions); collapse those and drop unsupported keys so a schema the legacy
    ``response_format`` path accepts stays dispatchable. Root stays an object.
    """
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    node = dict(schema)
    union = node.pop("anyOf", None)
    if isinstance(union, list):
        for branch in union:
            if isinstance(branch, dict) and branch.get("type") != "null":
                node.update(branch)
                break
    node_type = node.get("type")
    if isinstance(node_type, list):
        node["type"] = next((t for t in node_type if t != "null"), "string")
    out = {k: v for k, v in node.items() if k in _PI_SCHEMA_KEYS}
    if "additionalProperties" in out and not isinstance(out["additionalProperties"], bool):
        del out["additionalProperties"]
    if isinstance(out.get("properties"), dict):
        out["properties"] = {k: _pi_dispatch_schema(v) for k, v in out["properties"].items()}
    if isinstance(out.get("items"), dict):
        out["items"] = _pi_dispatch_schema(out["items"])
    if "type" not in out:
        out["type"] = "object" if "properties" in out else "string"
    return out


def _normalized_skill_output_response_format(skill_name: str) -> dict:
    """Return the compact schema Istara needs to normalize candidate skill results."""
    return openai_json_schema_response_format(
        name=f"{skill_name.replace('-', '_')}_normalized_output",
        schema=_make_schema_strict(
            {
                "summary": "...",
                "nuggets": [{"text": "...", "source": "...", "tags": ["..."]}],
                "facts": [{"text": "..."}],
                "insights": [{"text": "...", "confidence": "medium"}],
                "recommendations": [{"text": "...", "priority": "medium"}],
                "suggestions": ["..."],
            }
        ),
        strict=True,
    )


def _extract_text_from_files(files: list[str], max_chars: int = 4000) -> str:
    """Extract text from input files."""
    texts = []
    total = 0
    for f in files:
        result = process_file(Path(f))
        if not result.error and result.chunks:
            for chunk in result.chunks:
                if total + len(chunk.text) > max_chars:
                    break
                texts.append(chunk.text)
                total += len(chunk.text)
    return "\n\n".join(texts)


def _parse_json_response(text: str) -> dict:
    """Try to extract JSON from an LLM response."""
    return parse_json_object(text) or {}


def _format_prompt_template(template: str, **values: str) -> str:
    """Substitute Istara prompt tokens without interpreting literal braces.

    Skill definitions often include JSON examples, formulas, or tags such as
    ``ux-law:{id}``. Python ``str.format`` treats those as replacement fields,
    so generated skills must only replace the runtime tokens Istara owns.
    """
    formatted = template
    for key, value in values.items():
        formatted = formatted.replace("{" + key + "}", value)
    return formatted


def _compact_text(value: Any, *, limit: int = 320) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, (int, float, bool)):
        text = str(value)
    else:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except TypeError:
            text = str(value)
    return " ".join(text.split())[:limit].strip()


def _list_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_generated_findings(
    data: dict[str, Any],
    *,
    source_label: str,
    item_limit: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Map skill-specific JSON schemas into Istara's shared finding chain."""

    def as_dict(item: Any, default_key: str = "text") -> dict[str, Any]:
        return item if isinstance(item, dict) else {default_key: str(item)}

    nuggets = [
        {
            "text": _compact_text(as_dict(n).get("text", str(n))),
            "source": _compact_text(as_dict(n).get("source", source_label), limit=120) or source_label,
            "tags": as_dict(n).get("tags", []),
        }
        for n in _list_items(data.get("nuggets"))
    ]
    facts = [
        {"text": _compact_text(as_dict(f).get("text", str(f)))}
        for f in _list_items(data.get("facts"))
    ]
    insights = [
        {
            "text": _compact_text(as_dict(i).get("text", str(i))),
            "confidence": _compact_text(as_dict(i).get("confidence", "medium"), limit=40) or "medium",
        }
        for i in _list_items(data.get("insights"))
    ]
    recommendations = [
        {
            "text": _compact_text(as_dict(r).get("text", str(r))),
            "priority": _compact_text(as_dict(r).get("priority", "medium"), limit=40) or "medium",
        }
        for r in _list_items(data.get("recommendations"))
    ]

    if not nuggets:
        for insight in _list_items(data.get("source_insights")):
            item = as_dict(insight)
            for evidence in _list_items(item.get("evidence"))[:item_limit]:
                text = _compact_text(evidence)
                if text:
                    nuggets.append({"text": text, "source": source_label, "tags": ["source-insight"]})
        for metric in _list_items(data.get("metrics")):
            item = as_dict(metric)
            points = _list_items(item.get("data_points"))
            if points:
                sample = ", ".join(_compact_text(point, limit=80) for point in points[:2])
                metric_name = _compact_text(item.get("metric_name") or item.get("metric_id"), limit=120)
                if sample:
                    nuggets.append({
                        "text": f"{metric_name or 'Metric'} observed data points: {sample}",
                        "source": source_label,
                        "tags": ["metric-data"],
                    })

    if not facts:
        for insight in _list_items(data.get("source_insights")):
            item = as_dict(insight)
            text = _compact_text(item.get("text") or item.get("finding"))
            if text:
                count = item.get("data_point_count")
                suffix = f" ({count} supporting data points)" if count not in (None, "") else ""
                facts.append({"text": f"{text}{suffix}"})
        heart = data.get("heart_scorecard")
        if isinstance(heart, dict):
            for category, item in heart.items():
                metric = as_dict(item)
                metric_name = _compact_text(metric.get("primary_metric"), limit=120)
                trend = _compact_text(metric.get("trend"), limit=40)
                health = _compact_text(metric.get("health"), limit=40)
                if metric_name or trend or health:
                    facts.append({
                        "text": (
                            f"HEART {category} tracks {metric_name or 'a primary metric'}"
                            f" with trend={trend or 'unknown'} and health={health or 'unknown'}."
                        )
                    })
        for metric in _list_items(data.get("metrics")):
            item = as_dict(metric)
            metric_name = _compact_text(item.get("metric_name") or item.get("metric_id"), limit=120)
            trend = as_dict(item.get("trend", {}))
            direction = _compact_text(trend.get("direction"), limit=40)
            if metric_name or direction:
                facts.append({"text": f"{metric_name or 'Metric'} trend is {direction or 'reported'}."})

    if not insights:
        for insight in _list_items(data.get("source_insights")):
            item = as_dict(insight)
            text = _compact_text(item.get("text") or item.get("finding"))
            if text:
                insights.append({
                    "text": text,
                    "confidence": _compact_text(item.get("confidence"), limit=40) or "medium",
                })
        for hmw in _list_items(data.get("hmw_statements"))[:item_limit]:
            item = as_dict(hmw)
            statement = _compact_text(item.get("statement") or item.get("text"))
            cluster = _compact_text(item.get("cluster"), limit=120)
            if statement:
                insights.append({
                    "text": f"{statement}" + (f" Opportunity cluster: {cluster}." if cluster else ""),
                    "confidence": "medium",
                })
        for regression in _list_items(data.get("regressions")):
            item = as_dict(regression)
            metric = _compact_text(item.get("metric"), limit=120)
            severity = _compact_text(item.get("severity"), limit=40)
            magnitude = _compact_text(item.get("magnitude_pct"), limit=40)
            if metric or severity:
                insights.append({
                    "text": f"{metric or 'Metric'} regression severity={severity or 'reported'}, magnitude={magnitude or 'n/a'}.",
                    "confidence": "medium",
                })
        for key in ("findings", "opportunities", "pain_points", "themes", "patterns"):
            for item in _list_items(data.get(key)):
                entry = as_dict(item)
                text = _compact_text(
                    entry.get("text") or entry.get("description") or entry.get("name") or entry
                )
                if text:
                    insights.append({"text": text, "confidence": "medium"})

    if not recommendations:
        for top in _list_items(data.get("prioritized_top_5")):
            item = as_dict(top)
            statement = _compact_text(item.get("statement") or item.get("hmw_id"))
            rationale = _compact_text(item.get("rationale"))
            if statement:
                recommendations.append({
                    "text": f"Use this HMW for ideation: {statement}" + (f" Rationale: {rationale}" if rationale else ""),
                    "priority": "high",
                })
        for regression in _list_items(data.get("regressions")):
            item = as_dict(regression)
            metric = _compact_text(item.get("metric"), limit=120)
            status = _compact_text(item.get("investigation_status"), limit=80)
            if metric:
                recommendations.append({
                    "text": f"Investigate the {metric} regression" + (f" ({status})." if status else "."),
                    "priority": _compact_text(item.get("severity"), limit=40) or "medium",
                })

    return (
        [item for item in nuggets if item.get("text")][:item_limit],
        [item for item in facts if item.get("text")][:item_limit],
        [item for item in insights if item.get("text")][:item_limit],
        [item for item in recommendations if item.get("text")][:item_limit],
    )


def _deterministic_findings_from_research_data(
    research_data: str,
    *,
    display: str,
    source_label: str,
    item_limit: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Last-resort evidence fallback when the model returns empty findings."""

    lines = [line.strip() for line in (research_data or "").splitlines() if line.strip()]
    if not lines:
        return [], [], [], []

    header = lines[0]
    rows = lines[1:]
    columns = [part.strip() for part in header.split(",") if part.strip()] if "," in header else []
    representative = next((line for line in rows if line and not line.startswith("#")), lines[0])

    nuggets = [
        {
            "text": _compact_text(representative, limit=360),
            "source": source_label,
            "tags": ["deterministic-fallback"],
        }
    ]
    facts = []
    if columns:
        facts.append(
            {
                "text": (
                    f"Input for {display} contains {len(rows)} data row(s) with columns: "
                    f"{', '.join(columns[:8])}."
                )
            }
        )
    else:
        facts.append({"text": f"Input for {display} contains {len(lines)} non-empty evidence line(s)."})

    has_date_column = any(col.lower() in {"date", "timestamp", "week", "month"} for col in columns)
    if has_date_column and len(rows) < 6:
        insight_text = (
            f"{display} received time-indexed data, but only {len(rows)} row(s); "
            "trend and anomaly claims should be treated as preliminary."
        )
        recommendation_text = (
            "Collect at least 6-12 comparable time periods before relying on trend, "
            "control-chart, or seasonality conclusions."
        )
    else:
        insight_text = (
            f"{display} has usable input evidence, but the model returned no normalized findings; "
            "the fallback preserved the available evidence for review."
        )
        recommendation_text = "Review the source data and rerun the skill if deeper model synthesis is required."

    insights = [{"text": insight_text, "confidence": "low"}]
    recommendations = [{"text": recommendation_text, "priority": "medium"}]
    return nuggets[:item_limit], facts[:item_limit], insights[:item_limit], recommendations[:item_limit]


def _fallback_plan(
    *,
    skill_name: str,
    display: str,
    desc: str,
    phase: SkillPhase,
    context: str,
) -> str:
    """Build a deterministic plan when the LLM cannot provide one."""
    scoped_context = (context or "General UX research").strip()
    return (
        f"# {display} Plan\n\n"
        f"Skill: `{skill_name}`\n"
        f"Phase: `{phase.value}`\n\n"
        f"Objective: {desc}\n\n"
        f"Context: {scoped_context[:500]}\n\n"
        "1. Confirm the research question, available evidence, and decision to support.\n"
        "2. Review the supplied artifacts and separate direct observations from interpretation.\n"
        "3. Extract evidence-backed findings with source labels and confidence notes.\n"
        "4. Synthesize patterns into actionable insights and recommendations.\n"
        "5. Report limitations, missing data, and next validation steps."
    )


def create_skill(
    skill_name: str,
    display: str,
    desc: str,
    phase: SkillPhase,
    skill_type: SkillType,
    plan_prompt: str,
    execute_prompt: str,
    output_schema: str,
) -> type[BaseSkill]:
    """Create a concrete skill class from configuration.

    Args:
        skill_name: Unique identifier (e.g., 'competitive-analysis')
        display: Human name (e.g., 'Competitive Analysis')
        desc: Description of what the skill does
        phase: Double Diamond phase
        skill_type: Qual/quant/mixed
        plan_prompt: Prompt template for plan(). Uses {context}, {user_context}
        execute_prompt: Prompt template for execute(). Uses {context}, {content}
        output_schema: JSON schema description appended to execute_prompt
    """

    class GeneratedSkill(BaseSkill):
        @property
        def name(self) -> str:
            return skill_name

        @property
        def display_name(self) -> str:
            return display

        @property
        def description(self) -> str:
            return desc

        @property
        def phase(self) -> SkillPhase:
            return phase

        @property
        def skill_type(self) -> SkillType:
            return skill_type

        async def plan(self, skill_input: SkillInput) -> dict:
            ctx = skill_input.project_context or skill_input.user_context or "General UX research"
            urls_str = ", ".join(skill_input.urls) if skill_input.urls else ""
            prompt = _format_prompt_template(
                plan_prompt,
                context=ctx,
                user_context=skill_input.user_context or "",
                urls=urls_str,
            )
            fallback = _fallback_plan(
                skill_name=self.name,
                display=self.display_name,
                desc=self.description,
                phase=self.phase,
                context=ctx,
            )
            try:
                if settings.agentic_core:
                    # W5: the plan call goes through the AgenticDispatcher
                    # (``skill.plan``); the legacy branch below is preserved
                    # for agentic_core=False.
                    from app.core.agentic import agentic
                    from app.core.agentic.types import TurnParams

                    outcome = await agentic.completion(
                        purpose="skill.plan",
                        project_id=skill_input.project_id,
                        system=None,
                        messages=[{"role": "user", "content": prompt}],
                        params=TurnParams(temperature=0.7, thinking_mode="off"),
                        spine_phase="plan",
                    )
                    plan = (outcome.text or "").strip()
                else:
                    resp = await ollama.chat(
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        thinking_mode="off",
                    )
                    plan = (resp.get("message", {}).get("content", "") or "").strip()
            except Exception as e:
                logger.warning("Skill %s plan fell back after LLM failure: %s", self.name, e)
                return {"skill": self.name, "plan": fallback, "fallback": True}

            if not plan:
                logger.warning("Skill %s plan fell back after empty LLM response.", self.name)
                return {"skill": self.name, "plan": fallback, "fallback": True}

            return {"skill": self.name, "plan": plan}

        async def execute(self, skill_input: SkillInput) -> SkillOutput:
            content = _extract_text_from_files(skill_input.files) if skill_input.files else ""
            if not content and not skill_input.user_context and not skill_input.urls:
                return SkillOutput(
                    success=False,
                    summary="No input provided.",
                    errors=["Provide files, context, or URLs."],
                )

            file_sources = [Path(f).name for f in skill_input.files] if skill_input.files else []
            source_label = ", ".join(file_sources[:3]) if file_sources else self.name

            ctx = "\n".join(
                filter(
                    None,
                    [
                        skill_input.company_context,
                        skill_input.project_context,
                        skill_input.user_context,
                    ],
                )
            )
            data_content = content or (skill_input.user_context or "N/A")[:10000]

            # SOTA Prompt Construction (Anthropic/OpenAI hybrid)
            methodology = _format_prompt_template(
                execute_prompt,
                context=(ctx or "N/A")[:2000],
                content="[RESEARCH_DATA_BELOW]",
                urls=", ".join(skill_input.urls) if skill_input.urls else "",
                urls_section="",
            )

            # Try to parse schema as dict for native support. When native
            # structured output is available, avoid duplicating the full schema
            # in the text prompt; large schemas slow local models dramatically.
            schema_dict = None
            max_schema_tokens = max(256, int(settings.skill_execute_max_schema_tokens))
            schema_budget = SchemaBudgetResult(
                schema_name=f"{self.name.replace('-', '_')}_output",
                schema_tokens=0,
                max_schema_tokens=max_schema_tokens,
                used_fallback=False,
                reason="no-json-schema",
            )
            try:
                parsed_schema = json.loads(output_schema)
                strict_schema = _make_schema_strict(parsed_schema)
                schema_dict = openai_json_schema_response_format(
                    name=f"{self.name.replace('-', '_')}_output",
                    schema=strict_schema,
                    strict=True,
                )
            except Exception as e:
                logger.warning(f"Skill {self.name} failed to prepare strict schema: {e}")

            if schema_dict:
                schema_token_count = count_tokens(json.dumps(schema_dict, ensure_ascii=False))
                schema_budget = SchemaBudgetResult(
                    schema_name=schema_dict.get("json_schema", {}).get("name", self.name),
                    schema_tokens=schema_token_count,
                    max_schema_tokens=max_schema_tokens,
                    used_fallback=False,
                    reason="full-schema-within-budget",
                )
                if schema_token_count > max_schema_tokens:
                    logger.info(
                        "Skill %s schema is %s tokens; using normalized output schema for local execution.",
                        self.name,
                        schema_token_count,
                    )
                    schema_dict = _normalized_skill_output_response_format(self.name)
                    schema_budget = SchemaBudgetResult(
                        schema_name=schema_dict.get("json_schema", {}).get("name", self.name),
                        schema_tokens=schema_token_count,
                        max_schema_tokens=max_schema_tokens,
                        used_fallback=True,
                        reason="schema-token-budget-exceeded",
                    )

            item_limit = max(1, int(settings.skill_execute_item_limit))
            if schema_dict:
                output_contract = (
                    "A native JSON schema is attached to this request. Return ONLY a valid JSON object; "
                    "do not include markdown, prose, or thinking text outside JSON. Use this compact shape "
                    "when the schema allows it:\n"
                    "{\n"
                    '  "summary": "...",\n'
                    '  "nuggets": [{"text": "...", "source": "...", "tags": ["..."]}],\n'
                    '  "facts": [{"text": "..."}],\n'
                    '  "insights": [{"text": "...", "confidence": "high|medium|low"}],\n'
                    '  "recommendations": [{"text": "...", "priority": "critical|high|medium|low"}],\n'
                    '  "suggestions": ["..."]\n'
                    "}\n"
                    "Keep arrays concise: at most "
                    f"{item_limit} nuggets, {item_limit} facts, {item_limit} insights, "
                    f"and {item_limit} recommendations unless the data clearly requires fewer. "
                    "All returned findings are candidate/provisional Research Spine artifacts, not accepted "
                    "or reportable evidence."
                )
            else:
                output_contract = output_schema[: settings.skill_schema_prompt_char_limit]

            repair_response_format = _normalized_skill_output_response_format(self.name)

            def _build_full_prompt(research_data: str, methodology_text: str) -> str:
                return (
                    f"<skill_context>\n"
                    f"Name: {self.name}\n"
                    f"Description: {self.description}\n"
                    f"Phase: {self.phase.value}\n"
                    f"</skill_context>\n\n"
                    f"<research_methodology>\n"
                    f"{methodology_text}\n"
                    f"</research_methodology>\n\n"
                    f"<research_data>\n"
                    f"{research_data}\n"
                    f"</research_data>\n\n"
                    f"<research_spine_contract>\n"
                    f"Sources and exact source spans come before trusted Atomic Research. "
                    f"Return only candidate/provisional atoms, facts, insights, and recommendations. "
                    f"Do not present documents -> nuggets -> facts -> insights as trusted before "
                    f"independent extraction/coding, reliability/reconciliation, and Done-task gates. "
                    f"Every candidate nugget should include a source, quote/span/location when available, "
                    f"and code-ready tags for later independent coding.\n"
                    f"</research_spine_contract>\n\n"
                    f"<instructions>\n"
                    f"1. **Think First**: Analyze the research data against the methodology privately.\n"
                    f"2. **Propose Candidate Evidence**: Find exact source quotes/spans and mark them as provisional.\n"
                    f"3. **Propose Candidate Synthesis**: Derive candidate facts, insights, and recommendations only from those spans.\n"
                    f"4. **Format**: Respond only with a valid JSON object matching the output contract.\n"
                    f"5. **Do Not Promote**: Do not describe any artifact as accepted, trusted, or reportable.\n"
                    f"6. **Be concise**: Prefer the strongest evidence and avoid exhaustive lists.\n"
                    f"</instructions>\n\n"
                    f"## Output Contract\n"
                    f"{output_contract}"
                )

            system_prompt = (
                "You are a meticulous UX Research Auditor. You prioritize evidence over assumption. "
                "Your skill output is candidate/provisional until Istara's Research Spine accepts it."
            )
            skill_context_limit = min(
                max(settings.max_context_tokens, 2048),
                max(2048, settings.skill_execute_context_limit_tokens),
            )
            max_output_tokens = max(256, int(settings.skill_execute_max_output_tokens))

            static_prompt = _build_full_prompt("", methodology)
            schema_tokens = (
                count_tokens(json.dumps(schema_dict, ensure_ascii=False))
                if schema_dict
                else 0
            )
            static_tokens = (
                count_tokens(static_prompt)
                + count_tokens(system_prompt)
                + max_output_tokens
                + schema_tokens
            )
            if static_tokens > skill_context_limit:
                methodology_budget = max(
                    256,
                    count_tokens(methodology) - (static_tokens - skill_context_limit) - 64,
                )
                methodology = _truncate_to_token_budget(
                    methodology,
                    methodology_budget,
                    suffix="\n...[methodology truncated to fit local context budget]",
                )

            static_prompt = _build_full_prompt("", methodology)
            static_tokens = (
                count_tokens(static_prompt)
                + count_tokens(system_prompt)
                + max_output_tokens
                + schema_tokens
            )
            data_budget_tokens = max(128, skill_context_limit - static_tokens)
            data_content = _truncate_to_token_budget(
                data_content,
                data_budget_tokens,
                suffix="\n...[research data truncated to fit local context budget]",
            )

            full_prompt = _build_full_prompt(data_content, methodology)
            estimated_context_tokens = (
                count_tokens(full_prompt)
                + count_tokens(system_prompt)
                + max_output_tokens
                + schema_tokens
            )

            if settings.agentic_core:
                # W5: skill execution dispatches structured output through the
                # AgenticDispatcher (``skill.execute``) — repair=False because
                # the 4-stage fallback chain below is the resilience contract
                # and the Pi engine must not double-repair inside it. The
                # legacy branch is preserved for agentic_core=False.
                from app.core.agentic import agentic
                from app.core.agentic.types import TurnParams

                try:
                    outcome = await agentic.structured(
                        purpose="skill.execute",
                        project_id=skill_input.project_id,
                        system=system_prompt,
                        messages=[{"role": "user", "content": full_prompt}],
                        schema=_pi_dispatch_schema(
                            extract_json_schema(schema_dict)
                            or extract_json_schema(repair_response_format)
                        ),
                        params=TurnParams(
                            temperature=0.2,
                            max_tokens=max_output_tokens,
                            min_context=estimated_context_tokens,
                            thinking_mode="off",
                        ),
                        repair=False,
                        spine_phase="execution",
                    )
                    raw_content = outcome.text
                    data = outcome.value if outcome.status == "success" else None
                except Exception as e:
                    # F-W5-1: on the Pi engine, run_structured(repair=False)
                    # raises PiRuntimeTurnError on the first invalid/missing
                    # structured output instead of returning status != "success".
                    # Degrade into the 4-stage fallback chain below (the
                    # product's resilience contract) with empty raw content;
                    # the repair stages are already individually guarded.
                    logger.warning(
                        "Skill %s primary structured call raised; entering repair fallback chain: %s",
                        self.name,
                        e,
                    )
                    raw_content = ""
                    data = None
            else:
                resp = await ollama.chat(
                    messages=[{"role": "user", "content": full_prompt}], 
                    temperature=0.2, # Lower temperature for analytical rigor
                    max_tokens=max_output_tokens,
                    response_format=schema_dict, # Enable native structured outputs
                    system=system_prompt,
                    min_context=estimated_context_tokens,
                    thinking_mode="off",
                )
                
                raw_content = resp.get("message", {}).get("content", "")
                data = None
            
            # Remove thinking tags from JSON parsing if model included them outside JSON
            clean_content = strip_thinking_markers(raw_content)
            
            json_success = False
            repaired_from_non_json = False
            repaired_content = ""
            plain_repair_content = ""
            data = data or _parse_json_response(clean_content)
            if data:
                json_success = True
            else:
                use_native_repair = (settings.llm_provider or "").strip().lower() not in {"lmstudio"}
                if use_native_repair:
                    repair_prompt = (
                        "Convert the failed skill response below into one valid JSON object for Istara.\n"
                        "Return ONLY JSON. Do not include markdown fences, comments, prose, or thinking text.\n"
                        "Use only evidence present in the failed response and research data sample. "
                        "When evidence for an array is missing, return an empty array instead of inventing details.\n\n"
                        f"Skill: {self.name}\n"
                        f"Display name: {display}\n"
                        f"Description: {self.description}\n"
                        f"Required compact output contract:\n{output_contract[:2000]}\n\n"
                        f"Failed response:\n{(raw_content or '[empty response]')[:6000]}\n\n"
                        f"Research data sample:\n{data_content[:3000]}"
                    )
                    try:
                        if settings.agentic_core:
                            # W5: native JSON repair dispatches through the
                            # AgenticDispatcher (``skill.repair_native``) with
                            # repair=False — this stage IS the repair, so the
                            # Pi engine must not run its own bounded repair
                            # inside the fallback chain. Legacy branch preserved.
                            from app.core.agentic import agentic
                            from app.core.agentic.types import TurnParams

                            repair_system = (
                                "You are a strict JSON repair adapter. "
                                "Your entire response must be one valid JSON object."
                            )
                            repair_outcome = await agentic.structured(
                                purpose="skill.repair_native",
                                project_id=skill_input.project_id,
                                system=repair_system,
                                messages=[{"role": "user", "content": repair_prompt}],
                                schema=_pi_dispatch_schema(extract_json_schema(repair_response_format)),
                                params=TurnParams(
                                    temperature=0.0,
                                    max_tokens=max_output_tokens,
                                    min_context=(
                                        count_tokens(repair_prompt)
                                        + count_tokens(repair_system)
                                        + max_output_tokens
                                    ),
                                    thinking_mode="off",
                                ),
                                repair=False,
                                spine_phase="recovery",
                            )
                            repaired_content = repair_outcome.text
                            data = (
                                repair_outcome.value
                                if repair_outcome.status == "success"
                                else None
                            )
                        else:
                            repair_resp = await ollama.chat(
                                messages=[{"role": "user", "content": repair_prompt}],
                                temperature=0.0,
                                max_tokens=max_output_tokens,
                                response_format=repair_response_format,
                                system=(
                                    "You are a strict JSON repair adapter. Your entire response must be "
                                    "one valid JSON object."
                                ),
                                min_context=(
                                    count_tokens(repair_prompt)
                                    + count_tokens("You are a strict JSON repair adapter. Your entire response must be one valid JSON object.")
                                    + max_output_tokens
                                ),
                                thinking_mode="off",
                            )
                            repaired_content = repair_resp.get("message", {}).get("content", "")
                            data = None
                        clean_repaired_content = strip_thinking_markers(repaired_content)
                        data = data or _parse_json_response(clean_repaired_content)
                        repaired_from_non_json = bool(data)
                        json_success = bool(data)
                        if repaired_from_non_json:
                            logger.info("Skill %s repaired non-JSON LLM output into structured JSON.", self.name)
                    except Exception as e:
                        logger.warning("Skill %s JSON repair failed after non-JSON output: %s", self.name, e)

            if not data:
                plain_repair_prompt = (
                    "You are converting a UX research skill result into Istara JSON.\n"
                    "Return one valid JSON object only. No markdown, no commentary, no hidden reasoning.\n"
                        "The object must contain provisional candidate summary, nuggets, facts, insights, recommendations, and suggestions.\n"
                        "Atomic Research artifacts are not trusted at this stage; use exact source spans where available.\n"
                        "Use empty arrays when evidence is missing.\n\n"
                    f"Skill: {self.name}\n"
                    f"Display name: {display}\n"
                    f"Research data sample:\n{data_content[:2500]}\n\n"
                    f"Previous response:\n{(raw_content or repaired_content or '[empty response]')[:3500]}"
                )
                try:
                    if settings.agentic_core:
                        # W5: plain JSON repair (stage 2 of the fallback chain)
                        # dispatches through the AgenticDispatcher
                        # (``skill.repair_plain``); legacy branch preserved.
                        from app.core.agentic import agentic
                        from app.core.agentic.types import TurnParams

                        plain_system = (
                            "Return exactly one syntactically valid JSON object for Istara."
                        )
                        plain_outcome = await agentic.completion(
                            purpose="skill.repair_plain",
                            project_id=skill_input.project_id,
                            system=plain_system,
                            messages=[{"role": "user", "content": plain_repair_prompt}],
                            params=TurnParams(
                                temperature=0.0,
                                max_tokens=max_output_tokens,
                                min_context=(
                                    count_tokens(plain_repair_prompt)
                                    + count_tokens(plain_system)
                                    + max_output_tokens
                                ),
                                thinking_mode="off",
                            ),
                            spine_phase="recovery",
                        )
                        plain_repair_content = plain_outcome.text
                    else:
                        plain_repair_resp = await ollama.chat(
                            messages=[{"role": "user", "content": plain_repair_prompt}],
                            temperature=0.0,
                            max_tokens=max_output_tokens,
                            system="Return exactly one syntactically valid JSON object for Istara.",
                            min_context=(
                                count_tokens(plain_repair_prompt)
                                + count_tokens("Return exactly one syntactically valid JSON object for Istara.")
                                + max_output_tokens
                            ),
                            thinking_mode="off",
                        )
                        plain_repair_content = plain_repair_resp.get("message", {}).get("content", "")
                    data = _parse_json_response(strip_thinking_markers(plain_repair_content))
                    repaired_from_non_json = bool(data)
                    json_success = bool(data)
                    if data:
                        logger.info("Skill %s recovered structured JSON through plain repair fallback.", self.name)
                except Exception as e:
                    logger.warning("Skill %s plain JSON repair fallback failed: %s", self.name, e)

            if not data:
                logger.warning("Skill %s returned non-JSON or empty JSON output.", self.name)
                return SkillOutput(
                    success=False,
                    summary=f"{display} did not return valid structured output.",
                    errors=["LLM returned non-JSON or empty JSON output."],
                    artifacts={
                        f"{skill_name}_raw_response.txt": raw_content[:4000],
                        f"{skill_name}_repair_response.txt": (repaired_content or plain_repair_content)[:4000],
                        f"{skill_name}_schema_budget.json": json.dumps(
                            schema_budget.to_dict(),
                            indent=2,
                        ),
                    },
                    json_success=False,
                )

            nuggets, facts, insights, recommendations = _normalize_generated_findings(
                data,
                source_label=source_label,
                item_limit=item_limit,
            )
            repaired_from_empty_findings = False
            empty_findings_repair_content = ""
            deterministic_findings_fallback = False

            def finding_count() -> int:
                return len(nuggets) + len(facts) + len(insights) + len(recommendations)

            use_empty_findings_repair = not (
                (settings.llm_provider or "").strip().lower() == "lmstudio"
                and schema_budget.used_fallback
            )

            if finding_count() == 0 and use_empty_findings_repair:
                empty_findings_prompt = (
                    "The previous skill JSON was syntactically valid but contained no Istara findings.\n"
                    "Extract concise candidate/provisional evidence-backed findings from the research data and return one JSON object only.\n"
                    "Required keys: summary, nuggets, facts, insights, recommendations, suggestions.\n"
                    "If the data has usable source evidence, include at least one candidate atom/fact or insight. "
                    "Do not invent beyond the data, skip exact source spans, or mark anything accepted/reportable.\n\n"
                    f"Skill: {self.name}\n"
                    f"Display name: {display}\n"
                    f"Context:\n{(ctx or skill_input.user_context or '')[:1200]}\n\n"
                    f"Research data sample:\n{data_content[:3500]}\n\n"
                    f"Previous JSON:\n{json.dumps(data, ensure_ascii=False)[:2500]}"
                )
                try:
                    if settings.agentic_core:
                        # W5: empty-findings repair (stage 3 of the fallback
                        # chain) dispatches through the AgenticDispatcher
                        # (``skill.repair_findings``); legacy branch preserved.
                        from app.core.agentic import agentic
                        from app.core.agentic.types import TurnParams

                        findings_system = (
                            "Return exactly one valid JSON object "
                            "with non-empty Istara findings."
                        )
                        empty_outcome = await agentic.completion(
                            purpose="skill.repair_findings",
                            project_id=skill_input.project_id,
                            system=findings_system,
                            messages=[{"role": "user", "content": empty_findings_prompt}],
                            params=TurnParams(
                                temperature=0.0,
                                max_tokens=max(512, min(max_output_tokens, 768)),
                                min_context=(
                                    count_tokens(empty_findings_prompt)
                                    + count_tokens(findings_system)
                                    + max(512, min(max_output_tokens, 768))
                                ),
                                thinking_mode="off",
                            ),
                            spine_phase="recovery",
                        )
                        empty_findings_repair_content = empty_outcome.text
                    else:
                        empty_repair_resp = await ollama.chat(
                            messages=[{"role": "user", "content": empty_findings_prompt}],
                            temperature=0.0,
                            max_tokens=max(512, min(max_output_tokens, 768)),
                            system="Return exactly one valid JSON object with non-empty Istara findings.",
                            min_context=(
                                count_tokens(empty_findings_prompt)
                                + count_tokens("Return exactly one valid JSON object with non-empty Istara findings.")
                                + max(512, min(max_output_tokens, 768))
                            ),
                            thinking_mode="off",
                        )
                        empty_findings_repair_content = empty_repair_resp.get("message", {}).get("content", "")
                    repaired_data = _parse_json_response(strip_thinking_markers(empty_findings_repair_content))
                    if repaired_data:
                        repaired = _normalize_generated_findings(
                            repaired_data,
                            source_label=source_label,
                            item_limit=item_limit,
                        )
                        if sum(len(group) for group in repaired) > 0:
                            data = repaired_data
                            nuggets, facts, insights, recommendations = repaired
                            repaired_from_empty_findings = True
                            logger.info("Skill %s repaired valid JSON with empty findings.", self.name)
                except Exception as e:
                    logger.warning("Skill %s empty-finding repair failed: %s", self.name, e)

            if finding_count() == 0:
                fallback = _deterministic_findings_from_research_data(
                    data_content,
                    display=display,
                    source_label=source_label,
                    item_limit=item_limit,
                )
                if sum(len(group) for group in fallback) > 0:
                    nuggets, facts, insights, recommendations = fallback
                    deterministic_findings_fallback = True
                    data = {
                        **data,
                        "summary": data.get("summary")
                        or f"{display} completed with deterministic evidence fallback.",
                        "deterministic_findings_fallback": True,
                    }
                    logger.info("Skill %s used deterministic evidence fallback after empty model findings.", self.name)

            if finding_count() == 0:
                logger.warning("Skill %s returned structured JSON without findings.", self.name)
                return SkillOutput(
                    success=False,
                    summary=f"{display} returned structured JSON without findings.",
                    errors=["LLM returned structured JSON without findings."],
                    artifacts={
                        f"{skill_name}_analysis.json": json.dumps(data, indent=2),
                        f"{skill_name}_empty_findings_repair.txt": empty_findings_repair_content[:4000],
                        f"{skill_name}_schema_budget.json": json.dumps(
                            schema_budget.to_dict(),
                            indent=2,
                        ),
                    },
                    json_success=True,
                )

            out = SkillOutput(
                success=True,
                summary=data.get("summary", f"Completed {display} analysis."),
                nuggets=nuggets,
                facts=facts,
                insights=insights,
                recommendations=recommendations,
                artifacts={
                    f"{skill_name}_analysis.json": json.dumps(data, indent=2),
                    f"{skill_name}_schema_budget.json": json.dumps(
                        schema_budget.to_dict(),
                        indent=2,
                    ),
                    **(
                        {f"{skill_name}_raw_response.txt": raw_content[:4000]}
                        if repaired_from_non_json and raw_content
                        else {}
                    ),
                    **(
                        {f"{skill_name}_empty_findings_repair.txt": empty_findings_repair_content[:4000]}
                        if repaired_from_empty_findings and empty_findings_repair_content
                        else {}
                    ),
                    **(
                        {
                            f"{skill_name}_deterministic_fallback.json": json.dumps(
                                {
                                    "reason": "model-returned-empty-findings",
                                    "nuggets": nuggets,
                                    "facts": facts,
                                    "insights": insights,
                                    "recommendations": recommendations,
                                },
                                indent=2,
                            )
                        }
                        if deterministic_findings_fallback
                        else {}
                    ),
                },
                suggestions=[
                    *data.get("suggestions", []),
                    *(
                        ["Model returned empty findings; deterministic evidence fallback was used."]
                        if deterministic_findings_fallback
                        else []
                    ),
                ],
            )
            # Set json_success manually since __init__ may fail in some environments
            out.json_success = json_success
            return out

    # Set a unique class name for debugging
    GeneratedSkill.__name__ = f"{display.replace(' ', '')}Skill"
    GeneratedSkill.__qualname__ = GeneratedSkill.__name__
    return GeneratedSkill
