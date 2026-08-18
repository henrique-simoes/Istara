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
PROFILE="${QA_PROFILE:-contract}"
# The QA overlay is SELF-CONTAINED: never merge the base compose, which would
# reintroduce ollama and the fixed istara-* container names.
COMPOSE=(docker compose -f "$ROOT/docker-compose.qa.yml")
PROJECT="istara-qa-${RUN_ID}"

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}"
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
    qa-seeder
  echo "Seeded slice=$slice run=$RUN_ID (provisional only)."
}

cmd_qa() {
  python "$ROOT/scripts/check_feature_obligations.py" --base "${QA_BASE:-origin/testing}" --head HEAD \
    --json-out "$ROOT/artifacts/feature-obligations.json"
  python "$ROOT/scripts/check_qa_capabilities.py"
  echo "Registry-selected QA obligations evaluated for run=$RUN_ID."
}

cmd_collect() {
  local out="$ROOT/qa/runs/$RUN_ID"
  mkdir -p "$out"
  python "$ROOT/qa/scripts/audit_qa.py" --run-id "$RUN_ID" \
    --source-sha "${QA_SOURCE_SHA:-$(git -C "$ROOT" rev-parse HEAD)}" \
    --image-digest "${QA_IMAGE_DIGEST:-}" \
    --json-out "$out/audit-report.json"
  echo "Evidence collected under $out (sanitized)."
}

cmd_reset() {
  python "$ROOT/qa/scripts/reset_qa.py" --run-id "$RUN_ID" \
    --confirm "${QA_CONFIRM:-RESET-ISTARA-QA-RUN}" "${QA_DRY_RUN:+--dry-run}"
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
