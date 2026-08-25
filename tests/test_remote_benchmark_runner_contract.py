"""Static safety contract for the Docker-only Mac Studio benchmark runner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_remote_runner_uses_one_disposable_container_per_engine():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert 'for engine in "${ENGINES[@]}"' in outer
    assert '-e ISTARA_BENCHMARK_ENGINE="$engine"' in outer
    assert '"probe:${ISTARA_BENCHMARK_ENGINE}"' in inner
    assert "probe:legacy" not in inner
    assert "probe:pi" not in inner


def test_remote_runner_collects_both_arms_before_returning_failure():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert "arm_failures=0" in outer
    assert "if docker run --rm" in outer
    assert "arm_failures=$((arm_failures + 1))" in outer
    assert 'if [ "$arm_failures" -ne 0 ]; then' in outer


def test_remote_runner_records_images_source_and_truthful_isolation():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    for variable in (
        "ISTARA_BENCHMARK_RUNNER_IMAGE",
        "ISTARA_BENCHMARK_RUNNER_IMAGE_ID",
        "ISTARA_BENCHMARK_BACKEND_IMAGE_ID",
        "ISTARA_BENCHMARK_FRONTEND_IMAGE_ID",
        "ISTARA_BENCHMARK_SOURCE_STATE",
        "ISTARA_BENCHMARK_STATE_ISOLATION",
        "ISTARA_BENCHMARK_RUN_GROUP",
        "ISTARA_BENCHMARK_REQUIRE_REPRODUCIBLE_RUN",
    ):
        assert variable in outer

    assert "fresh-postgres-container-per-engine" in outer
    assert "ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256" in outer
    assert "ISTARA_BENCHMARK_RUN_ORDER" in outer
    assert "ISTARA_BENCHMARK_ARM_INDEX" in outer
    assert "ISTARA_BENCHMARK_FRESH_SANDBOX=0" not in outer


def test_remote_runner_recreates_the_database_before_each_engine():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'reset_stack_for_engine "$engine"' in outer
    assert 'docker compose --project-name "$PROJECT"' in outer
    assert "--force-recreate" in outer
    assert "--wait" in outer
    assert "postgres provider-stub backend frontend caddy" in outer


def test_remote_runner_never_installs_or_authenticates_on_the_host():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert "curl " not in outer
    assert "python3 " not in outer
    assert "\nnpm " not in outer
    assert "playwright install" not in outer
    assert 'src="$REPO_ROOT",dst=/source,readonly' in outer
    assert "type=volume,dst=/work" in outer


def test_remote_runner_passes_admin_credentials_under_marathon_names():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert '-e ADMIN_PASSWORD="$ISTARA_ADMIN_PASSWORD"' in outer
    assert '-e ISTARA_TEST_ADMIN_PASSWORD="$ISTARA_ADMIN_PASSWORD"' in outer


def test_remote_runner_bounds_live_chat_waits_without_disabling_long_horizon():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert (
        'ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="${ISTARA_BENCHMARK_CHAT_TIMEOUT_MS:-300000}"'
        in inner
    )
    assert '-e ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="$ISTARA_BENCHMARK_CHAT_TIMEOUT_MS"' in outer
    assert "ISTARA_BENCHMARK_CHAT_TIMEOUT_MS=none" not in inner


def test_remote_runner_bounds_live_research_scope_without_disabling_three_model_proof():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert 'ISTARA_BENCHMARK_CODING_LIMIT="${ISTARA_BENCHMARK_CODING_LIMIT:-3}"' in outer
    assert 'ISTARA_BENCHMARK_MAX_UPLOADS="${ISTARA_BENCHMARK_MAX_UPLOADS:-6}"' in outer
    assert '-e ISTARA_BENCHMARK_CODING_LIMIT="$ISTARA_BENCHMARK_CODING_LIMIT"' in outer
    assert '-e ISTARA_BENCHMARK_MAX_UPLOADS="$ISTARA_BENCHMARK_MAX_UPLOADS"' in outer
    assert '--coding-limit "$ISTARA_BENCHMARK_CODING_LIMIT"' in inner
    assert '--max-uploads "$ISTARA_BENCHMARK_MAX_UPLOADS"' in inner


def test_provider_stub_source_is_present_in_the_root_docker_build_context():
    ignored = {
        line.strip().rstrip("/")
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "qa" not in ignored
    assert (ROOT / "qa/scripts/provider_stub.py").is_file()


def test_backend_image_uses_a_pi_supported_node_runtime():
    dockerfile = (ROOT / "backend/Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:24-slim AS node-runtime" in dockerfile
    assert "npm ci --engine-strict --omit=dev --ignore-scripts" in dockerfile
    assert dockerfile.count("COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node") == 2
    assert "libmagic1 nodejs" not in dockerfile


def test_ephemeral_postgres_data_is_writable_tmpfs_not_a_host_volume():
    compose = (ROOT / "docker-compose.vps.yml").read_text(encoding="utf-8")

    assert "/var/lib/postgresql/data:noexec,nosuid,size=1G" in compose
    assert "postgres-data:" not in compose
