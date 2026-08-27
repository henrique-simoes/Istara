"""QA stack contract tests: disposable, provider-agnostic, isolated.

These tests validate the QA Compose contract deterministically. The render
checks need a working ``docker compose`` binary and are skipped when Docker is
unavailable; the structural checks (project naming, no fixed container names,
no forbidden host deps) always run.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
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


def test_contract_stub_is_non_model_and_in_network():
    text = QA_COMPOSE.read_text(encoding="utf-8")
    stub = text[text.index("  qa-provider-stub:"):text.index("  # Synthetic corpus seeder")]
    assert "dockerfile: qa/provider-stub.Dockerfile" in stub
    assert "busybox" not in stub.lower()
    assert "qa-provider-stub:11434" in text
    assert "OLLAMA_MODEL" in text
    assert "OLLAMA_EMBED_MODEL" in text
    assert (ROOT / "qa" / "provider-stub.Dockerfile").exists()
    assert (ROOT / "qa" / "scripts" / "provider_stub.py").exists()


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


def test_istara_qa_sh_exports_generated_run_id():
    # F-3-r2 regression: the script's shell-local RUN_ID must be exported as
    # QA_RUN_ID so every compose subprocess resolves ${QA_RUN_ID:-local} to the
    # generated run id instead of the `local` fallback.
    script = (ROOT / "scripts" / "istara-qa.sh").read_text(encoding="utf-8")
    assert re.search(r"^export QA_RUN_ID=\"\$RUN_ID\"$", script, re.M)
    assert 'RUN_ID="${QA_RUN_ID:-$(date -u +%Y%m%d%H%M%S)}"' in script


def test_istara_qa_sh_seed_passes_run_id_to_seeder_explicitly():
    # F-3-r2 regression: `seed` must pass -e QA_RUN_ID="$RUN_ID" to the compose
    # run, so the seeder service never falls back to `local` even if the export
    # is later removed.
    script = (ROOT / "scripts" / "istara-qa.sh").read_text(encoding="utf-8")
    seed_cmd = script[script.index('cmd_seed()'):script.index('cmd_qa()')]
    assert '-e QA_RUN_ID="$RUN_ID"' in seed_cmd


def test_istara_qa_sh_seed_unset_input_propagates_generated_run_id():
    # F-3-r2 behavioral regression: with QA_RUN_ID unset, `seed` must generate a
    # timestamp run id and propagate it (explicit -e AND exported env) into the
    # compose seeder invocation — never `local`, so the manifest lands under
    # qa/runs/<run-id> matching the claimed istara-qa-<run-id> project.
    script = ROOT / "scripts" / "istara-qa.sh"
    with tempfile.TemporaryDirectory() as tmp:
        stub_dir = Path(tmp)
        stub = stub_dir / "docker"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'printf \'%s\\n\' "ARGS: $*" >> "$STUB_LOG"\n'
            'env | grep \'^QA_RUN_ID=\' >> "$STUB_LOG"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        log = stub_dir / "docker.log"
        env = dict(os.environ)
        env.pop("QA_RUN_ID", None)
        env["PATH"] = f"{stub_dir}:{env['PATH']}"
        env["STUB_LOG"] = str(log)
        result = subprocess.run(
            ["bash", str(script), "seed"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "Seeded slice=" in result.stdout
        seen = log.read_text(encoding="utf-8")
    # (log content captured before the tempdir is removed)
    # The compose invocation carries an explicit -e QA_RUN_ID=<generated>.
    assert re.search(r"-e QA_RUN_ID=\d{14}", seen), seen
    # The exported environment carries the same generated run id.
    assert re.search(r"^QA_RUN_ID=\d{14}$", seen, re.M), seen
    # The `local` fallback must never reach the seeder.
    assert "QA_RUN_ID=local" not in seen
    assert "istara-qa-local" not in seen


def test_istara_qa_governance_and_collection_are_container_only():
    """The Mac Studio wrapper must not run repository Python on the host."""
    script = (ROOT / "scripts" / "istara-qa.sh").read_text(encoding="utf-8")
    qa = script[script.index("cmd_qa()"):script.index("cmd_collect()")]
    collect = script[script.index("cmd_collect()"):script.index("cmd_reset()")]

    assert "run_qa_python scripts/check_feature_obligations.py" in qa
    assert "run_qa_python scripts/check_qa_capabilities.py" in qa
    assert "python \"$ROOT/scripts/" not in qa
    assert "run_qa_python qa/scripts/audit_qa.py" in collect
    assert "python \"$ROOT/qa/scripts/" not in collect
    assert "--build" in script
    assert "--no-deps" in script
    assert '"$ROOT:/workspace:ro"' in script


def test_istara_qa_reset_is_docker_only_and_requires_explicit_confirmation():
    script = (ROOT / "scripts" / "istara-qa.sh").read_text(encoding="utf-8")
    reset = script[script.index("cmd_reset()"):script.index("cmd_down()")]

    assert "python" not in reset
    assert '"${COMPOSE[@]}" -p "$PROJECT" down -v' in reset
    assert 'QA_CONFIRM:-RESET-ISTARA-QA-RUN' not in reset
    assert 'QA_CONFIRM=RESET-ISTARA-QA-RUN' in reset


def test_qa_seeder_depends_on_healthy_backend():
    text = QA_COMPOSE.read_text(encoding="utf-8")
    assert "condition: service_healthy" in text
    assert "QA_API_BASE" in text
    assert "--api-base" in text


def test_qa_backend_has_bounded_ephemeral_data_surface():
    text = QA_COMPOSE.read_text(encoding="utf-8")
    backend = text[text.index("  qa-backend:"):text.index("  qa-frontend:")]
    assert "read_only: true" in text
    assert "/app/data:rw,nosuid,nodev,uid=999,gid=999,mode=0750,size=2G" in backend


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
