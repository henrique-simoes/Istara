"""Contract tests for the Pi-vs-Legacy benchmark metrics schema (task B0-1).

These are pure tier-T0 checks: no live model, server, network, or database. They pin the
schema-first foundation that every downstream benchmark asset validates against, including
acceptance A1's negative test ("reject a schema-violating record").
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft202012Validator

from tests.pi_benchmark import schema

pytestmark = pytest.mark.benchmark

_FIXTURE = Path(__file__).parent / "fixtures" / "example_run_record.json"


def _golden() -> dict:
    """A fresh, deep copy of the conformant golden record for each mutation test."""
    with _FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


# --- the schema itself -------------------------------------------------------------


def test_schema_file_is_valid_json_schema():
    doc = schema.load_schema()
    # Raises jsonschema.SchemaError if the contract is itself malformed.
    Draft202012Validator.check_schema(doc)
    assert doc["title"] == "Pi-vs-Legacy benchmark run record"


def test_schema_path_points_at_the_deliverable():
    assert schema.SCHEMA_PATH.name == "metrics-schema.json"
    assert schema.SCHEMA_PATH.parent.name == "comparison-Istara-pi"
    assert schema.SCHEMA_PATH.is_file()


# --- the golden record validates ---------------------------------------------------


def test_golden_record_validates():
    record = _golden()
    assert schema.is_valid(record)
    # validate_record returns the record unchanged on success.
    assert schema.validate_record(record) is record


def test_golden_not_runnable_variant_validates():
    record = _golden()
    record["status"] = "not_runnable"
    record["not_runnable_reason"] = "engine_unsupported"
    record["usage"] = {"estimate": True, "estimator": "n/a"}
    del record["metrics"]
    assert schema.is_valid(record)


# --- negative tests: acceptance A1 -------------------------------------------------


@pytest.mark.parametrize("missing", ["tier", "engine", "phase", "pack", "usage", "provenance"])
def test_missing_required_top_level_field_is_rejected(missing):
    record = _golden()
    del record[missing]
    assert not schema.is_valid(record)
    with pytest.raises(ValidationError):
        schema.validate_record(record)


def test_unknown_tier_is_rejected():
    record = _golden()
    record["tier"] = "T4"
    assert not schema.is_valid(record)


def test_unknown_engine_is_rejected():
    record = _golden()
    record["engine"] = "pi-v2"
    assert not schema.is_valid(record)


def test_not_runnable_without_reason_is_rejected():
    record = _golden()
    record["status"] = "not_runnable"
    # no not_runnable_reason supplied -> the if/then must fire
    assert not schema.is_valid(record)


def test_not_runnable_reason_must_be_a_known_enum():
    record = _golden()
    record["status"] = "not_runnable"
    record["not_runnable_reason"] = "i_felt_like_it"
    assert not schema.is_valid(record)


def test_usage_without_estimate_flag_is_rejected():
    record = _golden()
    record["usage"].pop("estimate")
    assert not schema.is_valid(record)


def test_unknown_top_level_field_is_rejected():
    record = _golden()
    record["totally_new_field"] = 1
    assert not schema.is_valid(record)


def test_negative_token_count_is_rejected():
    record = _golden()
    record["usage"]["total_tokens"] = -1
    assert not schema.is_valid(record)


def test_non_hex_input_sha256_is_rejected():
    record = _golden()
    record["provenance"]["input_sha256"] = "not-a-real-hash"
    assert not schema.is_valid(record)


def test_feature_criteria_score_out_of_range_is_rejected():
    record = _golden()
    record["metrics"]["feature_integration"] = {
        "feature_id": "chat.stream",
        "criteria": "auto",
        "criteria_scores": {"reachable": 1.5},
    }
    assert not schema.is_valid(record)


def test_paired_stats_shape_is_enforced():
    good = _golden()
    good["paired_stats"] = {
        "delta": 0.1,
        "effect_size": 0.3,
        "bootstrap_ci": {"low": -0.05, "high": 0.25, "resamples": 10000},
        "no_detected_difference": True,
    }
    assert schema.is_valid(good)

    bad = copy.deepcopy(good)
    bad["paired_stats"]["bootstrap_ci"].pop("resamples")
    assert not schema.is_valid(bad)
