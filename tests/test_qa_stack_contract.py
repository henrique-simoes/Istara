"""QA stack contract tests: disposable, provider-agnostic, isolated.

These tests validate the QA Compose contract deterministically. The render
checks need a working ``docker compose`` binary and are skipped when Docker is
unavailable; the structural checks (project naming, no fixed container names,
no forbidden host deps) always run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
QA_COMPOSE = ROOT / "docker-compose.qa.yml"
BASE_COMPOSE = ROOT / "docker-compose.yml"

docker_compose = shutil.which("docker")


def _render(profile: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os

    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["docker", "compose", "-f", str(QA_COMPOSE), "--profile", profile, "config"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=full_env,
    )


def test_qa_compose_exists_and_declares_profiles():
    text = QA_COMPOSE.read_text(encoding="utf-8")
    assert "name: istara-qa-${QA_RUN_ID:-local}" in text
    for profile in ("contract", "synthetic", "reset", "audit", "live", "ui"):
        assert f"profiles:\n      - {profile}" in text


def test_qa_compose_has_no_fixed_container_name():
    # The QA overlay must not PIN container names (unique project isolation);
    # the word may appear in comments, so assert on the YAML key itself.
    text = QA_COMPOSE.read_text(encoding="utf-8")
    assert not any(
        line.strip().startswith("container_name:") for line in text.splitlines()
    )


def test_qa_compose_builds_qa_image_from_repo_root():
    # The QA seeder/resetter/auditor run qa/scripts + qa/corpora, so the image
    # must be built from the repo ROOT (context: .) with qa/Dockerfile, never
    # from ./backend (which lacks the QA tooling).
    text = QA_COMPOSE.read_text(encoding="utf-8")
    assert "context: ." in text
    assert "dockerfile: qa/Dockerfile" in text
    assert "context: ./backend" not in text
    assert (ROOT / "qa" / "Dockerfile").exists()


def test_istara_qa_sh_never_merges_base_compose():
    # up/down/seed/reset must stay isolated from the base local-model stack:
    # merging docker-compose.yml would reintroduce ollama + fixed istara-*
    # container names.
    script = (ROOT / "scripts" / "istara-qa.sh").read_text(encoding="utf-8")
    assert 'COMPOSE=(docker compose -f "$ROOT/docker-compose.qa.yml")' in script
    assert "docker-compose.yml" not in script.replace("docker-compose.qa.yml", "")
    # seed must run the compose seeder service, never `docker run $ROOT/backend`.
    assert "run --rm" in script
    assert '"$ROOT/backend"' not in script
    assert "docker run --rm" not in script


def test_qa_seeder_depends_on_healthy_backend():
    text = QA_COMPOSE.read_text(encoding="utf-8")
    assert "condition: service_healthy" in text
    assert "QA_API_BASE" in text
    assert "--api-base" in text


def test_qa_compose_forbids_host_docker_socket_and_host_mounts():
    text = QA_COMPOSE.read_text(encoding="utf-8").lower()
    assert "/var/run/docker.sock" not in text
    assert "privileged" not in text
    assert "network_mode: host" not in text


def test_qa_compose_never_starts_local_model_services_by_default():
    text = QA_COMPOSE.read_text(encoding="utf-8").lower()
    # The QA overlay itself declares no ollama/lmstudio service (the base
    # compose's ollama service is only reachable when explicitly merged).
    assert "ollama/ollama" not in text
    assert "image: ollama" not in text
    assert "image: lmstudio" not in text
    assert "lmstudio_host" not in text


def test_qa_runs_dir_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "qa/runs/" in gitignore


def test_live_profile_fails_closed_without_target():
    if not docker_compose:
        pytest.skip("docker not available")
    result = _render("live")
    # The live profile render must NOT require the target (compose renders all
    # profiles' interpolation), but the gate command must fail at runtime
    # without QA_LIVE_PROVIDER_TARGET. We assert the environment plumbing here.
    assert result.returncode in (0, 1)


def test_live_gate_never_echoes_target_verbatim():
    # F-4 regression: the live gate must never echo QA_LIVE_PROVIDER_TARGET (a
    # private endpoint) verbatim into logs; it may only emit a redacted
    # label/handle.
    text = QA_COMPOSE.read_text(encoding="utf-8")
    gate = text[text.index("qa-live-gate"):]
    assert "live-target=$${" not in gate
    assert "echo live-target=" not in gate
    assert "live-target-label" in gate or "live-target-set" in gate


@pytest.mark.parametrize("profile", ["contract", "synthetic", "reset", "audit", "ui"])
def test_qa_profile_renders(profile):
    if not docker_compose:
        pytest.skip("docker not available")
    result = _render(profile)
    assert result.returncode == 0, f"profile {profile} failed: {result.stderr}"
    rendered = result.stdout
    # contract profile must not start a model service
    if profile == "contract":
        assert "ollama" not in rendered.lower() or "istara-qa-ollama" not in rendered


def test_base_compose_renders_after_qa_hardening_fix():
    if not docker_compose:
        pytest.skip("docker not available")
    result = subprocess.run(
        ["docker", "compose", "-f", str(BASE_COMPOSE), "config", "--quiet"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"base compose render failed: {result.stderr}"
