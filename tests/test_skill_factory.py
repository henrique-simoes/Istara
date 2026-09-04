"""Regression tests for generated skill prompt and output contracts."""

# Import-order guard: app.skills.skill_factory sits on a latent module-level
# import cycle (research_validity -> skills.intercoder -> skill_factory ->
# file_processor -> embeddings -> pi_runtime.engine -> telemetry ->
# research_validity) that only resolves when the dispatcher plane
# (app.core.agentic) has been initialized first in the process. The cycle is
# pre-existing architecture debt outside this file; initializing the plane
# here keeps a standalone run of this file green.
import app.core.agentic  # noqa: F401

import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.skills.base import SkillInput, SkillOutput, SkillPhase, SkillType
from app.skills.skill_factory import _make_schema_strict, create_skill
from app.core.token_counter import count_tokens


def _completion_outcome(text: str) -> SimpleNamespace:
    """Dispatcher completion outcome (text only, no parsed value)."""
    return SimpleNamespace(
        text=text,
        status="success",
        usage={},
        stop_reason="stop",
        endpoint_id="ep-stub",
        tool_calls=[],
    )


def _structured_outcome(payload, *, status: str = "success") -> SimpleNamespace:
    """Dispatcher structured outcome.

    ``payload`` may be a dict (parsed ``value`` plus JSON ``text``) or a raw
    string (unparseable text with an empty ``value``), mirroring the two ways
    the real dispatcher reports structured results.
    """
    if isinstance(payload, str):
        text, value = payload, {}
    else:
        text, value = json.dumps(payload), payload
    return SimpleNamespace(
        text=text,
        value=value,
        status=status,
        usage={},
        stop_reason="stop",
        endpoint_id="ep-stub",
        tool_calls=[],
    )


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton.

    ``completion_results`` / ``structured_results`` are queued per verb so the
    multi-stage fallback chain (skill.execute -> skill.repair_native ->
    skill.repair_plain -> skill.repair_findings) can be driven stage by stage.
    A queued ``Exception`` instance is raised instead of returned.
    """

    def __init__(self, *, completion_results=None, structured_results=None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._completion_results = list(completion_results or [])
        self._structured_results = list(structured_results or [])

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        result = (
            self._completion_results.pop(0)
            if self._completion_results
            else _completion_outcome("")
        )
        if isinstance(result, Exception):
            raise result
        return result

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        result = (
            self._structured_results.pop(0)
            if self._structured_results
            else _structured_outcome("")
        )
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_generated_skill_preserves_literal_prompt_braces(monkeypatch):
    """Literal braces in methodology text must not be treated as format fields."""
    payload = {
        "nuggets": [
            {
                "text": "Three participants abandoned onboarding.",
                "source": "survey",
                "tags": ["ux-law:{id}"],
            }
        ],
        "facts": [{"text": "Onboarding abandonment appeared in survey data."}],
        "insights": [
            {
                "text": "Onboarding friction is likely affecting activation.",
                "confidence": "medium",
            }
        ],
        "recommendations": [
            {
                "text": "Shorten the first onboarding step.",
                "priority": "high",
            }
        ],
        "summary": "Completed survey analysis.",
    }
    dispatcher_stub = _StubAgentic(structured_results=[_structured_outcome(payload)])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="literal-brace-skill",
        display="Literal Brace Skill",
        desc="Tests prompt formatting with literal braces.",
        phase=SkillPhase.DISCOVER,
        skill_type=SkillType.QUANTITATIVE,
        plan_prompt="Plan for {context}; keep ux-law:{id}.",
        execute_prompt=(
            "Context: {context}\nSurvey Data: {content}\nTag findings with ux-law:{id}."
        ),
        output_schema='{"nuggets": [{"text": "..."}], "summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(
            project_id="project-1",
            user_context="survey rows",
            project_context="test project context",
        )
    )

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    prompt = kwargs["messages"][0]["content"]
    assert "Context: test project context" in prompt
    assert "Survey Data: [RESEARCH_DATA_BELOW]" in prompt
    assert "Tag findings with ux-law:{id}." in prompt
    assert "candidate/provisional Research Spine artifacts" in prompt
    assert "<research_spine_contract>" in prompt
    assert (
        "Sources and exact source spans come before trusted Atomic Research" in prompt
    )
    assert "Do not describe any artifact as accepted" in prompt

    assert output.success is True
    assert output.json_success is True
    assert output.nuggets[0]["tags"] == ["ux-law:{id}"]
    assert output.nuggets[0]["artifact_state"] == "candidate_atom"
    assert output.nuggets[0]["research_validity"]["report_allowed"] is False
    assert output.insights[0]["artifact_state"] == "candidate_insight"


def test_skill_output_cannot_self_promote_reportability():
    output = SkillOutput(
        success=True,
        summary="Attempted self-promotion.",
        research_validity={"status": "accepted", "report_allowed": True},
        nuggets=[
            {
                "text": "A model-generated observation.",
                "source": "skill",
                "tags": ["friction"],
                "research_validity": {"status": "accepted", "report_allowed": True},
            }
        ],
    )

    assert output.research_validity["status"] == "provisional"
    assert output.research_validity["report_allowed"] is False
    assert output.nuggets[0]["research_validity"]["status"] == "provisional"
    assert output.nuggets[0]["research_validity"]["report_allowed"] is False


@pytest.mark.asyncio
async def test_generated_skill_plan_falls_back_on_empty_llm_response(monkeypatch):
    dispatcher_stub = _StubAgentic(completion_results=[_completion_outcome("")])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="empty-plan-skill",
        display="Empty Plan Skill",
        desc="Tests plan fallback behavior.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    plan = await skill_cls().plan(
        SkillInput(project_id="project-1", user_context="Need a plan")
    )

    assert plan["skill"] == "empty-plan-skill"
    assert plan["fallback"] is True
    assert "Empty Plan Skill Plan" in plan["plan"]
    assert "Need a plan" in plan["plan"]


@pytest.mark.asyncio
async def test_generated_skill_plan_falls_back_on_llm_error(monkeypatch):
    dispatcher_stub = _StubAgentic(
        completion_results=[RuntimeError("No compute nodes available for chat")]
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="error-plan-skill",
        display="Error Plan Skill",
        desc="Tests plan fallback after provider errors.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    plan = await skill_cls().plan(
        SkillInput(project_id="project-1", user_context="Provider down")
    )

    assert plan["skill"] == "error-plan-skill"
    assert plan["fallback"] is True
    assert "Error Plan Skill Plan" in plan["plan"]


@pytest.mark.asyncio
async def test_generated_skill_execute_fails_on_non_json_llm_response(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: prose text, no parsed value
            _structured_outcome("Here is a prose answer, not JSON."),
            # skill.repair_native: still unusable
            _structured_outcome("Here is a prose answer, not JSON."),
        ],
        completion_results=[
            # skill.repair_plain: still unusable
            _completion_outcome("Here is a prose answer, not JSON."),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="non-json-execute-skill",
        display="Non JSON Execute Skill",
        desc="Tests execute failure on invalid model output.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is False
    assert output.json_success is False
    assert output.errors == ["LLM returned non-JSON or empty JSON output."]
    assert len(dispatcher_stub.calls) == 3
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
        "completion",
    ]
    native_repair = dispatcher_stub.calls[1][1]
    assert native_repair["purpose"] == "skill.repair_native"
    assert native_repair["schema"]["type"] == "object"
    assert "schema" not in dispatcher_stub.calls[2][1]
    assert "non-json-execute-skill_schema_budget.json" in output.artifacts


@pytest.mark.asyncio
async def test_generated_skill_repairs_non_json_llm_response(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: prose text, no parsed value
            _structured_outcome("The key finding is that onboarding friction is high."),
            # skill.repair_native: valid normalized JSON
            _structured_outcome(
                {
                    "summary": "Onboarding friction is high.",
                    "nuggets": [],
                    "facts": [
                        {"text": "The failed response identified onboarding friction."}
                    ],
                    "insights": [],
                    "recommendations": [],
                    "suggestions": [],
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="json-repair-execute-skill",
        display="JSON Repair Execute Skill",
        desc="Tests execute repair for invalid model output.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "...", "facts": [{"text": "..."}]}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    assert output.json_success is True
    assert output.summary == "Onboarding friction is high."
    assert "json-repair-execute-skill_raw_response.txt" in output.artifacts
    assert len(dispatcher_stub.calls) == 2
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
    ]
    native_repair = dispatcher_stub.calls[1][1]
    assert native_repair["purpose"] == "skill.repair_native"
    assert native_repair["schema"]["type"] == "object"
    assert "strict JSON repair adapter" in native_repair["system"]


@pytest.mark.asyncio
async def test_generated_skill_plain_json_repair_fallback_when_native_repair_fails(
    monkeypatch,
):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: empty text, no parsed value
            _structured_outcome(""),
            # skill.repair_native: still unusable
            _structured_outcome(""),
        ],
        completion_results=[
            # skill.repair_plain: valid JSON behind thinking markers
            _completion_outcome(
                "<think>drafting</think>\n"
                '{"summary": "Recovered JSON.", "nuggets": [], "facts": [{"text": "Recovered fact."}], '
                '"insights": [], "recommendations": [], "suggestions": []}'
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="plain-repair-skill",
        display="Plain Repair Skill",
        desc="Tests response-format-free repair fallback.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    assert output.json_success is True
    assert output.summary == "Recovered JSON."
    assert len(dispatcher_stub.calls) == 3
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
        "completion",
    ]
    assert "schema" in dispatcher_stub.calls[1][1]
    assert "schema" not in dispatcher_stub.calls[2][1]


@pytest.mark.asyncio
async def test_generated_skill_ignores_classical_provider_when_running_native_repair(
    monkeypatch,
):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: prose text, no parsed value
            _structured_outcome("A prose response that missed JSON."),
            # skill.repair_native: Pi-selected route repairs the output even
            # when the retired classical provider setting says lmstudio.
            _structured_outcome(
                {
                    "summary": "Recovered through Pi native repair.",
                    "nuggets": [],
                    "facts": [{"text": "Recovered fact through Pi native repair."}],
                    "insights": [],
                    "recommendations": [],
                    "suggestions": [],
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="lmstudio-repair-skill",
        display="LM Studio Repair Skill",
        desc="Tests provider-aware repair fallback.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    assert output.json_success is True
    assert output.summary == "Recovered through Pi native repair."
    assert len(dispatcher_stub.calls) == 2
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
    ]
    assert [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls] == [
        "skill.execute",
        "skill.repair_native",
    ]


@pytest.mark.asyncio
async def test_generated_skill_repairs_valid_json_with_empty_findings(monkeypatch):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: valid JSON but zero findings
            _structured_outcome({"summary": "No findings here."}),
        ],
        completion_results=[
            # skill.repair_findings: valid JSON with findings
            _completion_outcome(
                json.dumps(
                    {
                        "summary": "Extracted findings.",
                        "nuggets": [
                            {
                                "text": "Participant could not find discount code.",
                                "source": "test",
                            }
                        ],
                        "facts": [{"text": "Discount discovery failed in checkout."}],
                        "insights": [],
                        "recommendations": [],
                        "suggestions": [],
                    }
                )
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="empty-findings-repair-skill",
        display="Empty Findings Repair Skill",
        desc="Tests empty finding repair.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "..."}',
    )

    output = await skill_cls().execute(
        SkillInput(
            project_id="project-1",
            user_context="Participant could not find discount code.",
        )
    )

    assert output.success is True
    assert output.summary == "Extracted findings."
    assert output.nuggets[0]["text"] == "Participant could not find discount code."
    assert len(dispatcher_stub.calls) == 2
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "completion",
    ]
    assert "schema" not in dispatcher_stub.calls[1][1]
    assert "empty-findings-repair-skill_empty_findings_repair.txt" in output.artifacts


@pytest.mark.asyncio
async def test_generated_skill_attempts_model_repair_before_deterministic_fallback_even_with_classical_setting(
    monkeypatch,
):
    monkeypatch.setattr(settings, "llm_provider", "lmstudio")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: valid JSON but zero findings.
            _structured_outcome({"summary": "No findings here."}),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="deterministic-fallback-skill",
        display="Deterministic Fallback Skill",
        desc="Tests deterministic empty-finding fallback.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema=json.dumps(
            {
                "summary": "...",
                "fields": {f"field_{idx}": {"nested": "..."} for idx in range(200)},
            }
        ),
    )

    output = await skill_cls().execute(
        SkillInput(
            project_id="project-1",
            user_context="date,sessions,nps\n2026-03-01,100,32\n2026-03-02,120,35",
        )
    )

    assert output.success is True
    assert output.json_success is True
    assert output.nuggets[0]["tags"] == ["deterministic-fallback"]
    assert "columns: date, sessions, nps" in output.facts[0]["text"]
    assert "preliminary" in output.insights[0]["text"]
    assert "deterministic evidence fallback was used" in output.suggestions[0]
    assert (
        "deterministic-fallback-skill_deterministic_fallback.json" in output.artifacts
    )
    assert len(dispatcher_stub.calls) == 2
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "completion",
    ]
    assert dispatcher_stub.calls[1][1]["purpose"] == "skill.repair_findings"


@pytest.mark.asyncio
async def test_generated_skill_normalizes_hmw_schema_fields(monkeypatch):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            _structured_outcome(
                {
                    "source_insights": [
                        {
                            "text": "Users cannot find the promo code field.",
                            "evidence": [
                                "3 of 8 participants failed to locate the promo code field."
                            ],
                            "data_point_count": 3,
                            "confidence": "high",
                        }
                    ],
                    "hmw_statements": [
                        {
                            "statement": "How might we make discounts discoverable without slowing checkout?",
                            "cluster": "Checkout confidence",
                        }
                    ],
                    "prioritized_top_5": [
                        {
                            "statement": "How might we make discounts discoverable without slowing checkout?",
                            "rationale": "High impact checkout friction.",
                        }
                    ],
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="hmw-normalization-skill",
        display="HMW Normalization Skill",
        desc="Tests schema-specific normalization.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"source_insights": [], "hmw_statements": [], "prioritized_top_5": []}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    assert (
        output.nuggets[0]["text"]
        == "3 of 8 participants failed to locate the promo code field."
    )
    assert output.facts[0]["text"].startswith("Users cannot find the promo code field.")
    assert output.insights[0]["text"] == "Users cannot find the promo code field."
    assert output.recommendations[0]["text"].startswith("Use this HMW for ideation:")


@pytest.mark.asyncio
async def test_generated_skill_normalizes_longitudinal_schema_fields(monkeypatch):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            _structured_outcome(
                {
                    "heart_scorecard": {
                        "happiness": {
                            "primary_metric": "NPS",
                            "trend": "declining",
                            "health": "red",
                        }
                    },
                    "metrics": [
                        {
                            "metric_id": "nps",
                            "metric_name": "NPS",
                            "data_points": [{"date": "2026-03-01", "value": 32}],
                            "trend": {"direction": "declining"},
                        }
                    ],
                    "regressions": [
                        {
                            "metric": "NPS",
                            "severity": "major",
                            "magnitude_pct": 18,
                            "investigation_status": "needs_investigation",
                        }
                    ],
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    skill_cls = create_skill(
        skill_name="longitudinal-normalization-skill",
        display="Longitudinal Normalization Skill",
        desc="Tests metric schema normalization.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"heart_scorecard": {}, "metrics": [], "regressions": []}',
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    assert "NPS observed data points" in output.nuggets[0]["text"]
    assert "HEART happiness tracks NPS" in output.facts[0]["text"]
    assert "NPS regression severity=major" in output.insights[0]["text"]
    assert (
        output.recommendations[0]["text"]
        == "Investigate the NPS regression (needs_investigation)."
    )


@pytest.mark.asyncio
async def test_generated_skill_counts_native_schema_in_context_budget(monkeypatch):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            _structured_outcome(
                {
                    "nuggets": [],
                    "facts": [{"text": "Schema budget fact."}],
                    "insights": [],
                    "recommendations": [],
                    "summary": "ok",
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    output_schema = json.dumps(
        {
            "summary": "...",
            "fields": {f"field_{idx}": "..." for idx in range(30)},
        }
    )
    skill_cls = create_skill(
        skill_name="schema-budget-skill",
        display="Schema Budget Skill",
        desc="Tests schema budget accounting.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema=output_schema,
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    method, captured = dispatcher_stub.calls[0]
    assert method == "structured"
    expected_floor = (
        count_tokens(captured["messages"][0]["content"])
        + count_tokens(
            "You are a meticulous UX Research Auditor. You prioritize evidence over assumption."
        )
        + captured["params"].max_tokens
        + count_tokens(json.dumps(captured["schema"], ensure_ascii=False))
    )
    assert captured["params"].min_context >= expected_floor
    assert "A native JSON schema is attached" in captured["messages"][0]["content"]
    assert output_schema not in captured["messages"][0]["content"]


@pytest.mark.asyncio
async def test_generated_skill_uses_normalized_schema_when_native_schema_is_too_large(
    monkeypatch,
):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            _structured_outcome(
                {
                    "nuggets": [],
                    "facts": [{"text": "Oversized schema fact."}],
                    "insights": [],
                    "recommendations": [],
                    "summary": "ok",
                    "suggestions": [],
                }
            ),
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr(settings, "skill_execute_max_schema_tokens", 256)
    output_schema = json.dumps(
        {
            "summary": "...",
            "fields": {
                f"field_{idx}": {"nested": "...", "type": "label"} for idx in range(200)
            },
        }
    )
    skill_cls = create_skill(
        skill_name="oversized-schema-skill",
        display="Oversized Schema Skill",
        desc="Tests normalized schema fallback for local execution.",
        phase=SkillPhase.DELIVER,
        skill_type=SkillType.QUALITATIVE,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema=output_schema,
    )

    output = await skill_cls().execute(
        SkillInput(project_id="project-1", user_context="Short content")
    )

    assert output.success is True
    method, captured = dispatcher_stub.calls[0]
    assert method == "structured"
    assert captured["schema"]["type"] == "object"
    assert {
        "summary",
        "nuggets",
        "facts",
        "insights",
        "recommendations",
        "suggestions",
    }.issubset(set(captured["schema"].get("properties", {})))
    assert output_schema not in captured["messages"][0]["content"]
    budget = json.loads(output.artifacts["oversized-schema-skill_schema_budget.json"])
    assert budget["schema_name"] == "oversized_schema_skill_normalized_output"
    assert budget["used_fallback"] is True
    assert budget["reason"] == "schema-token-budget-exceeded"
    assert {
        "summary",
        "nuggets",
        "facts",
        "insights",
        "recommendations",
        "suggestions",
    }.issubset(set(budget["preserved_fields"]))


def test_example_output_schema_allows_business_type_fields():
    strict_schema = _make_schema_strict(
        {
            "response_summary": [
                {
                    "question_id": "q1",
                    "type": "likert|rating|open-ended",
                    "results": {"mean": 0, "frequencies": {}},
                }
            ],
            "nuggets": [{"text": "quote", "type": "statistic|quote"}],
            "summary": "...",
        }
    )

    response_item = strict_schema["properties"]["response_summary"]["items"]
    nugget_item = strict_schema["properties"]["nuggets"]["items"]

    assert response_item["type"] == "object"
    assert response_item["properties"]["type"] == {"type": "string"}
    assert response_item["properties"]["results"]["type"] == "object"
    assert nugget_item["type"] == "object"
    assert nugget_item["properties"]["type"] == {"type": "string"}
