"""JudgeLayer for the Pi-vs-Legacy benchmark (task B0-7, master plan §10.3).

Judges are never the DUT and never re-spend (winning plan §2.2 principle 5):

* The judge model is owner-set in one config file and MUST differ from every DUT model —
  a config that judges with a DUT model is rejected at load.
* Every judgment is **blind** (engine arms relabelled A/B) and **position-swapped**
  deterministically per pair, so neither the engine identity nor a fixed A/B position can
  bias the judge.
* Every prompt logs ``sha256(rubric_version || rubric || prompt)`` for auditability.
* Results are cached by ``(scenario, run, rubric_version, judge_model)`` so re-reporting
  (B4) costs nothing.

The model call is *injected* (``judge_fn``): the layer assembles the blind prompt, manages
the cache and logging, and un-blinds the verdict — all of which is pure and unit-testable
at T0 with a deterministic fake. No model is loaded here; a live judge is wired only
behind owner gate G1.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class JudgeIsDutError(ValueError):
    """Raised when the configured judge model is also a device-under-test model."""


@dataclass(frozen=True)
class JudgeConfig:
    """Owner-set judge configuration (loaded from a JSON file)."""

    judge_model: str
    dut_models: frozenset[str]
    rubric_versions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.judge_model:
            raise ValueError("judge_model must be set")
        if self.judge_model in self.dut_models:
            raise JudgeIsDutError(
                f"judge_model {self.judge_model!r} is also a DUT model; the judge must "
                "differ from every engine under test"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeConfig":
        return cls(
            judge_model=str(data["judge_model"]),
            dut_models=frozenset(str(m) for m in data.get("dut_models", [])),
            rubric_versions=dict(data.get("rubric_versions", {})),
        )

    @classmethod
    def load(cls, path: str | Path) -> "JudgeConfig":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


@dataclass(frozen=True)
class Rubric:
    axis: str
    version: str
    text: str


# A minimal default rubric bank; a live run supplies owner-versioned rubrics per axis.
DEFAULT_RUBRIC_BANK: dict[str, Rubric] = {
    "output_quality": Rubric(
        "output_quality", "1.0.0",
        "Score each response 1-7 for correctness, grounding, and completeness. "
        "Prefer responses whose claims trace to provided evidence.",
    ),
    "a2a": Rubric(
        "a2a", "1.0.0",
        "Score each multi-agent transcript 1-7 for goal completion, coordination "
        "efficiency, and absence of redundant rounds.",
    ),
    "spine_phase": Rubric(
        "spine_phase", "1.0.0",
        "Score adherence to the research-validity spine phase under review 1-7.",
    ),
}


@dataclass
class Judgment:
    scenario_id: str
    run_id: str
    axis: str
    rubric_version: str
    judge_model: str
    prompt_sha256: str
    # Un-blinded verdict: winner is "pi" | "legacy" | "tie".
    winner: str
    scores: dict[str, float]
    # The A/B → engine mapping actually used for this judgment (audit trail).
    position: dict[str, str]
    cached: bool = False


# judge_fn receives the blind prompt and the two blind arms, returns a raw verdict dict:
#   {"winner": "A"|"B"|"tie", "score_a": float, "score_b": float, ...}
JudgeFn = Callable[[str, dict[str, str]], dict[str, Any]]


class JudgeLayer:
    def __init__(
        self,
        config: JudgeConfig,
        judge_fn: JudgeFn | None = None,
        rubric_bank: dict[str, Rubric] | None = None,
    ) -> None:
        self.config = config
        self._judge_fn = judge_fn
        self._bank = rubric_bank if rubric_bank is not None else DEFAULT_RUBRIC_BANK
        self._cache: dict[tuple[str, str, str, str], Judgment] = {}

    # ── blinding ─────────────────────────────────────────────────────────────
    @staticmethod
    def _swap(pair_key: str) -> bool:
        """Deterministic position swap per pair: True == pi occupies slot B.

        Derived from a stable hash of the pair key so it is reproducible across reruns
        yet hides which arm is pi behind a per-pair coin flip.
        """
        digest = hashlib.sha256(pair_key.encode()).digest()
        return bool(digest[0] & 1)

    def _blind(self, pair_key: str, pi_output: str, legacy_output: str) -> tuple[dict[str, str], dict[str, str]]:
        """Return ``(arms, position)``: arms maps A/B → text, position maps A/B → engine."""
        if self._swap(pair_key):
            return {"A": legacy_output, "B": pi_output}, {"A": "legacy", "B": "pi"}
        return {"A": pi_output, "B": legacy_output}, {"A": "pi", "B": "legacy"}

    def rubric_for(self, axis: str) -> Rubric:
        rubric = self._bank.get(axis)
        if rubric is None:
            raise KeyError(f"no rubric for axis {axis!r}")
        # Honour an owner-pinned rubric version override if the config declares one.
        version = self.config.rubric_versions.get(axis, rubric.version)
        return Rubric(axis=rubric.axis, version=version, text=rubric.text)

    def _build_prompt(self, rubric: Rubric, arms: dict[str, str]) -> str:
        return (
            f"[rubric:{rubric.axis}@{rubric.version}]\n{rubric.text}\n\n"
            f"[Response A]\n{arms['A']}\n\n[Response B]\n{arms['B']}\n\n"
            "Return the stronger response (A, B, or tie) and a 1-7 score for each."
        )

    @staticmethod
    def _prompt_sha256(rubric: Rubric, prompt: str) -> str:
        payload = f"{rubric.version}\n{rubric.text}\n{prompt}".encode()
        return hashlib.sha256(payload).hexdigest()

    # ── judging ──────────────────────────────────────────────────────────────
    def judge(
        self, *, scenario_id: str, run_id: str, axis: str, pi_output: str, legacy_output: str,
    ) -> Judgment:
        rubric = self.rubric_for(axis)
        cache_key = (scenario_id, run_id, rubric.version, self.config.judge_model)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            return Judgment(**{**cached.__dict__, "cached": True})

        if self._judge_fn is None:
            raise RuntimeError(
                "no judge_fn wired; live judging is owner-gated (G1). Inject a judge_fn to "
                "run the JudgeLayer offline."
            )

        pair_key = f"{scenario_id}|{run_id}|{axis}"
        arms, position = self._blind(pair_key, pi_output, legacy_output)
        prompt = self._build_prompt(rubric, arms)
        prompt_sha = self._prompt_sha256(rubric, prompt)

        raw = self._judge_fn(prompt, arms)
        winner_slot = str(raw.get("winner", "tie")).upper()
        winner = position.get(winner_slot, "tie") if winner_slot in ("A", "B") else "tie"
        scores = {
            position["A"]: float(raw.get("score_a", 0.0)),
            position["B"]: float(raw.get("score_b", 0.0)),
        }
        judgment = Judgment(
            scenario_id=scenario_id, run_id=run_id, axis=axis, rubric_version=rubric.version,
            judge_model=self.config.judge_model, prompt_sha256=prompt_sha, winner=winner,
            scores=scores, position=position, cached=False,
        )
        self._cache[cache_key] = judgment
        return judgment
