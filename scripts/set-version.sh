#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Version Manager
# Sets the version across all package files using CalVer (YYYY.MM.DD)
#
# Usage:
#   ./scripts/set-version.sh              # Auto-generate from today's date
#   ./scripts/set-version.sh 2026.03.29   # Set specific version
#   ./scripts/set-version.sh --bump       # Increment daily build number
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

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

# ── Update all version files ──────────────────────────────────────

# Convert CalVer to semver for Tauri/Cargo.
# Windows MSI requires each segment ≤ 255, so we can't use 0.2026.329.
# Strategy: MAJOR = last 2 digits of year, MINOR = month*31+day, PATCH = build#
# 2026.03.29 → 26.122.0   |   2026.03.29.2 → 26.122.2
SEMVER_VERSION=$(echo "$VERSION" | awk -F. '{
    year = $1 % 100;
    month = $2 + 0;
    day = $3 + 0;
    minor = month * 31 + day;
    build = ($4 ? $4 : 0);
    printf "%d.%d.%d", year, minor, build
}')

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

# 8. Create/update VERSION file at root
echo "$VERSION" > "$ROOT/VERSION"
echo "  ✓ VERSION"

echo ""
echo "Version set to $VERSION across all packages."
echo "Commit with: git commit -am 'release: $VERSION'"
echo "Tag with:    git tag v$VERSION && git push origin v$VERSION"
