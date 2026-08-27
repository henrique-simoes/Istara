#!/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:$PATH
export ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="${ISTARA_BENCHMARK_CHAT_TIMEOUT_MS:-300000}"
: "${ISTARA_BENCHMARK_CODING_LIMIT:=3}"
: "${ISTARA_BENCHMARK_MAX_UPLOADS:=6}"
: "${ISTARA_BENCHMARK_ENGINE:?set ISTARA_BENCHMARK_ENGINE to legacy or pi}"
: "${ISTARA_BENCHMARK_ACCEPTANCE_PROFILE:=combined}"
: "${ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON:=0}"
if [[ -z "${ISTARA_RUNNER_SKIP_MARATHON:-}" ]]; then
  case "$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" in
    combined) ISTARA_RUNNER_SKIP_MARATHON=0 ;;
    provider|petals) ISTARA_RUNNER_SKIP_MARATHON=1 ;;
    *) echo "unsupported acceptance profile: $ISTARA_BENCHMARK_ACCEPTANCE_PROFILE" >&2; exit 2 ;;
  esac
fi
case "$ISTARA_BENCHMARK_ENGINE" in
  legacy|pi) ;;
  *) echo "unsupported benchmark engine: $ISTARA_BENCHMARK_ENGINE" >&2; exit 2 ;;
esac
case "$ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON" in
  0|false|no) RUN_LONG_HORIZON=0 ;;
  1|true|yes) RUN_LONG_HORIZON=1 ;;
  *) echo "ISTARA_BENCHMARK_REQUIRE_LONG_HORIZON must be 0/1/true/false/yes/no" >&2; exit 2 ;;
esac

# Materialize a disposable worktree inside Docker. Writable result mounts are
# deliberately excluded so their prior evidence is preserved across runs.
cd /source
tar \
  --exclude='./tests/real_user_benchmark/.results' \
  --exclude='./tests/simulation/.results' \
  --exclude='./data/test-marathon' \
  -cf - . | tar -xf - -C /work
cd /work

echo "[runner] installing simulation deps + chromium (cached volume)"
cd tests/simulation
npm ci --no-audit --no-fund > /dev/null
npx playwright install --with-deps chromium
cd /work

if [[ "${ISTARA_RUNNER_SKIP_MARATHON:-0}" != "1" ]]; then
  echo "[runner] MARATHON engine=$ISTARA_MARATHON_ENGINE start $(date -u +%H:%M:%S)"
  export ISTARA_MARATHON_CONTAINERIZED=1
  node scripts/marathon/run-cycle.mjs --all
  echo "[runner] MARATHON done $(date -u +%H:%M:%S)"
else
  echo "[runner] MARATHON skipped (ISTARA_RUNNER_SKIP_MARATHON=1)"
fi

if [[ "$RUN_LONG_HORIZON" -eq 1 ]]; then
  case "${ISTARA_LONG_HORIZON_ENGINE:-}" in
    legacy|pi) ;;
    *) echo "ISTARA_LONG_HORIZON_ENGINE must be legacy or pi when long-horizon is required" >&2; exit 2 ;;
  esac
  LONG_HORIZON_RESULTS="data/test-marathon/long-horizon"
  mkdir -p "$LONG_HORIZON_RESULTS"
  echo "[runner] LONG_HORIZON engine=$ISTARA_LONG_HORIZON_ENGINE start $(date -u +%H:%M:%S)"
  /opt/runner-venv/bin/python tests/benchmarks/long_horizon_runner.py \
    2>&1 | tee "$LONG_HORIZON_RESULTS/${ISTARA_LONG_HORIZON_ENGINE}.log"
  export ISTARA_BENCHMARK_LONG_HORIZON_VERIFIED=1
  echo "[runner] LONG_HORIZON engine=$ISTARA_LONG_HORIZON_ENGINE done $(date -u +%H:%M:%S)"
else
  echo "[runner] LONG_HORIZON skipped for acceptance profile=$ISTARA_BENCHMARK_ACCEPTANCE_PROFILE"
fi

echo "[runner] probe deps"
cd tests/real_user_benchmark
npm ci --no-audit --no-fund > /dev/null
npx playwright install --with-deps chromium
cd /work

echo "[runner] PROBE $ISTARA_BENCHMARK_ENGINE start $(date -u +%H:%M:%S)"
PROBE_SCRIPT="${ISTARA_BENCHMARK_PROBE_SCRIPT:-probe:${ISTARA_BENCHMARK_ENGINE}}"
npm --prefix tests/real_user_benchmark run "$PROBE_SCRIPT" -- \
  --coding-limit "$ISTARA_BENCHMARK_CODING_LIMIT" \
  --max-uploads "$ISTARA_BENCHMARK_MAX_UPLOADS"
echo "[runner] ALL DONE $(date -u +%H:%M:%S)"
