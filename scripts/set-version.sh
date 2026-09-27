#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Version Manager
# Sets the version across all package files using CalVer (YYYY.MM.DD)
#
# Usage:
#   ./scripts/set-version.sh              # Auto-generate from today's date
#   ./scripts/set-version.sh 2026.03.29   # Set specific version
#   ./scripts/set-version.sh --bump       # Increment daily build number
#   ./scripts/set-version.sh --semver-of 2026.09.27.3   # Print the desktop semver (126.9.2703)
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Convert CalVer to semver for Tauri, Cargo, the MSI and the updater.
# Windows MSI requires MAJOR <= 255, MINOR <= 255, PATCH <= 65535. The old mapping
# (MINOR = month*31+day) passed 255 on 8 August and broke every Windows build after it.
# Strategy: MAJOR = 100 + (year % 100), MINOR = month, PATCH = day*100 + build.
#   2026.09.27 -> 126.9.2700   |   2026.09.27.3 -> 126.9.2703   |   2027.01.02 -> 127.1.200
# MAJOR starts at 126 so every new version sorts above the old 26.<month*31+day>.<build> ones,
# and installed apps still see the update.
calver_to_semver() {
    echo "$1" | awk -F. '{
        year = $1 % 100;
        month = $2 + 0;
        day = $3 + 0;
        build = ($4 ? $4 + 0 : 0);
        if (NF < 3 || month < 1 || month > 12 || day < 1 || day > 31 || build > 99) { exit 1 }
        printf "%d.%d.%d", 100 + year, month, day * 100 + build
    }'
}

if [ "${1:-}" = "--semver-of" ]; then
    calver_to_semver "${2:?usage: set-version.sh --semver-of YYYY.MM.DD[.N]}" || {
        echo "Not a CalVer version: ${2}" >&2
        exit 1
    }
    echo
    exit 0
fi

# Generate version from date or use argument
if [ "${1:-}" = "--bump" ]; then
    # Read current CalVer version from VERSION file (NOT tauri.conf.json which has semver)
    CURRENT=$(cat "$ROOT/VERSION" 2>/dev/null | tr -d '[:space:]')
    TODAY=$(date -u +%Y.%m.%d)

    if [[ "$CURRENT" == "$TODAY"* ]]; then
        # Same day — increment build number
        BUILD=$(echo "$CURRENT" | awk -F. '{print ($4 ? $4+1 : 2)}')
        VERSION="${TODAY}.${BUILD}"
    else
        VERSION="$TODAY"
    fi
elif [ -n "${1:-}" ]; then
    VERSION="$1"
else
    VERSION=$(date -u +%Y.%m.%d)
fi

echo "Setting Istara version to: $VERSION"

SEMVER_VERSION=$(calver_to_semver "$VERSION") || {
    echo "Not a CalVer version (YYYY.MM.DD[.N]): $VERSION" >&2
    exit 1
}

# ── Update all version files ──────────────────────────────────────

# 1. Tauri config (JSON) — needs semver
sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$SEMVER_VERSION\"/" "$ROOT/desktop/src-tauri/tauri.conf.json"
rm -f "$ROOT/desktop/src-tauri/tauri.conf.json.bak"
echo "  ✓ desktop/src-tauri/tauri.conf.json (semver: $SEMVER_VERSION)"

# 2. Desktop package.json
sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/desktop/package.json"
rm -f "$ROOT/desktop/package.json.bak"
echo "  ✓ desktop/package.json"

# 3. Rust Cargo.toml — needs semver
sed -i.bak "s/^version = \"[^\"]*\"/version = \"$SEMVER_VERSION\"/" "$ROOT/desktop/src-tauri/Cargo.toml"
rm -f "$ROOT/desktop/src-tauri/Cargo.toml.bak"
echo "  ✓ desktop/src-tauri/Cargo.toml (semver: $SEMVER_VERSION)"

# 4. Frontend package.json
sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/frontend/package.json"
rm -f "$ROOT/frontend/package.json.bak"
echo "  ✓ frontend/package.json"

# 5. Relay package.json
sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$ROOT/relay/package.json"
rm -f "$ROOT/relay/package.json.bak"
echo "  ✓ relay/package.json"

# 6. Backend pyproject.toml
sed -i.bak "s/^version = \"[^\"]*\"/version = \"$VERSION\"/" "$ROOT/backend/pyproject.toml"
rm -f "$ROOT/backend/pyproject.toml.bak"
echo "  ✓ backend/pyproject.toml"

# 7. NSIS installer
sed -i.bak "s/!define VERSION \"[^\"]*\"/!define VERSION \"$VERSION\"/" "$ROOT/installer/windows/nsis-installer.nsi"
rm -f "$ROOT/installer/windows/nsis-installer.nsi.bak"
echo "  ✓ installer/windows/nsis-installer.nsi"

# 7b. npm lockfiles carry the package version too (root and packages[""])
for lock in desktop/package-lock.json frontend/package-lock.json relay/package-lock.json; do
    [ -f "$ROOT/$lock" ] || continue
    python3 - "$ROOT/$lock" "$VERSION" <<'PY'
import json, sys
path, version = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
data["version"] = version
if "" in data.get("packages", {}):
    data["packages"][""]["version"] = version
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
PY
    echo "  ✓ $lock"
done

# 8. Create/update VERSION file at root
echo "$VERSION" > "$ROOT/VERSION"
echo "  ✓ VERSION"

echo ""
echo "Version set to $VERSION across all packages."
echo "Commit with: git commit -am 'release: $VERSION'"
echo "Tag with:    git tag v$VERSION && git push origin v$VERSION"
