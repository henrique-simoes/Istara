#!/usr/bin/env bash
# Build ReClaw.app as a macOS .dmg installer.
# Prerequisites: Rust toolchain, Node.js, create-dmg (brew install create-dmg)
#
# Usage:
#   cd installer/macos && ./build-dmg.sh
#
# For notarization (CI only):
#   APPLE_ID=you@apple.com APPLE_TEAM_ID=XXXXXXXXXX ./build-dmg.sh --notarize

set -euo pipefail
cd "$(dirname "$0")/../.."

echo "=== Building ReClaw Desktop (Tauri) ==="
cd desktop
npm install 2>/dev/null || true

# Build universal macOS binary (Intel + Apple Silicon)
npx tauri build --target universal-apple-darwin 2>&1

APP_PATH="src-tauri/target/universal-apple-darwin/release/bundle/macos/ReClaw.app"
DMG_PATH="ReClaw-$(cat src-tauri/tauri.conf.json | python3 -c 'import sys,json; print(json.load(sys.stdin)["version"])').dmg"

if [ ! -d "$APP_PATH" ]; then
  echo "ERROR: Build failed — $APP_PATH not found"
  exit 1
fi

echo "=== Creating .dmg ==="
cd ..
create-dmg \
  --volname "ReClaw" \
  --volicon "desktop/src-tauri/icons/icon.icns" \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "ReClaw.app" 150 190 \
  --app-drop-link 450 190 \
  --hide-extension "ReClaw.app" \
  "installer/macos/$DMG_PATH" \
  "desktop/$APP_PATH" || true

echo "=== DMG created: installer/macos/$DMG_PATH ==="

# Optional notarization
if [ "${1:-}" = "--notarize" ] && [ -n "${APPLE_ID:-}" ]; then
  echo "=== Notarizing ==="
  xcrun notarytool submit "installer/macos/$DMG_PATH" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" \
    --wait
  xcrun stapler staple "installer/macos/$DMG_PATH"
  echo "=== Notarization complete ==="
fi
