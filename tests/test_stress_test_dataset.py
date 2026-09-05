"""Test suite for the 150-Turn Agentic Engine Stress Test dataset."""

import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent / "data" / "stress_test_150_turns"
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_corpus_manifest_integrity():
    manifest_path = DATA_DIR / "corpus_manifest.json"
    assert manifest_path.exists(), "corpus_manifest.json is missing"
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_selected"] >= 30
    assert len(data["sources"]) == data["total_selected"]

    methods = set()
    for src in data["sources"]:
        assert src["id"].startswith("CR-")
        assert src["title"]
        assert src["method"]
        methods.add(src["method"])
        rel_path = src["relative_path"]
        assert (REPO_ROOT / rel_path).exists(), f"Source file {rel_path} does not exist on disk"

    # Must cover diverse qualitative and quantitative methods
    expected_methods = {"interview", "usability", "accessibility", "competitor", "diary"}
    assert expected_methods.issubset(methods), f"Missing methods: {expected_methods - methods}"


def test_simulated_surveys_100_integrity():
    surveys_path = DATA_DIR / "simulated_surveys_100.json"
    assert surveys_path.exists(), "simulated_surveys_100.json is missing"
    with open(surveys_path, encoding="utf-8") as f:
        surveys = json.load(f)

    assert len(surveys) == 100, f"Expected 100 surveys, found {len(surveys)}"

    resp_ids = set()
    part_ids = set()
    roles = set()
    languages = set()

    for r in surveys:
        assert r["response_id"] not in resp_ids, f"Duplicate response_id: {r['response_id']}"
        assert r["participant_id"] not in part_ids, f"Duplicate participant_id: {r['participant_id']}"
        resp_ids.add(r["response_id"])
        part_ids.add(r["participant_id"])

        demo = r["demographics"]
        roles.add(demo["role"])
        languages.add(demo["language"])

        metrics = r["metrics"]
        assert 1 <= metrics["readiness_clarity"] <= 5
        assert 1 <= metrics["caregiver_proxy_comfort"] <= 5
        assert 1 <= metrics["audit_trail_importance"] <= 5
        assert 1 <= metrics["notification_satisfaction"] <= 5
        assert 0 <= metrics["nps_rating"] <= 10

        answers = r["answers"]
        assert len(answers) >= 5
        for a in answers:
            assert a["question"]
            assert a["answer"]

    assert {"patient", "family_caregiver", "healthcare_proxy"}.issubset(roles)
    assert {"en", "es", "pt-BR"}.issubset(languages)


def test_usability_testing_20_integrity():
    usability_path = DATA_DIR / "usability_testing_20.json"
    assert usability_path.exists(), "usability_testing_20.json is missing"
    with open(usability_path, encoding="utf-8") as f:
        sessions = json.load(f)

    assert len(sessions) == 20, f"Expected 20 usability sessions, found {len(sessions)}"

    for s in sessions:
        assert s["session_id"].startswith("US-")
        assert s["persona"]
        assert len(s["tasks"]) == 3
        for t in s["tasks"]:
            assert "duration_seconds" in t
            assert "success" in t
            assert "errors" in t
            assert t["verbatim"]

        metrics = s["metrics"]
        assert 0.0 <= metrics["sus_score"] <= 100.0
        assert 0.0 <= metrics["umux_score"] <= 100.0
        assert metrics["total_duration_seconds"] > 0


def test_codebook_lifecycle_integrity():
    cb_path = DATA_DIR / "codebook_lifecycle.json"
    assert cb_path.exists(), "codebook_lifecycle.json is missing"
    with open(cb_path, encoding="utf-8") as f:
        cb = json.load(f)

    stages = cb["stages"]
    assert "v1_0_initial" in stages
    assert "v1_1_steered" in stages
    assert "v2_0_consolidated" in stages

    v1_codes = {c["name"] for c in stages["v1_0_initial"]["codes"]}
    v11_codes = {c["name"] for c in stages["v1_1_steered"]["codes"]}
    v2_codes = {c["name"] for c in stages["v2_0_consolidated"]["codes"]}

    assert "caregiver-privacy" in v1_codes
    assert "caregiver-proxy-scheduling" in v11_codes
    assert "caregiver-confidential-notes" in v11_codes
    assert "accessibility-contrast-deficiency" in v2_codes
    assert "audit-immutability-governance" in v2_codes

    for stage_name, stage_data in stages.items():
        for c in stage_data["codes"]:
            assert c["definition"]
            assert c["inclusion_criteria"]
            assert c["exclusion_criteria"]
            assert len(c["anchor_quotes"]) >= 1


def test_trajectory_150_turns_integrity():
    traj_path = DATA_DIR / "trajectory_150_turns.json"
    assert traj_path.exists(), "trajectory_150_turns.json is missing"
    with open(traj_path, encoding="utf-8") as f:
        trajectory = json.load(f)

    assert len(trajectory) == 150, f"Expected 150 turns, found {len(trajectory)}"

    steering_count = 0
    phase_counts = {"discover": 0, "define": 0, "develop": 0, "deliver": 0}

    for idx, turn in enumerate(trajectory, start=1):
        assert turn["turn_index"] == idx
        assert turn["phase"] in phase_counts
        phase_counts[turn["phase"]] += 1
        assert len(turn["user_prompt"]) > 20
        assert turn["expected_tool"]
        if turn.get("steering"):
            steering_count += 1
            st = turn["steering"]
            assert "type" in st
            assert "injection_text" in st
            assert "verification_criterion" in st

    assert phase_counts["discover"] == 40
    assert phase_counts["define"] == 40
    assert phase_counts["develop"] == 35
    assert phase_counts["deliver"] == 35
    assert steering_count >= 30, f"Expected at least 30 steering interventions, found {steering_count}"
