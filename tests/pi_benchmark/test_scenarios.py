"""Contract tests for the scenario packs (task B0-5). Pure tier-T0."""

from __future__ import annotations

import pytest

from tests.pi_benchmark.scenarios import PACK_NAMES, load_pack
from tests.pi_benchmark.scenarios import canonical

pytestmark = pytest.mark.benchmark


def test_canonical_pack_has_the_fifteen_production_ids():
    scenarios = load_pack("canonical")
    assert len(scenarios) == 15
    ids = {s.id for s in scenarios}
    assert ids == set(canonical._catalog_ids())


def test_canonical_scenarios_are_t0_and_carry_a_contract_check():
    for scenario in load_pack("canonical"):
        assert scenario.pack == "canonical"
        assert scenario.min_tier == "T0"
        assert scenario.contract_check is not None


def test_canonical_contract_checks_resolve_to_a_production_test():
    # Every canonical scenario must resolve to a real production test (winning plan §2.2
    # principle 4). If a mapped production test disappears this fails loudly.
    for scenario in load_pack("canonical"):
        result = scenario.contract_check("pi", 0)
        assert result.passed, f"{scenario.id} does not resolve: {result.detail}"
        assert result.outcome_class == "resolves"


def test_canonical_contract_check_flags_a_missing_production_test():
    # Drive the negative branch directly: a bogus mapping must report `unresolved`.
    check = canonical._make_check("x", "test_does_not_exist", "test_missing")
    result = check("legacy", 0)
    assert not result.passed
    assert result.outcome_class == "unresolved"


def test_behavioural_packs_declare_t2_and_have_no_offline_check():
    for pack in ("spine", "a2a"):
        scenarios = load_pack(pack)
        assert scenarios, f"{pack} pack is empty"
        for scenario in scenarios:
            assert scenario.pack == pack
            assert scenario.min_tier == "T2"
            assert scenario.contract_check is None


def test_pack_names_and_unknown_pack_raises():
    assert set(PACK_NAMES) == {"canonical", "spine", "a2a", "industry"}
    with pytest.raises(KeyError):
        load_pack("does-not-exist")
