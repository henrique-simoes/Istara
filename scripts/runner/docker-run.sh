#!/bin/bash
# Phase 7 runner: marathon + real-user probes INSIDE Docker. The checkout is
# mounted read-only and copied into an anonymous container volume before the
# browser automation run, so neither dependencies nor browser packages can land on the
# Mac Studio host. Only benchmark result directories are writable bind mounts.
set -euo pipefail

# The Mac Studio SSH login shell may not include Docker Desktop's CLI in PATH. Resolve an
# operator-supplied binary (or Docker Desktop's standard path) without installing anything
# on the host; every benchmark workload still runs in Docker below.
if [[ -n "${ISTARA_DOCKER_BIN:-}" ]]; then
  [ -x "$ISTARA_DOCKER_BIN" ] || { echo "ISTARA_DOCKER_BIN is not executable: $ISTARA_DOCKER_BIN" >&2; exit 2; }
  export PATH="$(dirname "$ISTARA_DOCKER_BIN"):$PATH"
elif ! command -v docker >/dev/null 2>&1; then
  for docker_dir in \
    "/Applications/Docker.app/Contents/Resources/bin" \
    "/opt/homebrew/bin" \
    "/usr/local/bin"; do
    if [ -x "$docker_dir/docker" ]; then
      export PATH="$docker_dir:$PATH"
      break
    fi
  done
fi
command -v docker >/dev/null 2>&1 || { echo "Docker CLI is required; install/use Docker Desktop on the Docker host, never this runner" >&2; exit 2; }

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
# Three raw evidence units are the smallest useful live Fleiss-kappa proof:
# each is coded independently by all three selected model identities. They may
# come from one source document; source diversity is observable but is not a
# validity gate. Keep uploads larger than that scope so source ingestion is also
# exercised, without turning a smoke/proof arm into an unbounded corpus benchmark.
ISTARA_BENCHMARK_CODING_LIMIT="${ISTARA_BENCHMARK_CODING_LIMIT:-3}"
ISTARA_BENCHMARK_MAX_UPLOADS="${ISTARA_BENCHMARK_MAX_UPLOADS:-6}"

case "${ISTARA_MARATHON_ENGINE:-both}" in
  both) ENGINES=(legacy pi) ;;
  legacy|pi) ENGINES=("${ISTARA_MARATHON_ENGINE}") ;;
  *) echo "ISTARA_MARATHON_ENGINE must be legacy, pi, or both" >&2; exit 2 ;;
esac

RUN_GROUP="${ISTARA_BENCHMARK_RUN_GROUP:-docker-comparison-$(date -u +%Y%m%dT%H%M%SZ)}"
RUNNER_IMAGE_REQUEST="${ISTARA_RUNNER_IMAGE:-istara-benchmark-runner:node20-docker-cli}"
: "${ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256:?set the sha256 of the exact source snapshot copied to the Mac Studio}"
SOURCE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)" || {
  echo "unable to resolve the exact source commit for benchmark provenance" >&2
  exit 1
}
# The caller supplies the digest from the detached source transfer, but a shape check
# alone cannot prove that the mounted source is the same snapshot. Recompute the
# canonical Git archive locally and fail before any image pull, stack startup, or model
# operation when the declared digest is stale or belongs to a different checkout. macOS
# provides `shasum`; Linux hosts commonly provide `sha256sum`, so support both without
# installing host tooling.
compute_source_snapshot_sha256() {
  if command -v shasum >/dev/null 2>&1; then
    git -C "$REPO_ROOT" archive --format=tar HEAD | shasum -a 256 | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    git -C "$REPO_ROOT" archive --format=tar HEAD | sha256sum | awk '{print $1}'
  else
    echo "a SHA-256 utility (shasum or sha256sum) is required for source provenance" >&2
    return 1
  fi
}
SOURCE_ARCHIVE_SHA256="$(compute_source_snapshot_sha256)" || {
  echo "unable to compute the checked-out source snapshot sha256" >&2
  exit 2
}
if ! [[ "$SOURCE_ARCHIVE_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
  echo "computed source snapshot sha256 is invalid" >&2
  exit 2
fi
DECLARED_SOURCE_SNAPSHOT_SHA256="$(printf '%s' "$ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256" | tr '[:upper:]' '[:lower:]')"
if [[ "$DECLARED_SOURCE_SNAPSHOT_SHA256" != "$SOURCE_ARCHIVE_SHA256" ]]; then
  echo "source snapshot sha256 does not match the checked-out source" >&2
  exit 2
fi
COMPOSE_FILE="${ISTARA_BENCHMARK_COMPOSE_FILE:-$REPO_ROOT/docker-compose.vps.yml}"
COMPOSE_ENV_FILE="${ISTARA_BENCHMARK_COMPOSE_ENV_FILE:-$REPO_ROOT/.env.deploy}"
MODEL_ROOT_HOST="${ISTARA_BENCHMARK_MODEL_ROOT:-$HOME/Istara-Projects/models}"
case "$MODEL_ROOT_HOST" in
  /*) ;;
  *) echo "ISTARA_BENCHMARK_MODEL_ROOT must be an absolute Docker-host path: $MODEL_ROOT_HOST" >&2; exit 2 ;;
esac
RESET_STACK="${ISTARA_BENCHMARK_RESET_STACK:-1}"
RUN_ORDER="$(IFS=,; echo "${ENGINES[*]}")"
# Non-plan benchmark runs must require donated compute unless the operator explicitly
# selects an offline harness/debug control. Keep the default aligned with run.mjs and the
# benchmark registry; never silently turn the Research Spine acceptance gate off.
ISTARA_BENCHMARK_ACCEPTANCE_PROFILE="${ISTARA_BENCHMARK_ACCEPTANCE_PROFILE:-combined}"
case "$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" in
  provider|petals|combined) ;;
  *) echo "ISTARA_BENCHMARK_ACCEPTANCE_PROFILE must be provider, petals, or combined" >&2; exit 2 ;;
esac
if [[ -z "${ISTARA_RUNNER_SKIP_MARATHON:-}" ]]; then
  case "$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" in
    combined) ISTARA_RUNNER_SKIP_MARATHON=0 ;;
    provider|petals) ISTARA_RUNNER_SKIP_MARATHON=1 ;;
  esac
fi
if [[ -z "${ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT:-}" ]]; then
  case "$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" in
    combined) ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=1 ;;
    provider|petals) ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=0 ;;
  esac
fi
if [[ -z "${ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION:-}" ]]; then
  case "$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" in
    provider) ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0 ;;
    petals|combined) ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=1 ;;
  esac
fi
ISTARA_BENCHMARK_START_CLIENT_SANDBOXES="${ISTARA_BENCHMARK_START_CLIENT_SANDBOXES:-$ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION}"
ISTARA_BENCHMARK_DOCKER_SOCKET="${ISTARA_BENCHMARK_DOCKER_SOCKET:-/var/run/docker.sock}"
if [[ -n "${ISTARA_BENCHMARK_PROBE_SCRIPT:-}" ]]; then
  PROBE_SCRIPT="$ISTARA_BENCHMARK_PROBE_SCRIPT"
elif [[ -n "${ISTARA_BENCHMARK_DONOR_TOPOLOGY:-}" ]]; then
  PROBE_SCRIPT="probe:deep:three-model"
else
  PROBE_SCRIPT="probe:${ISTARA_BENCHMARK_ENGINE}"
fi
case "$PROBE_SCRIPT" in
  probe|probe:deep|probe:deep:three-model|probe:legacy|probe:pi) ;;
  *) echo "ISTARA_BENCHMARK_PROBE_SCRIPT must be probe, probe:deep, probe:deep:three-model, probe:legacy, or probe:pi" >&2; exit 2 ;;
esac
THREE_MODEL_RUN=0
case "$PROBE_SCRIPT" in
  probe:deep:three-model) THREE_MODEL_RUN=1 ;;
esac
case "${ISTARA_BENCHMARK_DONOR_TOPOLOGY:-}" in
  3-model|3model|three-model|macstudio-colima|macstudio-colima-qwen-gemma|macstudio+colima|local-three-model) THREE_MODEL_RUN=1 ;;
esac
COMPOSE_PROFILE_ARGS=()
COMPOSE_DONOR_SERVICES=()
if [ "$THREE_MODEL_RUN" -eq 1 ]; then
  : "${ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE:?set ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE for the Compose-managed Gemma donor}"
  case "$ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE" in
    "$MODEL_ROOT_HOST"/*) ;;
    *) echo "ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE must be under ISTARA_BENCHMARK_MODEL_ROOT" >&2; exit 2 ;;
  esac
  [ -f "$ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE" ] || {
    echo "Compose-managed Gemma model file is missing: $ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE" >&2
    exit 2
  }
  ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_RELATIVE="${ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_FILE#"$MODEL_ROOT_HOST/"}"
  export ISTARA_BENCHMARK_MODEL_ROOT="$MODEL_ROOT_HOST"
  export ISTARA_BENCHMARK_DONOR_GEMMA_MODEL_RELATIVE
  COMPOSE_PROFILE_ARGS+=(--profile three-model)
  COMPOSE_DONOR_SERVICES+=(donor-gemma)
fi

case "$ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION" in
  0|1|true|false|yes|no) ;;
  *) echo "ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION must be 0/1/true/false/yes/no" >&2; exit 2 ;;
esac
case "$ISTARA_BENCHMARK_START_CLIENT_SANDBOXES" in
  0|1|true|false|yes|no) ;;
  *) echo "ISTARA_BENCHMARK_START_CLIENT_SANDBOXES must be 0/1/true/false/yes/no" >&2; exit 2 ;;
esac

# The benchmark's donor/model/client helpers invoke Docker from inside the disposable
# runner. Mount only the Docker API socket into that runner when client sandboxes are
# enabled; application services never receive the socket. This is a deliberate Docker-only
# boundary, and missing prerequisites fail closed before any comparison arm starts.
NESTED_DOCKER_MOUNTS=()
case "$ISTARA_BENCHMARK_START_CLIENT_SANDBOXES" in
  1|true|yes)
    [ -S "$ISTARA_BENCHMARK_DOCKER_SOCKET" ] || {
      echo "required nested Docker socket is unavailable: $ISTARA_BENCHMARK_DOCKER_SOCKET" >&2
      echo "set ISTARA_BENCHMARK_START_CLIENT_SANDBOXES=0 only for an explicit offline control run" >&2
      exit 2
    }
    NESTED_DOCKER_MOUNTS=(--mount "type=bind,src=$ISTARA_BENCHMARK_DOCKER_SOCKET,dst=/var/run/docker.sock")
    ;;
esac

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

append_env_name() {
  local name="$1"
  case "$name" in
    ISTARA_ADMIN_PASSWORD|ADMIN_PASSWORD|ISTARA_TEST_ADMIN_PASSWORD) return 0 ;;
  esac
  if [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && declare -p "$name" >/dev/null 2>&1; then
    printf '%s=%s\n' "$name" "${!name}" >> "$RUNNER_ENV_FILE"
  fi
}

# Pass benchmark topology/profile inputs into the isolated runner without exposing secrets
# in the Docker CLI argv. API keys referenced by *_API_KEY_ENV are opt-in via
# ISTARA_BENCHMARK_PASSTHROUGH_ENV_NAMES and are written only to the mode-600 transient env
# file. The prefixed benchmark variables are safe to forward because they are namespaced and
# consumed solely by the benchmark process, including ISTARA_BENCHMARK_DONOR_* profiles,
# ISTARA_BENCHMARK_DONOR_PROFILES_FILE, ISTARA_BENCHMARK_COMPUTE_CONNECTION_STRINGS,
# topology/count/route requirements, and signed connection-string inputs.
while IFS= read -r env_name; do
  append_env_name "$env_name"
done < <(compgen -A variable | sed -n '/^ISTARA_BENCHMARK_/p')
for env_name in ISTARA_NETWORK_ACCESS_TOKEN NETWORK_ACCESS_TOKEN; do
  append_env_name "$env_name"
done
if [[ -n "${ISTARA_BENCHMARK_PASSTHROUGH_ENV_NAMES:-}" ]]; then
  passthrough_names="${ISTARA_BENCHMARK_PASSTHROUGH_ENV_NAMES//,/ }"
  for env_name in $passthrough_names; do
    append_env_name "$env_name"
  done
fi

if [[ -n "${ISTARA_RUNNER_IMAGE:-}" ]]; then
  docker pull "$RUNNER_IMAGE_REQUEST" >/dev/null
else
  docker build --pull -f "$REPO_ROOT/scripts/runner/Dockerfile" -t "$RUNNER_IMAGE_REQUEST" "$REPO_ROOT/scripts/runner" >/dev/null
fi
RUNNER_IMAGE_DIGEST="$(docker image inspect --format '{{join .RepoDigests "\n"}}' "$RUNNER_IMAGE_REQUEST" 2>/dev/null | sed -n '1p')"
RUNNER_IMAGE="${RUNNER_IMAGE_DIGEST:-$RUNNER_IMAGE_REQUEST}"
RUNNER_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$RUNNER_IMAGE_REQUEST")"

if [[ ${#NESTED_DOCKER_MOUNTS[@]} -gt 0 ]]; then
  if ! docker run --rm "${NESTED_DOCKER_MOUNTS[@]}" "$RUNNER_IMAGE_REQUEST" docker info >/dev/null 2>&1; then
    echo "runner image cannot reach the Docker daemon through $ISTARA_BENCHMARK_DOCKER_SOCKET" >&2
    echo "use the repository Dockerfile or an ISTARA_RUNNER_IMAGE that contains a Linux Docker CLI" >&2
    exit 2
  fi
fi

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
    "${COMPOSE_PROFILE_ARGS[@]}" \
    --env-file "$COMPOSE_ENV_FILE" \
    -f "$COMPOSE_FILE" \
    up -d --force-recreate --wait \
    postgres provider-stub backend frontend caddy "${COMPOSE_DONOR_SERVICES[@]}"
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
  runner_docker_args=(
    --rm
    --network "$BACKEND_NET"
    --network "$FRONTEND_NET"
    --mount "type=bind,src=$REPO_ROOT,dst=/source,readonly"
    --mount type=volume,dst=/work
    --mount "type=bind,src=$PROBE_RESULTS,dst=/work/tests/real_user_benchmark/.results"
    --mount "type=bind,src=$SIM_RESULTS,dst=/work/tests/simulation/.results"
    --mount "type=bind,src=$MARATHON_RESULTS,dst=/work/data/test-marathon"
    -v istara-pw-browsers:/ms-playwright
    -w /work
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
    -e "ISTARA_API_URL=$API_URL"
    -e "ISTARA_FRONTEND_URL=$FRONTEND_URL"
    -e "ISTARA_MARATHON_ENGINE=$engine"
    -e "ISTARA_RUNNER_SKIP_MARATHON=$ISTARA_RUNNER_SKIP_MARATHON"
    -e "ISTARA_BENCHMARK_ENGINE=$engine"
    -e "ISTARA_BENCHMARK_ACCEPTANCE_PROFILE=$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE"
    -e "ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=$ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION"
    -e "ISTARA_BENCHMARK_START_CLIENT_SANDBOXES=$ISTARA_BENCHMARK_START_CLIENT_SANDBOXES"
    -e "ISTARA_BENCHMARK_PROBE_SCRIPT=$PROBE_SCRIPT"
    -e "ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=$ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT"
    -e ISTARA_BENCHMARK_DOCKER_RUNNER=1
    -e "ISTARA_BENCHMARK_MODEL_ROOT=$MODEL_ROOT_HOST"
    -e "ISTARA_BENCHMARK_BACKEND_NETWORK=$BACKEND_NET"
    -e ISTARA_BENCHMARK_START_SANDBOX=0
    -e ISTARA_BENCHMARK_SKIP_SANDBOX=1
    -e ISTARA_BENCHMARK_TEAM_MODE=true
    -e "ISTARA_BENCHMARK_CHAT_TIMEOUT_MS=$ISTARA_BENCHMARK_CHAT_TIMEOUT_MS"
    -e "ISTARA_BENCHMARK_CODING_LIMIT=$ISTARA_BENCHMARK_CODING_LIMIT"
    -e "ISTARA_BENCHMARK_MAX_UPLOADS=$ISTARA_BENCHMARK_MAX_UPLOADS"
    -e "ISTARA_BENCHMARK_RUNNER_IMAGE=$RUNNER_IMAGE"
    -e "ISTARA_BENCHMARK_RUNNER_IMAGE_ID=$RUNNER_IMAGE_ID"
    -e "ISTARA_BENCHMARK_BACKEND_IMAGE_ID=$BACKEND_IMAGE_ID"
    -e "ISTARA_BENCHMARK_FRONTEND_IMAGE_ID=$FRONTEND_IMAGE_ID"
    -e "ISTARA_BENCHMARK_SOURCE_SHA=$SOURCE_COMMIT"
    -e ISTARA_BENCHMARK_SOURCE_STATE=working-tree-snapshot
    -e "ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256=$ISTARA_BENCHMARK_SOURCE_SNAPSHOT_SHA256"
    -e ISTARA_BENCHMARK_STATE_ISOLATION=fresh-postgres-container-per-engine
    -e "ISTARA_BENCHMARK_STACK_PROJECT=$PROJECT"
    -e "ISTARA_BENCHMARK_RUN_GROUP=$RUN_GROUP"
    -e "ISTARA_BENCHMARK_RUN_ORDER=$RUN_ORDER"
    -e "ISTARA_BENCHMARK_ARM_INDEX=$arm_index"
    -e ISTARA_BENCHMARK_REQUIRE_REPRODUCIBLE_RUN=1
    -e "ISTARA_ADMIN_USERNAME=${ISTARA_ADMIN_USER:-admin}"
    --env-file "$RUNNER_ENV_FILE"
    -e HOME=/tmp
  )
  if [ -d "$MODEL_ROOT_HOST" ]; then
    runner_docker_args+=( --mount "type=bind,src=$MODEL_ROOT_HOST,dst=$MODEL_ROOT_HOST,readonly" )
  fi
  if [[ ${#NESTED_DOCKER_MOUNTS[@]} -gt 0 ]]; then
    runner_docker_args+=( "${NESTED_DOCKER_MOUNTS[@]}" )
  fi
  runner_docker_args+=( --entrypoint bash "$RUNNER_IMAGE" /source/scripts/runner/inside.sh )
  if docker run "${runner_docker_args[@]}"; then
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
