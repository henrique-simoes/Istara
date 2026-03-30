#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# Istara macOS Installer Builder
# Produces a complete .dmg with Istara.app + bundled source code
# ═══════════════════════════════════════════════════════════════════════
#
# Prerequisites:
#   - Rust toolchain (rustup)
#   - Node.js 20+
#   - create-dmg (brew install create-dmg)
#
# Usage:
#   cd installer/macos && ./build-dmg.sh
#
# For notarization (CI only):
#   APPLE_ID=you@apple.com APPLE_TEAM_ID=XXX APPLE_APP_PASSWORD=xxx ./build-dmg.sh --notarize

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION=$(grep '"version"' "$ROOT/desktop/src-tauri/tauri.conf.json" | head -1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
DMG_NAME="Istara-${VERSION:-0.1.0}.dmg"

echo "═══════════════════════════════════════════════════════════════"
echo "  Building Istara $VERSION for macOS"
echo "═══════════════════════════════════════════════════════════════"

# ── Step 1: Build Tauri app ──────────────────────────────────────────
echo ""
echo "▸ Step 1/5: Building Tauri desktop app..."
cd "$ROOT/desktop"

# Install frontend deps for the setup wizard webview
if [ -f "package.json" ]; then
    npm install 2>/dev/null || true
fi

# Build universal binary (Intel + Apple Silicon)
if command -v cargo &> /dev/null; then
    npx tauri build --target universal-apple-darwin 2>&1
else
    echo "  ⚠ Rust not installed. Install via: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
    exit 1
fi

APP_PATH="src-tauri/target/universal-apple-darwin/release/bundle/macos/Istara.app"
if [ ! -d "$APP_PATH" ]; then
    # Fallback: try release bundle without universal target
    APP_PATH="src-tauri/target/release/bundle/macos/Istara.app"
fi
if [ ! -d "$APP_PATH" ]; then
    echo "  ✗ Build failed — .app bundle not found"
    exit 1
fi
echo "  ✓ Tauri app built: $APP_PATH"

# ── Step 2: Bundle Istara source code into .app ─────────────────────
echo ""
echo "▸ Step 2/5: Bundling Istara source code into app bundle..."
RESOURCES="$APP_PATH/Contents/Resources/istara"
mkdir -p "$RESOURCES"

# Backend (Python source — venv created at first run by setup wizard)
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
    --exclude='data/' --exclude='venv/' --exclude='.pytest_cache/' \
    "$ROOT/backend/" "$RESOURCES/backend/"

# Frontend (source — built at first run by setup wizard)
rsync -a --exclude='node_modules/' --exclude='.next/' --exclude='out/' \
    "$ROOT/frontend/" "$RESOURCES/frontend/"

# Relay
rsync -a --exclude='node_modules/' "$ROOT/relay/" "$RESOURCES/relay/"

# Config and scripts
cp "$ROOT/.env.example" "$RESOURCES/.env.example"
cp "$ROOT/istara.sh" "$RESOURCES/istara.sh"
chmod +x "$RESOURCES/istara.sh"

# Skills definitions (system skills, not proposals/stats)
rsync -a --exclude='_proposals.json' --exclude='_creation_proposals.json' \
    --exclude='_usage_stats.json' --exclude='_deleted/' \
    "$ROOT/backend/app/skills/definitions/" "$RESOURCES/backend/app/skills/definitions/"

# Agent personas (system agents only — no UUID custom agents)
for persona in istara-main istara-devops istara-ui-audit istara-ux-eval istara-sim; do
    rsync -a "$ROOT/backend/app/agents/personas/$persona/" \
        "$RESOURCES/backend/app/agents/personas/$persona/"
done

echo "  ✓ Source bundled ($(du -sh "$RESOURCES" | cut -f1) total)"

# ── Step 3: Create LaunchAgent template ──────────────────────────────
echo ""
echo "▸ Step 3/5: Including LaunchAgent for auto-start..."
mkdir -p "$RESOURCES/installer"
cp "$ROOT/installer/macos/com.istara.server.plist" "$RESOURCES/installer/" 2>/dev/null || true
echo "  ✓ LaunchAgent template included"

# ── Step 4: Create .dmg ─────────────────────────────────────────────
echo ""
echo "▸ Step 4/5: Creating DMG installer..."
cd "$ROOT"

if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "Istara" \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "Istara.app" 150 190 \
        --app-drop-link 450 190 \
        --hide-extension "Istara.app" \
        "installer/macos/$DMG_NAME" \
        "desktop/$APP_PATH" 2>&1 || true
    echo "  ✓ DMG created: installer/macos/$DMG_NAME"
else
    # Fallback: simple DMG creation
    hdiutil create -volname "Istara" -srcfolder "desktop/$APP_PATH" \
        -ov -format UDZO "installer/macos/$DMG_NAME" 2>&1
    echo "  ✓ DMG created (basic): installer/macos/$DMG_NAME"
fi

# ── Step 5: Notarize (optional, CI only) ─────────────────────────────
if [ "${1:-}" = "--notarize" ] && [ -n "${APPLE_ID:-}" ]; then
    echo ""
    echo "▸ Step 5/5: Notarizing with Apple..."
    xcrun notarytool submit "installer/macos/$DMG_NAME" \
        --apple-id "$APPLE_ID" \
        --team-id "${APPLE_TEAM_ID:-}" \
        --password "${APPLE_APP_PASSWORD:-}" \
        --wait 2>&1
    xcrun stapler staple "installer/macos/$DMG_NAME" 2>&1
    echo "  ✓ Notarization complete"
else
    echo ""
    echo "▸ Step 5/5: Skipping notarization (no APPLE_ID set)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✓ Istara $VERSION macOS installer ready!"
echo "  📦 installer/macos/$DMG_NAME"
echo "  📏 $(du -h "installer/macos/$DMG_NAME" | cut -f1)"
echo "═══════════════════════════════════════════════════════════════"
