#!/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:$PATH
export ISTARA_BENCHMARK_CHAT_TIMEOUT_MS="${ISTARA_BENCHMARK_CHAT_TIMEOUT_MS:-300000}"
: "${ISTARA_BENCHMARK_CODING_LIMIT:=3}"
: "${ISTARA_BENCHMARK_MAX_UPLOADS:=6}"
: "${ISTARA_BENCHMARK_ENGINE:?set ISTARA_BENCHMARK_ENGINE to legacy or pi}"
: "${ISTARA_BENCHMARK_ACCEPTANCE_PROFILE:=combined}"
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
