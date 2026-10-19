"""Assurance modes and the human-verified learning signal (CF-SPEC-1, Phase 3).

A project chooses LLM judges, decision models, both or neither. The plan must run exactly what the
mode allows, and method selection may learn only from whether a method's verdict matched the
researcher's review, never from self-agreement (AV-1).
"""

import random

from app.core.assurance import (
    LLM_METHODS,
    ProjectAssurance,
    method_agreed_with_human,
    plan_validation,
    thompson_choice,
)


def _value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def test_no_policy_is_auto_and_matches_the_old_behaviour():
    plan = plan_validation(None)
    assert plan.mode == "auto" and plan.run_llm and plan.llm_methods == LLM_METHODS
    assert not plan.run_deciders and plan.unvalidated_reason is None and plan.validates


def test_mode_matrix():
    deciders = ("jev", "kev")
    llm = plan_validation(ProjectAssurance("llm_judges", llm_method="dual_run"))
    assert llm.run_llm and llm.llm_methods == ("dual_run",) and not llm.run_deciders

    only_deciders = plan_validation(ProjectAssurance("decision_models", decider_endpoint_ids=deciders))
    assert not only_deciders.run_llm and only_deciders.llm_methods == ()
    assert only_deciders.run_deciders and only_deciders.decider_endpoint_ids == deciders

    no_decider = plan_validation(ProjectAssurance("decision_models"))
    assert not no_decider.validates and no_decider.unvalidated_reason == "no_decider_configured"

    both = plan_validation(
        ProjectAssurance("both", llm_method="full_ensemble", llm_judges=5, decider_endpoint_ids=deciders)
    )
    assert both.run_llm and both.run_deciders and both.llm_judges == 5
    assert both.llm_methods == ("full_ensemble",)

    both_without = plan_validation(ProjectAssurance("both"))
    assert both_without.run_llm and not both_without.run_deciders
    assert both_without.notes == ["no_decider_configured"]

    off = plan_validation(ProjectAssurance("none", decider_endpoint_ids=deciders))
    assert not off.validates and off.unvalidated_reason == "assurance_disabled"

    auto_with_deciders = plan_validation(ProjectAssurance(decider_endpoint_ids=deciders))
    assert auto_with_deciders.run_llm and auto_with_deciders.run_deciders


def test_policy_values_are_validated_and_endpoint_ids_cleaned():
    assert _value_error(lambda: ProjectAssurance("judges_only"))
    assert _value_error(lambda: ProjectAssurance("llm_judges", llm_method="vote"))
    assert _value_error(lambda: ProjectAssurance("llm_judges", llm_judges=2))
    assert _value_error(lambda: ProjectAssurance("llm_judges", llm_judges=8))
    policy = ProjectAssurance("decision_models", decider_endpoint_ids=(" jev ", "", "jev", "kev"))
    assert policy.decider_endpoint_ids == ("jev", "kev")


def test_agreement_with_the_human_is_the_learning_signal():
    assert method_agreed_with_human(True, "approved") is True
    assert method_agreed_with_human(False, "approved") is False  # flagged something acceptable
    assert method_agreed_with_human(True, "needs_revision") is False  # passed a bad output
    assert method_agreed_with_human(False, "needs_revision") is True  # caught it
    assert method_agreed_with_human(False, "rejected_after_done") is True
    assert method_agreed_with_human(True, "system_failed") is None
    assert method_agreed_with_human(True, "") is None


def test_thompson_needs_human_outcomes_and_respects_the_allowed_set():
    rng = random.Random(3)
    assert thompson_choice(["self_moa", "dual_run"], {}, rng) is None
    assert thompson_choice(["dual_run"], {"self_moa": (40, 2)}, rng) is None
    counts = {"self_moa": (40, 2), "dual_run": (1, 1)}
    assert thompson_choice(["dual_run"], counts, rng) == "dual_run"


def test_thompson_prefers_the_method_researchers_agree_with():
    # Self-MoA agrees with itself most, but researchers sent back many outputs it passed.
    counts = {"self_moa": (10, 30), "full_ensemble": (30, 10)}
    rng = random.Random(7)
    picks = [thompson_choice(["self_moa", "full_ensemble"], counts, rng) for _ in range(500)]
    assert picks.count("full_ensemble") > 480
