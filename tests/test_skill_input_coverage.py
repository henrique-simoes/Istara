"""SK2, SK4, D-14: skills read all of their input, and never invent findings.

Before this round the generic runner read at most 4,000 characters per task (a 4,096-token
context, 1,024 output tokens), the interview skill read the first 4,000 characters of each
transcript, and an empty model answer was replaced by deterministic meta-findings.
"""

from __future__ import annotations

import app.core.agentic  # noqa: F401  (import-order guard, see test_w5_skill_factory.py)

import json
from types import SimpleNamespace

import pytest


def _transcript(tag: str, paragraphs: int = 60) -> str:
    return "\n\n".join(
        f"P-{tag}: paragraph {i} says marker-{tag}-{i:03d} about invoices and receipts."
        for i in range(paragraphs)
    )


class _RecordingAgentic:
    """Answers every call with one nugget quoting the first marker it sees; records prompts."""

    def __init__(self, empty: bool = False):
        self.prompts: list[str] = []
        self.empty = empty

    async def structured(self, **kwargs):  # noqa: ANN003
        content = kwargs["messages"][-1]["content"]
        self.prompts.append(content)
        if self.empty:
            value = {"summary": "nothing", "nuggets": [], "facts": [], "insights": [],
                     "recommendations": []}
        else:
            marker = next((w for w in content.split() if w.startswith("marker-")), "none")
            value = {
                "summary": "ok",
                "nuggets": [{"text": f"quote with {marker}", "source": "", "tags": []}],
                "facts": [{"text": f"fact about {marker}"}],
                "insights": [],
                "recommendations": [],
            }
        return SimpleNamespace(usage={}, text=json.dumps(value), value=value, status="success")

    async def completion(self, **kwargs):  # noqa: ANN003
        content = kwargs["messages"][-1]["content"]
        self.prompts.append(content)
        return SimpleNamespace(usage={}, text="{}", status="success")


def _skill():
    from app.skills.base import SkillPhase, SkillType
    from app.skills.skill_factory import create_skill

    return create_skill(
        skill_name="coverage-test-skill",
        display="Coverage Test Skill",
        desc="Reads everything.",
        phase=SkillPhase.DISCOVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "...", "nuggets": [{"text": "..."}], "facts": [{"text": "..."}]}',
    )


@pytest.fixture
def small_budget(monkeypatch):
    """A 4,096-token endpoint: the smallest local model the product supports."""
    monkeypatch.setattr("app.config.settings.skill_execute_context_limit_tokens", 4096)
    monkeypatch.setattr("app.config.settings.skill_execute_max_output_tokens", 1024)
    try:
        from app.skills import skill_windows
    except ImportError:  # main before DEC-9: the settings above are its whole budget
        return
    monkeypatch.setattr(
        skill_windows,
        "resolve_call_budget",
        lambda project_id: skill_windows.SkillCallBudget(
            context_tokens=4096, max_output_tokens=1024
        ),
    )


@pytest.mark.asyncio
async def test_generic_skill_reads_every_file_in_full(monkeypatch, tmp_path, small_budget):
    from app.skills.base import SkillInput

    files = []
    for tag in ("A", "B", "C"):
        path = tmp_path / f"interview-{tag}.txt"
        path.write_text(_transcript(tag), encoding="utf-8")
        files.append(str(path))
    agentic = _RecordingAgentic()
    monkeypatch.setattr("app.core.agentic.agentic", agentic)

    output = await _skill()().execute(SkillInput(project_id="p1", files=files))

    seen = " ".join(agentic.prompts)
    missing = [f"marker-{t}-{i:03d}" for t in "ABC" for i in range(60) if f"marker-{t}-{i:03d}" not in seen]
    assert missing == []
    coverage = json.loads(output.artifacts.get("input_coverage.json", "{}"))
    assert coverage["coverage"] == 1.0 and coverage["windows"] > 1
    assert output.success and output.nuggets
    assert {n["source"] for n in output.nuggets} <= {"interview-A.txt", "interview-B.txt", "interview-C.txt", "interview-A.txt, interview-B.txt", "interview-B.txt, interview-C.txt"}
    assert any("evidence nuggets extracted from all" in p for p in agentic.prompts)


@pytest.mark.asyncio
async def test_empty_model_answer_stores_no_invented_findings(monkeypatch, tmp_path, small_budget):
    from app.skills.base import SkillInput

    path = tmp_path / "survey.csv"
    path.write_text("date,score\n2026-09-01,4\n2026-09-02,5\n", encoding="utf-8")
    monkeypatch.setattr("app.core.agentic.agentic", _RecordingAgentic(empty=True))

    output = await _skill()().execute(SkillInput(project_id="p1", files=[str(path)]))

    assert output.success is False
    assert (output.nuggets, output.facts, output.insights, output.recommendations) == ([], [], [], [])


@pytest.mark.asyncio
async def test_interview_skill_reads_a_long_transcript_to_the_end_and_synthesises_one(
    monkeypatch, tmp_path, small_budget
):
    from app.skills.base import SkillInput
    from app.skills.discover.user_interviews import UserInterviewsSkill

    path = tmp_path / "HB-IV-01-P01.md"
    path.write_text(_transcript("Z", paragraphs=400), encoding="utf-8")  # ~30,000 characters
    agentic = _RecordingAgentic()
    monkeypatch.setattr("app.core.agentic.agentic", agentic)

    output = await UserInterviewsSkill().execute(SkillInput(project_id="p1", files=[str(path)]))

    seen = " ".join(agentic.prompts)
    assert "marker-Z-399" in seen  # the last paragraph reached a model
    assert len(agentic.prompts) >= 3  # several passages plus the synthesis
    assert output.facts, "a single transcript is synthesised too"


@pytest.mark.parametrize(
    "module, cls",
    [
        ("app.skills.discover.contextual_inquiry", "ContextualInquirySkill"),
        ("app.skills.discover.diary_studies", "DiaryStudiesSkill"),
    ],
)
@pytest.mark.asyncio
async def test_custom_discover_skills_read_every_note(monkeypatch, tmp_path, small_budget, module, cls):
    import importlib

    from app.skills.base import SkillInput

    skill_cls = getattr(importlib.import_module(module), cls)
    path = tmp_path / "notes-Q.md"
    path.write_text(_transcript("Q", paragraphs=300), encoding="utf-8")  # ~22,000 characters
    agentic = _RecordingAgentic()
    monkeypatch.setattr("app.core.agentic.agentic", agentic)

    output = await skill_cls().execute(SkillInput(project_id="p1", files=[str(path)]))

    seen = " ".join(agentic.prompts)
    assert "marker-Q-299" in seen and "marker-Q-000" in seen
    assert output.nuggets and all(n["source"] == "notes-Q.md" for n in output.nuggets)
