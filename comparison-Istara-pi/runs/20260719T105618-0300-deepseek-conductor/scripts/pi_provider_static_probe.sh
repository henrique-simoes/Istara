#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/logs/pi-provider-static-probe.json"

LOCAL_RESOLVE_STATUS="missing"
if node -e "require.resolve('@earendil-works/pi-ai')" >/dev/null 2>&1; then
  LOCAL_RESOLVE_STATUS="present"
fi

NPM_VERSION=""
if command -v npm >/dev/null 2>&1; then
  NPM_VERSION="$(npm view @earendil-works/pi-ai version 2>/dev/null || true)"
fi

python3 - "$OUT" "$LOCAL_RESOLVE_STATUS" "$NPM_VERSION" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
local_status = sys.argv[2]
npm_version = sys.argv[3]
result = {
    "probe": "pi_provider_static",
    "package": "@earendil-works/pi-ai",
    "local_package_resolvable": local_status == "present",
    "npm_latest_version": npm_version or None,
    "deepseek_provider_smoke_executed": False,
    "blocked_reason": None,
    "next_gate": None,
}
if local_status != "present":
    result["blocked_reason"] = (
        "@earendil-works/pi-ai is not installed in the Istara repo runtime; "
        "executing Pi's provider layer would require dependency installation or a local Pi checkout."
    )
    result["next_gate"] = (
        "Ask owner before installing Pi packages or cloning/checking out the Pi monorepo."
    )
else:
    result["next_gate"] = "Run a Pi-provider DeepSeek smoke through @earendil-works/pi-ai."
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
PY

