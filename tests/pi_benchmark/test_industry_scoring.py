"""Tests for deterministic industry scoring (CF-324)."""

from __future__ import annotations

import tests.pi_benchmark.industry_scoring as scoring

import pytest

pytestmark = pytest.mark.benchmark


def test_extract_plain_json():
    assert scoring.extract_json_call('{"name": "f", "arguments": {"a": 1}}') == {
        "name": "f",
        "arguments": {"a": 1},
    }


def test_extract_from_fenced_and_prose():
    text = 'Sure!\n```json\n{"name": "f", "arguments": {}}\n```\nDone.'
    assert scoring.extract_json_call(text)["name"] == "f"


def test_extract_none_on_garbage():
    assert scoring.extract_json_call("no json here") is None
    assert scoring.extract_json_call("") is None


def test_bfcl_strict_match():
    truth = [
        {
            "calculate_triangle_area": {
                "base": [10],
                "height": [5],
                "unit": ["units", ""],
            }
        }
    ]
    out = '{"name": "calculate_triangle_area", "arguments": {"base": 10, "height": 5, "unit": "units"}}'
    result = scoring.score_bfcl(truth, out)
    assert result["score"] == 1.0
    assert result["name_accuracy"] == 1.0
    assert result["argument_validity"] == 1.0


def test_bfcl_allowed_alternative_value():
    truth = [{"f": {"unit": ["units", ""]}}]
    assert (
        scoring.score_bfcl(truth, '{"name": "f", "arguments": {"unit": ""}}')["score"]
        == 1.0
    )


def test_bfcl_wrong_function_scores_zero():
    truth = [{"f": {"a": [1]}}]
    result = scoring.score_bfcl(truth, '{"name": "g", "arguments": {"a": 1}}')
    assert result["score"] == 0.0
    assert result["error"] == "wrong_function"


def test_bfcl_argument_mismatch_partial():
    truth = [{"f": {"a": [1], "b": [2]}}]
    result = scoring.score_bfcl(truth, '{"name": "f", "arguments": {"a": 1, "b": 3}}')
    assert result["score"] == 0.0
    assert result["name_accuracy"] == 1.0
    assert result["argument_validity"] == 0.5


def test_bfcl_float_int_normalisation():
    truth = [{"f": {"n": [5]}}]
    assert (
        scoring.score_bfcl(truth, '{"name": "f", "arguments": {"n": 5.0}}')["score"]
        == 1.0
    )


def test_tau_action_match():
    assert (
        scoring.score_tau(
            ["book_reservation"], '{"action": "book_reservation", "rationale": "x"}'
        )["score"]
        == 1.0
    )


def test_tau_unexpected_action():
    result = scoring.score_tau(["cancel_reservation"], '{"action": "book_reservation"}')
    assert result["score"] == 0.0
    assert "unexpected_action" in result["error"]


def test_score_industry_record_routes_by_expected_keys():
    assert (
        scoring.score_industry_record(
            {"bfcl_ground_truth": [{"f": {}}]}, '{"name":"f","arguments":{}}'
        )["kind"]
        == "bfcl"
    )
    assert (
        scoring.score_industry_record(
            {"tau_expected_actions": ["a"]}, '{"action":"a"}'
        )["kind"]
        == "tau"
    )
    assert scoring.score_industry_record({}, "x") is None
