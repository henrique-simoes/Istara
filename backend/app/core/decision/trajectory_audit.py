"""Per-transition audit of an agent's tool-call trajectory (CF-SPEC-1, Phase 8, I8).

A trajectory is a list of transitions (s, a, o): the state the agent was in, the tool call it made
and the observation that came back, followed by what the agent said or did next. Following Wang &
Gao [R7], each transition is checked on its own, so a failure is localised rather than averaged
into one task score. This module is pure and deterministic:

* ``unknown_tool``: the call names a tool that is not in the catalogue;
* ``missing_argument`` / ``wrong_type`` / ``unexpected_argument``: the arguments break the tool's
  JSON schema (``required``, ``properties[*].type``, ``additionalProperties: false``);
* ``empty_observation`` / ``error_observation``: nothing usable came back;
* ``claims_success_after_error``: the next step reports success right after an error observation.

Whether an observation *supports* the next statement is a semantic question; the service layer
asks a decision model (``services.decider_advisory``) for that and records it as advice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list, tuple),
    "object": (dict,),
    "null": (type(None),),
}
_ERROR_MARKERS = ("error", "exception", "traceback", "failed", "not found", "denied", "timeout")
_SUCCESS_MARKERS = ("success", "done", "completed", "found", "saved", "created", "succeeded")


@dataclass(frozen=True)
class Transition:
    tool: str
    arguments: Mapping[str, Any]
    observation: str
    next_step: str = ""


@dataclass
class TransitionFinding:
    index: int
    tool: str
    flags: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.flags


def _type_ok(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        types = _JSON_TYPES.get(str(name))
        if types is None:
            return True  # unknown schema type: do not guess
        if name in ("integer", "number") and isinstance(value, bool):
            continue
        if isinstance(value, types):
            return True
    return False


def schema_flags(arguments: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    """Argument problems against a JSON-schema subset (required, property types, extras)."""
    flags: list[str] = []
    properties = schema.get("properties") or {}
    for name in schema.get("required") or []:
        if name not in arguments:
            flags.append(f"missing_argument:{name}")
    for name, value in arguments.items():
        spec = properties.get(name)
        if spec is None:
            if schema.get("additionalProperties") is False:
                flags.append(f"unexpected_argument:{name}")
            continue
        if "type" in spec and not _type_ok(value, spec["type"]):
            flags.append(f"wrong_type:{name}")
    return flags


def _is_error(observation: str) -> bool:
    lowered = observation.lower()
    return any(marker in lowered for marker in _ERROR_MARKERS)


def _claims_success(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _SUCCESS_MARKERS)


def audit_trajectory(
    transitions: Sequence[Transition], tools: Mapping[str, Mapping[str, Any]]
) -> list[TransitionFinding]:
    """One finding per transition; ``tools`` maps tool name to its JSON schema."""
    findings: list[TransitionFinding] = []
    for index, step in enumerate(transitions):
        finding = TransitionFinding(index=index, tool=step.tool)
        schema = tools.get(step.tool)
        if schema is None:
            finding.flags.append("unknown_tool")
        else:
            finding.flags.extend(schema_flags(step.arguments, schema))
        observation = (step.observation or "").strip()
        if not observation:
            finding.flags.append("empty_observation")
        elif _is_error(observation):
            finding.flags.append("error_observation")
            if step.next_step and _claims_success(step.next_step):
                finding.flags.append("claims_success_after_error")
        findings.append(finding)
    return findings


def audit_summary(findings: Sequence[TransitionFinding]) -> dict[str, Any]:
    """Content-free counts for telemetry and reports."""
    counts: dict[str, int] = {}
    for finding in findings:
        for flag in finding.flags:
            kind = flag.split(":", 1)[0]
            counts[kind] = counts.get(kind, 0) + 1
    flagged = [f.index for f in findings if not f.ok]
    return {
        "transitions": len(findings),
        "flagged_transitions": len(flagged),
        "first_flagged_index": flagged[0] if flagged else None,
        "flag_counts": counts,
    }
