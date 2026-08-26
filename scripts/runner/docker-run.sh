#!/bin/bash
# Phase 7 runner: marathon + real-user probes INSIDE Docker. The checkout is
# mounted read-only and copied into an anonymous container volume before the
# browser automation run, so neither dependencies nor browser packages can land on the
# Mac Studio host. Only benchmark result directories are writable bind mounts.
set -euo pipefail

PROJECT="${ISTARA_STACK_PROJECT:-istara-testing}"
BACKEND_NET="${PROJECT}_backend-net"
FRONTEND_NET="${PROJECT}_frontend-net"
API_URL="${ISTARA_API_URL:-http://backend:8000}"
FRONTEND_URL="${ISTARA_FRONTEND_URL:-http://frontend:3000}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROBE_RESULTS="$REPO_ROOT/tests/real_user_benchmark/.results"
SIM_RESULTS="$REPO_ROOT/tests/simulation/.results"
MARATHON_RESULTS="$REPO_ROOT/data/test-marathon"

# These mounts are generated/ignored artifacts, so a pristine detached checkout must be
# able to bootstrap them without manual host preparation. Docker remains the only runtime;
# this creates empty bind-mount targets and all work happens in containers below.
mkdir -p "$PROBE_RESULTS" "$SIM_RESULTS" "$MARATHON_RESULTS"

: "${ISTARA_ADMIN_PASSWORD:?set ISTARA_ADMIN_PASSWORD}"
ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="${ISTARA_BENCHMARK_CHAT_TIMEOUT_MS:-300000}"
# Three source evidence units are the smallest useful live Fleiss-kappa proof:
# each is still coded independently by all three selected model identities.
# Keep uploads larger than that scope so source ingestion is also exercised,
# without turning a smoke/proof arm into an unbounded corpus benchmark.
ISTARA_BENCHMARK_CODING_LIMIT="${ISTARA_BENCHMARK_CODING_LIMIT:-3}"
ISTARA_BENCHMARK_MAX_UPLOADS="${ISTARA_BENCHMARK_MAX_UPLOADS:-6}"

case "${ISTARA_MARATHON_ENGINE:-both}" in
  both) ENGINES=(legacy pi) ;;
  legacy|pi) ENGINES=("${ISTARA_MARATHON_ENGINE}") ;;
  *) echo "ISTARA_MARATHON_ENGINE must be legacy, pi, or both" >&2; exit 2 ;;
esac

RUN_GROUP="${ISTARA_BENCHMARK_RUN_GROUP:-docker-comparison-$(date -u +%Y%m%dT%H%M%SZ)}"
RUNNER_IMAGE_REQUEST="${ISTARA_RUNNER_IMAGE:-node:20-bookworm}"
: "${ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256:?set the sha256 of the exact source snapshot copied to the Mac Studio}"
SOURCE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)" || {
  echo "unable to resolve the exact source commit for benchmark provenance" >&2
  exit 1
}
COMPOSE_FILE="${ISTARA_BENCHMARK_COMPOSE_FILE:-$REPO_ROOT/docker-compose.vps.yml}"
COMPOSE_ENV_FILE="${ISTARA_BENCHMARK_COMPOSE_ENV_FILE:-$REPO_ROOT/.env.deploy}"
RESET_STACK="${ISTARA_BENCHMARK_RESET_STACK:-1}"
RUN_ORDER="$(IFS=,; echo "${ENGINES[*]}")"

# Never place credentials in the docker CLI argument vector: macOS process listings expose
# command-line values to other local users. Docker reads this short-lived, mode-600 file and
# the EXIT trap removes it after both comparison arms complete.
umask 077
RUNNER_ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/istara-benchmark-env.XXXXXX")"
chmod 600 "$RUNNER_ENV_FILE"
cleanup_runner_env() { rm -f "$RUNNER_ENV_FILE"; }
trap cleanup_runner_env EXIT
printf 'ISTARA_ADMIN_PASSWORD=%s\nADMIN_PASSWORD=%s\nISTARA_TEST_ADMIN_PASSWORD=%s\n' \
  "$ISTARA_ADMIN_PASSWORD" "$ISTARA_ADMIN_PASSWORD" "$ISTARA_ADMIN_PASSWORD" > "$RUNNER_ENV_FILE"

docker pull "$RUNNER_IMAGE_REQUEST" >/dev/null
RUNNER_IMAGE="$(docker image inspect --format '{{index .RepoDigests 0}}' "$RUNNER_IMAGE_REQUEST")"
RUNNER_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$RUNNER_IMAGE_REQUEST")"

reset_stack_for_engine() {
  local engine="$1"
  case "$RESET_STACK" in
    1|true|yes) ;;
    *)
      echo "refusing non-isolated comparison: ISTARA_BENCHMARK_RESET_STACK must be enabled" >&2
      exit 2
      ;;
  esac
  [ -f "$COMPOSE_FILE" ] || { echo "compose file missing: $COMPOSE_FILE" >&2; exit 1; }
  [ -f "$COMPOSE_ENV_FILE" ] || { echo "compose env file missing: $COMPOSE_ENV_FILE" >&2; exit 1; }
  echo "[runner] recreating fresh database stack for engine=$engine"
  docker compose --project-name "$PROJECT" \
    --env-file "$COMPOSE_ENV_FILE" \
    -f "$COMPOSE_FILE" \
    up -d --force-recreate --wait \
    postgres provider-stub backend frontend caddy
}

docker volume create istara-pw-browsers >/dev/null 2>&1 || true

arm_index=0
arm_failures=0
for engine in "${ENGINES[@]}"; do
  arm_index=$((arm_index + 1))
  reset_stack_for_engine "$engine"
  BACKEND_CONTAINER="$(docker ps -q --filter "label=com.docker.compose.project=$PROJECT" --filter 'label=com.docker.compose.service=backend' | head -n 1)"
  FRONTEND_CONTAINER="$(docker ps -q --filter "label=com.docker.compose.project=$PROJECT" --filter 'label=com.docker.compose.service=frontend' | head -n 1)"
  [ -n "$BACKEND_CONTAINER" ] || { echo "backend container not found for Compose project $PROJECT" >&2; exit 1; }
  [ -n "$FRONTEND_CONTAINER" ] || { echo "frontend container not found for Compose project $PROJECT" >&2; exit 1; }
  BACKEND_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$BACKEND_CONTAINER")"
  FRONTEND_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$FRONTEND_CONTAINER")"
  if docker run --rm \
    --network "$BACKEND_NET" \
    --network "$FRONTEND_NET" \
    --mount type=bind,src="$REPO_ROOT",dst=/source,readonly \
    --mount type=volume,dst=/work \
    --mount type=bind,src="$PROBE_RESULTS",dst=/work/tests/real_user_benchmark/.results \
    --mount type=bind,src="$SIM_RESULTS",dst=/work/tests/simulation/.results \
    --mount type=bind,src="$MARATHON_RESULTS",dst=/work/data/test-marathon \
    -v istara-pw-browsers:/ms-playwright \
    -w /work \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    -e ISTARA_API_URL="$API_URL" \
    -e ISTARA_FRONTEND_URL="$FRONTEND_URL" \
    -e ISTARA_MARATHON_ENGINE="$engine" \
    -e ISTARA_RUNNER_SKIP_MARATHON="${ISTARA_RUNNER_SKIP_MARATHON:-0}" \
    -e ISTARA_BENCHMARK_ENGINE="$engine" \
    -e ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0 \
    -e ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=1 \
    -e ISTARA_BENCHMARK_START_SANDBOX=0 \
    -e ISTARA_BENCHMARK_SKIP_SANDBOX=1 \
    -e ISTARA_BENCHMARK_TEAM_MODE=true \
    -e ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="$ISTARA_BENCHMARK_CHAT_TIMEOUT_MS" \
    -e ISTARA_BENCHMARK_CODING_LIMIT="$ISTARA_BENCHMARK_CODING_LIMIT" \
    -e ISTARA_BENCHMARK_MAX_UPLOADS="$ISTARA_BENCHMARK_MAX_UPLOADS" \
    -e ISTARA_BENCHMARK_RUNNER_IMAGE="$RUNNER_IMAGE" \
    -e ISTARA_BENCHMARK_RUNNER_IMAGE_ID="$RUNNER_IMAGE_ID" \
    -e ISTARA_BENCHMARK_BACKEND_IMAGE_ID="$BACKEND_IMAGE_ID" \
    -e ISTARA_BENCHMARK_FRONTEND_IMAGE_ID="$FRONTEND_IMAGE_ID" \
    -e ISTARA_BENCHMARK_SOURCE_SHA="$SOURCE_COMMIT" \
    -e ISTARA_BENCHMARK_SOURCE_STATE=working-tree-snapshot \
    -e ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256="$ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256" \
    -e ISTARA_BENCHMARK_STATE_ISOLATION=fresh-postgres-container-per-engine \
    -e ISTARA_BENCHMARK_STACK_PROJECT="$PROJECT" \
    -e ISTARA_BENCHMARK_RUN_GROUP="$RUN_GROUP" \
    -e ISTARA_BENCHMARK_RUN_ORDER="$RUN_ORDER" \
    -e ISTARA_BENCHMARK_ARM_INDEX="$arm_index" \
    -e ISTARA_BENCHMARK_REQUIRE_REPRODUCIBLE_RUN=1 \
    -e ISTARA_ADMIN_USERNAME="${ISTARA_ADMIN_USER:-admin}" \
    --env-file "$RUNNER_ENV_FILE" \
    -e HOME=/tmp \
    --entrypoint bash \
    "$RUNNER_IMAGE" \
    /source/scripts/runner/inside.sh; then
    echo "[runner] engine=$engine completed without blockers"
  else
    arm_status=$?
    arm_failures=$((arm_failures + 1))
    echo "[runner] engine=$engine recorded blockers (exit=$arm_status); continuing comparison" >&2
  fi
done

if [ "$arm_failures" -ne 0 ]; then
  echo "[runner] comparison completed with blocker-bearing arms=$arm_failures" >&2
  exit 1
fi
