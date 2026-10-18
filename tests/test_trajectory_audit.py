"""Per-transition trajectory audit (CF-SPEC-1, Phase 8, I8). Pure, deterministic."""

from app.core.decision.trajectory_audit import (
    Transition,
    audit_summary,
    audit_trajectory,
    schema_flags,
)

TOOLS = {
    "search_documents": {
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["query"],
        "additionalProperties": False,
    },
    "save_nugget": {"type": "object", "properties": {"text": {"type": "string"}}},
}


def test_schema_flags_cover_required_types_and_extras():
    schema = TOOLS["search_documents"]
    assert schema_flags({"query": "x", "limit": 3}, schema) == []
    assert schema_flags({"limit": 3}, schema) == ["missing_argument:query"]
    assert schema_flags({"query": "x", "limit": True}, schema) == ["wrong_type:limit"]
    assert schema_flags({"query": "x", "page": 2}, schema) == ["unexpected_argument:page"]
    # Extra arguments are allowed unless the schema forbids them.
    assert schema_flags({"text": "t", "tag": "a"}, TOOLS["save_nugget"]) == []


def test_each_transition_is_flagged_on_its_own():
    transitions = [
        Transition("search_documents", {"query": "onboarding"}, "3 passages", "Reading them"),
        Transition("search_documents", {"limit": "5"}, "", ""),
        Transition("delete_project", {}, "ok", ""),
        Transition("save_nugget", {"text": "t"}, "Error: database locked", "Saved the nugget."),
    ]
    findings = audit_trajectory(transitions, TOOLS)
    assert findings[0].ok
    assert findings[1].flags == [
        "missing_argument:query",
        "wrong_type:limit",
        "empty_observation",
    ]
    assert findings[2].flags == ["unknown_tool"]
    assert findings[3].flags == ["error_observation", "claims_success_after_error"]
    summary = audit_summary(findings)
    assert summary["transitions"] == 4 and summary["flagged_transitions"] == 3
    assert summary["first_flagged_index"] == 1
    assert summary["flag_counts"]["missing_argument"] == 1
