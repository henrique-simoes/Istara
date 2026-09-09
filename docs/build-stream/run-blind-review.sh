#!/bin/bash
# Blind reviewer runner: reads ONLY the blind pack, writes ONLY the measurement sheet.
# Run: nohup bash docs/build-stream/run-blind-review.sh > /tmp/blind-review.log 2>&1 &
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR/../.." || exit 1
SHEET=docs/build-stream/2026-09-08-systemwide-audit-coverage.measurement.md
{
echo "# Measurement Sheet (blind — frozen before comparison)"
echo ""
echo "Reviewer: independent background process. Sources: blind pack only."
echo ""
run() { echo "## $1"; echo '```'; eval "$2" 2>&1 | tail -n 6; echo '```'; echo ""; }
run "M-1 test_files" "pytest tests/test_files.py -q"
run "M-2 test_websocket" "pytest tests/test_websocket.py -q"
run "M-3 scope contracts x3" "pytest tests/test_project_scope_contracts.py tests/test_harness_project_scope_contracts.py tests/test_agent_scope_contracts.py -q"
run "M-4 pi replacement" "pytest tests/test_pi_replacement_candidate.py -q"
run "M-5 chat" "pytest tests/test_chat.py -q"
run "M-6 benchmark" "python scripts/security_benchmark.py --fail-on-threshold | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[\"status\"], d[\"counts\"], d[\"score_percent\"])'"
echo "## M-7 quarantine guards"
grep -n "QUARANTINED" backend/app/api/routes/files.py
echo ""
echo "## M-8 display events"
grep -n 'result_display\|"type": "content"' backend/app/api/routes/chat.py | head -n 12
echo "direct appends of display (expect none):"
grep -n "all_text_parts.append(result_display" backend/app/api/routes/chat.py || echo "(none found)"
echo ""
echo "## M-9 new tests in isolation"
for t in test_quarantined_files_are_not_servable test_file_serve_denies_stranger_and_anonymous test_ws_rejects_missing_and_invalid_token test_ws_denies_nonmember_project_with_4003 test_relay_rejects_unauthenticated_and_accepts_network_token; do
  f=tests/test_files.py; case "$t" in test_ws*|test_relay*) f=tests/test_websocket.py;; esac
  echo "### $t"; pytest "$f::$t" -q 2>&1 | tail -n 2; echo ""
done
echo "## M-10 ruff on six files"
ruff check backend/app/api/routes/files.py backend/app/api/routes/chat.py tests/test_files.py tests/test_websocket.py tests/test_project_scope_contracts.py --output-format concise 2>&1 | tail -n 18
echo ""
echo "## M-11 diff check"
git diff --check && echo CLEAN
echo ""
echo "## M-12 literal match spot-check"
for lit in 'await get_active_project_or_404(db, request, scoped_project_id, min_role="researcher"' 'source_ids: list[str] | None = None' 'project_id: str | None = None' 'Human approval marks this task Done'; do
  echo "### [$lit]"; grep -rl -- "$lit" backend/app frontend/src 2>/dev/null | head -n 4; echo ""
done
echo "## M-13 refutations"
echo "### a. quarantined served to viewers (expect 403 in test):"
pytest tests/test_files.py::test_quarantined_files_are_not_servable -q 2>&1 | tail -n 2
echo "### d. unauth relay connects (expect 4001 close in test):"
pytest tests/test_websocket.py::test_relay_rejects_unauthenticated_and_accepts_network_token -q 2>&1 | tail -n 2
echo ""
echo "FROZEN: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$SHEET" 2>&1
echo "done $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /tmp/blind-review.log
