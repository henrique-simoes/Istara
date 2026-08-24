#!/bin/bash
# Phase 7 runner: marathon + real-user probes INSIDE Docker (never installs
# on the host). Joins the deployed stack's networks and talks to services
# by DNS. Playwright browsers cached in a named volume.
set -euo pipefail

PROJECT="${ISTARA_STACK_PROJECT:-istara-testing}"
BACKEND_NET="${PROJECT}_backend-net"
FRONTEND_NET="${PROJECT}_frontend-net"
API_URL="${ISTARA_API_URL:-http://backend:8000}"
FRONTEND_URL="${ISTARA_FRONTEND_URL:-http://frontend:3000}"
ENGINE_SETTING="${ISTARA_MARATHON_ENGINE:-both}"

docker volume create istara-pw-browsers >/dev/null 2>&1 || true

TOKEN="$(curl -s "${ISTARA_PUBLIC_API_URL:-http://localhost:13080}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ISTARA_ADMIN_USER:-admin}\",\"password\":\"${ISTARA_ADMIN_PASSWORD:?set ISTARA_ADMIN_PASSWORD}\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))')"
[ -n "$TOKEN" ] || { echo "auth failed"; exit 1; }

docker run --rm \
  --network "$BACKEND_NET" \
  --network "$FRONTEND_NET" \
  -v "$(cd "$(dirname "$0")/../.." && pwd)":/work \
  -v istara-pw-browsers:/ms-playwright \
  -w /work \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  -e ISTARA_API_URL="$API_URL" \
  -e ISTARA_FRONTEND_URL="$FRONTEND_URL" \
  -e ISTARA_TEST_AUTH_TOKEN="$TOKEN" \
  -e ISTARA_MARATHON_ENGINE="$ENGINE_SETTING" \
  -e ISTARA_RUNNER_SKIP_MARATHON="${ISTARA_RUNNER_SKIP_MARATHON:-0}" \
  -e ISTARA_BENCHMARK_ENGINE="" \
  -e ISTARA_BENCHMARK_REQUIRE_COMPUTE_DONATION=0 \
  -e ISTARA_BENCHMARK_REQUIRE_LIVE_CHAT=1 \
  -e ISTARA_BENCHMARK_START_SANDBOX=0 \
  -e ISTARA_BENCHMARK_SKIP_SANDBOX=1 \
  -e ISTARA_BENCHMARK_FRESH_SANDBOX=0 \
  -e ISTARA_BENCHMARK_TEAM_MODE=true \
  -e ISTARA_ADMIN_USERNAME="${ISTARA_ADMIN_USER:-admin}" \
  -e ISTARA_ADMIN_PASSWORD="$ISTARA_ADMIN_PASSWORD" \
  -e HOME=/tmp \
  --entrypoint bash \
  node:20-bookworm \
  /work/scripts/runner/inside.sh
