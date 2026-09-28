#!/usr/bin/env bash
# Public, provider-agnostic Istara QA developer entrypoint.
#
# Usage: scripts/istara-qa.sh <command> [--run-id <id>] [--profile <p>] [--persistent] [--apply]
#
# Commands:
#   render   Validate the QA compose contract (CI-safe, no services started).
#   up       Start the selected QA profile as a unique istara-qa-<run-id> project.
#   wait     Wait for backend readiness (bounded).
#   seed     Seed the named synthetic corpus slice (provisional only).
#   qa       Run registry-selected deterministic QA obligations.
#   collect  Export sanitized JSON/JUnit evidence + provenance manifest.
#   reset    Tear down ONLY this run's project namespace (confirmation token).
#   down     Remove the run's containers, networks and anonymous volumes.
#   cycle    up -> wait -> seed -> qa -> collect (persistent: up -> wait -> qa),
#            cleaned up on success, failure or kill.
#   backup   Snapshot the persistent QA volume to ~/never-delete-official-data/.
#   cleanup  List (default) or remove (--apply + QA_CONFIRM=CLEANUP-ISTARA-QA)
#            every istara-qa-* Docker resource not on the keep list.
#
# --persistent (QA_PERSISTENT=1) layers docker-compose.qa.persistent.yml: the
# one kept QA install, on the external volume istara-qa-persistent-data.
# Heavy commands refuse when Docker has under QA_MIN_FREE_GB (20) free.
#   staging  Placeholder: owner-local staging adapters live outside this file.
#
# No command here starts ollama/lmstudio/multivac, loads models, publishes
# beyond loopback, or touches LLMs/ and Model_Finetuning/. The `live` profile
# refuses to start without QA_LIVE_PROVIDER_TARGET.
set -euo pipefail

ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) QA_RUN_ID="$2"; shift 2 ;;
    --profile) QA_PROFILE="$2"; shift 2 ;;
    --persistent) QA_PERSISTENT=1; shift ;;
    --apply) QA_APPLY=1; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ID="${QA_RUN_ID:-$(date -u +%Y%m%d%H%M%S)}"
# Export so EVERY compose subprocess (up/seed/reset/audit/down) resolves
# ${QA_RUN_ID:-local} to THIS run's id instead of the fallback `local`; the
# shell-local RUN_ID must never diverge from what the compose overlay sees
# (F-3-r2: default-invocation seed wrote manifests under qa/runs/local).
export QA_RUN_ID="$RUN_ID"
PROFILE="${QA_PROFILE:-contract}"
# The QA overlay is SELF-CONTAINED: never merge the base compose, which would
# reintroduce ollama and the fixed istara-* container names.
COMPOSE=(docker compose -f "$ROOT/docker-compose.qa.yml")
PROJECT="istara-qa-${RUN_ID}"
PERSISTENT_VOLUME="istara-qa-persistent-data"
RECORDS_DIR="${QA_RECORDS_DIR:-$HOME/never-delete-official-data}"
if [ -n "${QA_PERSISTENT:-}" ]; then
  # The one kept install: fixed project name, external data volume.
  COMPOSE+=(-f "$ROOT/docker-compose.qa.persistent.yml")
  PROJECT="istara-qa-persistent"
fi

usage() {
  sed -n '2,29p' "${BASH_SOURCE[0]}"
}

# Refuse heavy work when the Docker disk is nearly full: a full disk breaks
# every other project on the host, not just this run.
ensure_disk_space() {
  local min="${QA_MIN_FREE_GB:-20}" free
  free="$(docker run --rm busybox:1.36 df -Pk / | awk 'NR==2 {print int($4 / 1048576)}')"
  if [ "${free:-0}" -lt "$min" ]; then
    echo "refusing: Docker disk has ${free:-0} GB free (< ${min} GB). Run 'scripts/istara-qa.sh cleanup' and report." >&2
    exit 3
  fi
  echo "Docker disk free: ${free} GB (minimum ${min} GB)."
}

cmd_backup() {
  docker volume inspect "$PERSISTENT_VOLUME" >/dev/null 2>&1 || {
    echo "no $PERSISTENT_VOLUME volume yet; nothing to back up."; return 0; }
  local dest
  dest="$RECORDS_DIR/$PERSISTENT_VOLUME/$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$dest"
  docker run --rm -v "$PERSISTENT_VOLUME:/data:ro" -v "$dest:/backup" busybox:1.36 \
    tar -czf /backup/app-data.tar.gz -C /data .
  echo "Backed up $PERSISTENT_VOLUME to $dest (a record: never delete)."
}

# Run QA Python tooling in the disposable QA image. The Mac Studio shell may
# orchestrate Docker and create bounded artifact directories, but it must not
# execute repository Python/Node workloads on the host. The source checkout is
# mounted read-only; only the ignored QA/artifact output surfaces are writable.
run_qa_python() {
  local script="$1"
  shift
  local -a mounts=( -v "$ROOT:/workspace:ro" )
  if [ -d "$ROOT/artifacts" ]; then
    mounts+=( -v "$ROOT/artifacts:/workspace/artifacts:rw" )
  fi
  if [ -d "$ROOT/qa/runs" ]; then
    mounts+=( -v "$ROOT/qa/runs:/workspace/qa/runs:rw" )
  fi
  # --profile keeps profile-gated depends_on targets (qa-provider-stub)
  # resolvable; --no-deps still stops them from starting.
  "${COMPOSE[@]}" -p "$PROJECT" --profile "$PROFILE" run --rm -T --no-deps --build \
    "${mounts[@]}" -w /workspace \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/workspace \
    qa-backend \
    python "/workspace/$script" "$@"
}

cmd_render() {
  docker compose -f "$ROOT/docker-compose.qa.yml" --profile "$PROFILE" config --quiet
  echo "QA compose contract renders (profile=$PROFILE)."
}

cmd_up() {
  ensure_disk_space
  if [ -n "${QA_PERSISTENT:-}" ]; then
    docker volume create --label istara.qa.keep=true "$PERSISTENT_VOLUME" >/dev/null
    cmd_backup
  fi
  "${COMPOSE[@]}" -p "$PROJECT" --profile "$PROFILE" up -d --build
  echo "QA stack up: project=$PROJECT profile=$PROFILE"
}

cmd_wait() {
  local timeout="${QA_WAIT_SECONDS:-180}"
  local i=0
  until curl -fsS "http://localhost:${QA_API_PORT:-8000}/api/health" >/dev/null 2>&1; do
    i=$((i + 5))
    if [ "$i" -ge "$timeout" ]; then
      echo "QA readiness timeout after ${timeout}s (project=$PROJECT)" >&2
      "${COMPOSE[@]}" -p "$PROJECT" logs --tail=50 || true
      exit 1
    fi
    sleep 5
  done
  echo "QA backend ready (project=$PROJECT)."
}

cmd_seed() {
  local slice="${QA_SLICE:-coding-reliability}"
  # Run the seeder THROUGH the compose service (never `docker run $ROOT/backend`):
  # the QA image contains qa/scripts + qa/corpora, starts qa-backend (healthy)
  # as its dependency, and ingests the slice through the real evidence-unit
  # path. QA_API_BASE defaults to the in-network qa-backend service DNS.
  "${COMPOSE[@]}" -p "$PROJECT" --profile synthetic run --rm -T \
    -e QA_SLICE="$slice" \
    -e QA_RUN_ID="$RUN_ID" \
    qa-seeder
  echo "Seeded slice=$slice run=$RUN_ID (provisional only)."
}

cmd_qa() {
  mkdir -p "$ROOT/artifacts"
  run_qa_python scripts/check_feature_obligations.py \
    --base "${QA_BASE:-origin/testing}" --head HEAD \
    --json-out artifacts/feature-obligations.json
  run_qa_python scripts/check_qa_capabilities.py
  echo "Registry-selected QA obligations evaluated for run=$RUN_ID."
}

cmd_collect() {
  local out="$ROOT/qa/runs/$RUN_ID"
  mkdir -p "$out"
  run_qa_python qa/scripts/audit_qa.py --run-id "$RUN_ID" \
    --source-sha "${QA_SOURCE_SHA:-$(git -C "$ROOT" rev-parse HEAD)}" \
    --image-digest "${QA_IMAGE_DIGEST:-}" \
    --runs-dir /workspace/qa/runs \
    --json-out "/workspace/qa/runs/$RUN_ID/audit-report.json"
  echo "Evidence collected under $out (sanitized)."
}

cmd_reset() {
  if ! [[ "$RUN_ID" =~ ^[a-z0-9][a-z0-9_-]{0,63}$ ]]; then
    echo "unsafe QA run id: $RUN_ID" >&2
    exit 2
  fi
  local normalized="${RUN_ID,,}"
  case "$normalized" in
    *llms*|*model_finetuning*)
      echo "refusing reset: run id resolves toward a protected artifact folder" >&2
      exit 2
      ;;
  esac
  if [ "${QA_CONFIRM:-}" != "RESET-ISTARA-QA-RUN" ]; then
    echo "QA reset requires QA_CONFIRM=RESET-ISTARA-QA-RUN" >&2
    exit 2
  fi
  if [ -n "${QA_DRY_RUN:-}" ]; then
    echo "QA reset (dry-run) completed for project=$PROJECT"
    echo "command: docker compose -f $ROOT/docker-compose.qa.yml -p $PROJECT down -v"
    return 0
  fi
  "${COMPOSE[@]}" -p "$PROJECT" down -v
  echo "Reset completed for project=$PROJECT (this run only)."
}

cmd_down() {
  # -v removes only this project's anonymous/declared volumes; the persistent
  # volume is external and survives by construction.
  "${COMPOSE[@]}" -p "$PROJECT" --profile "*" down -v --remove-orphans
  echo "QA project $PROJECT removed (persistent data volume, if any, kept)."
}

# Removes a run's containers, networks and anonymous volumes, and any image a
# rebuild left dangling. Registered as the EXIT/INT/TERM trap of `cycle`.
cleanup_run() {
  local rc=$?
  trap - EXIT INT TERM
  echo "Cleaning up QA project $PROJECT (exit $rc)."
  cmd_down || true
  prune_dangling_images || true
  exit "$rc"
}

# Dangling images a rebuild left behind, limited to istara-qa-* compose projects.
dangling_istara_images() {
  local id
  for id in $(docker images -q --filter dangling=true); do
    case "$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$id" 2>/dev/null)" in
      istara-qa-*) echo "$id" ;;
    esac
  done
}

prune_dangling_images() {
  local ids
  ids="$(dangling_istara_images)"
  [ -z "$ids" ] || docker rmi $ids
}

cmd_cycle() {
  trap cleanup_run EXIT INT TERM
  cmd_up
  cmd_wait
  if [ -n "${QA_PERSISTENT:-}" ]; then
    # Never seed the synthetic corpus into the kept install.
    cmd_qa
  else
    cmd_seed
    cmd_qa
    cmd_collect
  fi
}

# Keep list: the current image set (istara-qa-*:${QA_IMAGE_TAG:-current}),
# the persistent volume, running containers, and anything outside the
# istara-qa- namespace (other projects are listed, never touched).
cmd_cleanup() {
  local tag="${QA_IMAGE_TAG:-current}" apply=""
  if [ -n "${QA_APPLY:-}" ]; then
    if [ "${QA_CONFIRM:-}" != "CLEANUP-ISTARA-QA" ]; then
      echo "cleanup --apply requires QA_CONFIRM=CLEANUP-ISTARA-QA" >&2
      exit 2
    fi
    apply=1
  fi
  local containers volumes networks images dangling
  containers="$(docker ps -a --filter status=exited --filter status=created --filter status=dead \
    --format '{{.Names}}' | grep -E '^istara-qa-' || true)"
  volumes="$(docker volume ls --format '{{.Name}}' | grep -E '^istara-qa-' \
    | grep -vx "$PERSISTENT_VOLUME" || true)"
  networks="$(docker network ls --format '{{.Name}}' | grep -E '^istara-qa-' || true)"
  images="$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^istara-qa-' \
    | grep -v ":${tag}\$" || true)"
  dangling="$(dangling_istara_images)"
  echo "== Istara QA resources not on the keep list"
  printf 'container %s\n' $containers
  printf 'volume    %s\n' $volumes
  printf 'network   %s\n' $networks
  printf 'image     %s\n' $images $dangling
  echo "== Other projects (never touched here)"
  docker ps -a --format '{{.Names}}' | grep -vE '^istara-qa-' | sed 's/^/  /' || true
  if [ -z "$apply" ]; then
    echo "Dry run. Re-run with --apply and QA_CONFIRM=CLEANUP-ISTARA-QA to remove the list above."
    return 0
  fi
  [ -z "$containers" ] || docker rm -v $containers
  [ -z "$networks" ] || docker network rm $networks || true
  [ -z "$volumes" ] || docker volume rm $volumes
  [ -z "$images$dangling" ] || docker rmi $images $dangling
  echo "Cleanup done. Kept: istara-qa-*:${tag}, $PERSISTENT_VOLUME, running containers."
}

cmd_staging() {
  echo "Staging adapters are owner-local and out of the public QA path." >&2
  echo "See the master plan §12 (read-only-first, unique project, rollback)." >&2
  exit 1
}

CMD="${1:-}"
case "$CMD" in
  render|up|wait|seed|qa|collect|reset|down|cycle|backup|cleanup|staging) "cmd_$CMD" ;;
  *) usage; exit 2 ;;
esac
