"""Static safety contract for the Docker-only Mac Studio benchmark runner."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_remote_runner_uses_one_disposable_container_per_engine():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert 'for engine in "${ENGINES[@]}"' in outer
    assert '-e "ISTARA_BENCHMARK_ENGINE=$engine"' in outer
    assert '-e "ISTARA_LONG_HORIZON_ENGINE=$engine"' in outer
    assert 'PROBE_SCRIPT="${ISTARA_BENCHMARK_PROBE_SCRIPT:-probe:${ISTARA_BENCHMARK_ENGINE}}"' in inner
    assert 'npm --prefix tests/real_user_benchmark run "$PROBE_SCRIPT"' in inner
    assert '/opt/runner-venv/bin/python tests/benchmarks/long_horizon_runner.py' in inner
    assert 'tee "$LONG_HORIZON_RESULTS/${ISTARA_LONG_HORIZON_ENGINE}.log"' in inner
    assert "probe:legacy" not in inner
    assert "probe:pi" not in inner


def test_remote_runner_collects_both_arms_before_returning_failure():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert "arm_failures=0" in outer
    assert 'if docker run "${runner_docker_args[@]}"' in outer
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
    assert "ISTARA_BENCHMARK_SOURCE_SHA" in outer
    assert 'git -C "$REPO_ROOT" rev-parse HEAD' in outer
    assert "ISTARA_BENCHMARK_RUN_ORDER" in outer
    assert "ISTARA_BENCHMARK_ARM_INDEX" in outer
    assert "ISTARA_BENCHMARK_FRESH_SANDBOX=0" not in outer


def test_remote_runner_verifies_snapshot_hash_against_the_checked_out_source():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'git -C "$REPO_ROOT" archive --format=tar HEAD' in outer
    assert "shasum -a 256" in outer
    assert "sha256sum" in outer
    assert "source snapshot sha256 does not match" in outer


def test_remote_runner_fails_closed_on_dirty_source_checkout():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'git -C "$REPO_ROOT" status --porcelain --untracked-files=all' in outer
    assert "refusing dirty source checkout" in outer


def test_remote_runner_bootstraps_ignored_result_mounts_from_pristine_checkout():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'mkdir -p "$PROBE_RESULTS" "$SIM_RESULTS" "$MARATHON_RESULTS"' in outer
    assert "required result directory missing" not in outer


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
    assert '"type=bind,src=$REPO_ROOT,dst=/source,readonly"' in outer
    assert "type=volume,dst=/work" in outer


def test_remote_runner_passes_admin_credentials_under_marathon_names():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert '--env-file "$RUNNER_ENV_FILE"' in outer
    assert 'mktemp' in outer
    assert 'chmod 600 "$RUNNER_ENV_FILE"' in outer
    assert '-e ADMIN_PASSWORD="$ISTARA_ADMIN_PASSWORD"' not in outer
    assert '-e ISTARA_TEST_ADMIN_PASSWORD="$ISTARA_ADMIN_PASSWORD"' not in outer


def test_remote_runner_bounds_live_chat_waits_without_disabling_long_horizon():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert (
        'ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="${ISTARA_BENCHMARK_CHAT_TIMEOUT_MS:-300000}"'
        in inner
    )
    assert '-e "ISTARA_BENCHMARK_CHAT_TIMEOUT_MS=$ISTARA_BENCHMARK_CHAT_TIMEOUT_MS"' in outer
    assert "ISTARA_BENCHMARK_CHAT_TIMEOUT_MS=none" not in inner


def test_remote_runner_bounds_live_research_scope_without_disabling_three_model_proof():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert 'ISTARA_BENCHMARK_CODING_LIMIT="${ISTARA_BENCHMARK_CODING_LIMIT:-3}"' in outer
    assert 'ISTARA_BENCHMARK_MAX_UPLOADS="${ISTARA_BENCHMARK_MAX_UPLOADS:-6}"' in outer
    assert '-e "ISTARA_BENCHMARK_CODING_LIMIT=$ISTARA_BENCHMARK_CODING_LIMIT"' in outer
    assert '-e "ISTARA_BENCHMARK_MAX_UPLOADS=$ISTARA_BENCHMARK_MAX_UPLOADS"' in outer
    assert '--coding-limit "$ISTARA_BENCHMARK_CODING_LIMIT"' in inner
    assert '--max-uploads "$ISTARA_BENCHMARK_MAX_UPLOADS"' in inner


def test_remote_runner_requires_compute_donation_by_default_and_forwards_topology_inputs():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'ISTARA_BENCHMARK_ACCEPTANCE_PROFILE="${ISTARA_BENCHMARK_ACCEPTANCE_PROFILE:-combined}"' in outer
    assert 'provider) ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0' in outer
    assert 'petals|combined) ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=1' in outer
    assert 'if [[ -z "${ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION:-}" ]]' in outer
    assert '-e "ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE"' in outer
    assert '-e "ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=$ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION"' in outer
    assert 'ISTARA_BENCHMARK_START_CLIENT_SANDBOXES="${ISTARA_BENCHMARK_START_CLIENT_SANDBOXES:-$ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION}"' in outer
    assert "ISTARA_BENCHMARK_DONOR_" in outer
    assert "ISTARA_BENCHMARK_DONOR_PROFILES_FILE" in outer
    assert "ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRINGS" in outer


def test_remote_runner_scopes_long_horizon_to_the_combined_acceptance_profile():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert 'if [[ -z "${ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON:-}" ]]' in outer
    assert 'combined) ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON=1' in outer
    assert 'provider|petals) ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON=0' in outer
    assert '-e "ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON=$ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON"' in outer
    assert 'LONG_HORIZON skipped for acceptance profile=' in inner
    assert 'ISTARA_LONG_HORIZON_ENGINE must be legacy or pi' in inner


def test_remote_runner_keeps_python_dependencies_inside_the_disposable_image():
    dockerfile = (ROOT / "scripts/runner/Dockerfile").read_text(encoding="utf-8")
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert "python3-venv" in dockerfile
    assert "python3 -m venv /opt/runner-venv" in dockerfile
    assert '"httpx==0.28.1"' in dockerfile
    assert "python3 " not in outer


def test_remote_runner_proves_nested_docker_contract_before_required_donor_run():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "scripts/runner/Dockerfile").read_text(encoding="utf-8")

    assert "var/run/docker.sock" in outer
    assert "docker info" in outer
    assert "NESTED_DOCKER_MOUNTS" in outer
    assert "RUNNER_IMAGE_REQUEST" in outer
    assert "apt-get install" in dockerfile
    assert "docker.io" in dockerfile


def test_remote_runner_handles_optional_nested_mounts_under_bash_nounset():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert "runner_docker_args=(" in outer
    assert 'runner_docker_args+=( "${NESTED_DOCKER_MOUNTS[@]}" )' in outer
    assert 'docker run "${runner_docker_args[@]}"' in outer
    assert '    "${NESTED_DOCKER_MOUNTS[@]}" \\\n' not in outer


def test_remote_runner_handles_optional_compose_arrays_under_bash_nounset():
    outer = (ROOT / "scripts/runner/docker-run.sh").read_text(encoding="utf-8")

    assert 'local compose_args=(docker compose --project-name "$PROJECT")' in outer
    assert 'if ((${#COMPOSE_PROFILE_ARGS[@]})); then' in outer
    assert 'compose_args+=("${COMPOSE_PROFILE_ARGS[@]}")' in outer
    assert 'if ((${#COMPOSE_DONOR_SERVICES[@]})); then' in outer
    assert 'compose_args+=("${COMPOSE_DONOR_SERVICES[@]}")' in outer
    assert '"${compose_args[@]}"' in outer
    assert '    "${COMPOSE_PROFILE_ARGS[@]}" \\\n' not in outer
    assert '    postgres provider-stub backend frontend caddy "${COMPOSE_DONOR_SERVICES[@]}"' not in outer


def test_manual_marathon_wrapper_fails_closed_outside_docker():
    wrapper = (ROOT / "scripts/marathon/start-marathon.sh").read_text(encoding="utf-8")
    inner = (ROOT / "scripts/runner/inside.sh").read_text(encoding="utf-8")

    assert "ISTARA_MARATHON_CONTAINERIZED" in wrapper
    assert "refusing host marathon" in wrapper
    assert "! -f /.dockerenv" in wrapper
    assert "export ISTARA_MARATHON_CONTAINERIZED=1" in inner


def test_provider_stub_source_is_present_in_the_root_docker_build_context():
    ignored = {
        line.strip().rstrip("/")
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "qa" not in ignored
    assert (ROOT / "qa/scripts/provider_stub.py").is_file()


def test_qa_entrypoint_is_reincluded_in_the_root_docker_build_context():
    lines = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "scripts/*" in lines
    assert "!scripts/istara-qa.sh" in lines
    assert (ROOT / "scripts/istara-qa.sh").is_file()


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
