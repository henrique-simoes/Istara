#!/usr/bin/env bash
# Istara Test Marathon — Manual start
#
# Usage:
#   ./scripts/marathon/start-marathon.sh           # Run next cycle
#   ./scripts/marathon/start-marathon.sh --all     # Run ALL cycles
#   ./scripts/marathon/start-marathon.sh --cycle A # Run specific cycle
#   ./scripts/marathon/start-marathon.sh --loop    # Continuous loop (30min interval)

set -euo pipefail
cd "$(dirname "$0")/../.."

# Ensure log directory
mkdir -p data/test-marathon/cycles data/test-marathon/issues

if [ "${1:-}" = "--loop" ]; then
    echo "🏃 Starting Istara Test Marathon (continuous loop, 30min interval)"
    echo "   Press Ctrl+C to stop"
    echo "   Logs: data/test-marathon/MARATHON_LOG.md"
    echo ""
    CYCLE=0
    while true; do
        CYCLE=$((CYCLE + 1))
        echo "━━━ Marathon Loop $CYCLE — $(date) ━━━"
        node scripts/marathon/run-cycle.mjs 2>&1 | tee -a data/test-marathon/marathon-output.log
        echo ""
        echo "⏳ Next cycle in 30 minutes... (Ctrl+C to stop)"
        sleep 1800
    done
else
    node scripts/marathon/run-cycle.mjs "$@" 2>&1 | tee -a data/test-marathon/marathon-output.log
fi
