#!/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:$PATH
cd /work

echo "[runner] installing simulation deps + chromium (cached volume)"
cd tests/simulation
npm ci --no-audit --no-fund > /dev/null
npx playwright install --with-deps chromium
cd /work

if [[ "${ISTARA_RUNNER_SKIP_MARATHON:-0}" != "1" ]]; then
  echo "[runner] MARATHON engine=$ISTARA_MARATHON_ENGINE start $(date -u +%H:%M:%S)"
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

echo "[runner] PROBE legacy start $(date -u +%H:%M:%S)"
npm --prefix tests/real_user_benchmark run probe:legacy
echo "[runner] PROBE pi start $(date -u +%H:%M:%S)"
npm --prefix tests/real_user_benchmark run probe:pi
echo "[runner] ALL DONE $(date -u +%H:%M:%S)"
