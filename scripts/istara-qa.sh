#!/usr/bin/env bash
# Public, provider-agnostic Istara QA developer entrypoint.
#
# Usage: scripts/istara-qa.sh <command> [--run-id <id>] [--profile <p>]
#
# Commands:
#   render   Validate the QA compose contract (CI-safe, no services started).
#   up       Start the selected QA profile as a unique istara-qa-<run-id> project.
#   wait     Wait for backend readiness (bounded).
#   seed     Seed the named synthetic corpus slice (provisional only).
#   qa       Run registry-selected deterministic QA obligations.
#   collect  Export sanitized JSON/JUnit evidence + provenance manifest.
#   reset    Tear down ONLY this run's project namespace (confirmation token).
#   down     Stop the run's project (keeps volumes).
#   staging  Placeholder: owner-local staging adapters live outside this file.
#
# No command here starts ollama/lmstudio/multivac, loads models, publishes
# beyond loopback, or touches LLMs/ and Model_Finetuning/. The `live` profile
# refuses to start without QA_LIVE_PROVIDER_TARGET.
set -euo pipefail

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

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}"
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
  "${COMPOSE[@]}" -p "$PROJECT" run --rm -T --no-deps --build \
    "${mounts[@]}" -w /workspace qa-backend \
    python "/workspace/$script" "$@"
}

cmd_render() {
  docker compose -f "$ROOT/docker-compose.qa.yml" --profile "$PROFILE" config --quiet
  echo "QA compose contract renders (profile=$PROFILE)."
}

cmd_up() {
  "${COMPOSE[@]}" -p "$PROJECT" --profile "$PROFILE" up -d
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
  "${COMPOSE[@]}" -p "$PROJECT" down
  echo "QA project $PROJECT stopped (volumes retained)."
}

cmd_staging() {
  echo "Staging adapters are owner-local and out of the public QA path." >&2
  echo "See the master plan §12 (read-only-first, unique project, rollback)." >&2
  exit 1
}

CMD="${1:-}"
case "$CMD" in
  render|up|wait|seed|qa|collect|reset|down|staging) "cmd_$CMD" ;;
  *) usage; exit 2 ;;
esac
