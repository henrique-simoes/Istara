from __future__ import annotations

from scripts.check_public_tree_clean import path_is_blocked


def test_public_tree_clean_blocks_runtime_model_and_eval_artifacts() -> None:
    blocked_paths = {
        "LLMs/model.gguf": "personal, runtime, model, or local tool directory",
        "Model_Finetuning/run/config.json": "personal, runtime, model, or local tool directory",
        "backend/data/istara.db": "personal, runtime, model, or local tool directory",
        "data/uploads/research.pdf": "personal, runtime, model, or local tool directory",
        "uploads/research.pdf": "personal, runtime, model, or local tool directory",
        "storage/lancedb/index.json": "personal, runtime, model, or local tool directory",
        "tests/evals/.results/run/manifest.json": "personal, runtime, model, or local tool directory",
        "tests/simulation/.results/run/report.json": "personal, runtime, model, or local tool directory",
        ".istara-backend.log": "local/runtime control file",
        "backend/.env.local": "local/runtime control file",
    }

    for path, reason in blocked_paths.items():
        assert path_is_blocked(path) == reason


def test_public_tree_clean_allows_source_and_fixture_files() -> None:
    allowed_paths = [
        "backend/app/main.py",
        "frontend/src/components/common/SettingsView.tsx",
        "tests/simulation/data/fixtures/interview.txt",
        "security/SECURITY_BENCHMARK.md",
    ]

    for path in allowed_paths:
        assert path_is_blocked(path) is None
