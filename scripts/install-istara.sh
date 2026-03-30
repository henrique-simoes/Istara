#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Installer — one-liner: curl -fsSL https://get.istara.dev | sh
#
# Detects platform, downloads the latest release, installs it.
# macOS: downloads DMG, copies .app to /Applications
# Linux: downloads AppImage (when available) or clones from source
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

REPO="henrique-simoes/Istara"
GITHUB_API="https://api.github.com/repos/${REPO}/releases/latest"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}▸${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }

echo ""
echo -e "${BOLD}🐾 Istara Installer${NC}"
echo -e "   Local-first AI agents for UX Research"
echo ""

# ── Detect platform ──────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *) error "Unsupported platform: $OS"; exit 1 ;;
esac

info "Platform: $OS ($ARCH)"

# ── Get latest release info ──────────────────────────────────────
info "Checking latest release..."
RELEASE_JSON=$(curl -sS "$GITHUB_API" 2>/dev/null)
VERSION=$(echo "$RELEASE_JSON" | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"v\([^"]*\)".*/\1/')

if [ -z "$VERSION" ]; then
    error "Could not determine latest version. Check your internet connection."
    echo "  Manual download: https://github.com/${REPO}/releases"
    exit 1
fi

ok "Latest version: $VERSION"

# ── macOS Installation ───────────────────────────────────────────
if [ "$PLATFORM" = "macos" ]; then
    DMG_NAME="Istara-${VERSION}.dmg"
    DMG_URL="https://github.com/${REPO}/releases/download/v${VERSION}/${DMG_NAME}"

    info "Downloading ${DMG_NAME}..."
    TMPDIR_INSTALL=$(mktemp -d)
    DMG_PATH="${TMPDIR_INSTALL}/${DMG_NAME}"

    curl -fSL --progress-bar "$DMG_URL" -o "$DMG_PATH"
    ok "Downloaded $(du -h "$DMG_PATH" | cut -f1)"

    info "Mounting DMG..."
    MOUNT_POINT=$(hdiutil attach "$DMG_PATH" -nobrowse -readonly 2>/dev/null | grep "/Volumes" | awk '{print $NF}')

    if [ -z "$MOUNT_POINT" ]; then
        # Try alternative parsing
        MOUNT_POINT="/Volumes/Istara"
    fi

    if [ ! -d "$MOUNT_POINT/Istara.app" ]; then
        error "Could not find Istara.app in the DMG"
        hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
        rm -rf "$TMPDIR_INSTALL"
        exit 1
    fi

    info "Installing to /Applications..."
    if [ -d "/Applications/Istara.app" ]; then
        warn "Existing installation found — replacing"
        rm -rf "/Applications/Istara.app"
    fi

    cp -R "$MOUNT_POINT/Istara.app" /Applications/
    ok "Istara.app installed to /Applications"

    # Cleanup
    hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
    rm -rf "$TMPDIR_INSTALL"

    # Remove quarantine attribute (downloaded from internet)
    xattr -dr com.apple.quarantine /Applications/Istara.app 2>/dev/null || true

    echo ""
    echo -e "${GREEN}${BOLD}✓ Istara $VERSION installed successfully!${NC}"
    echo ""
    echo "  To launch:   open /Applications/Istara.app"
    echo "  Or:          Cmd+Space → type 'Istara' → Enter"
    echo ""

    # Ask to launch
    read -p "Launch Istara now? [Y/n] " -n 1 -r REPLY
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        open /Applications/Istara.app
        ok "Istara launched — check your menubar for the 🐾 icon"
    fi

# ── Linux Installation ───────────────────────────────────────────
elif [ "$PLATFORM" = "linux" ]; then
    warn "Linux native installer coming soon."
    echo ""
    echo "  For now, install via Docker:"
    echo ""
    echo "    git clone https://github.com/${REPO}.git"
    echo "    cd Istara"
    echo "    cp .env.example .env"
    echo "    docker compose up -d"
    echo ""
    echo "  Or install from source:"
    echo ""
    echo "    git clone https://github.com/${REPO}.git"
    echo "    cd Istara"
    echo "    cd backend && python3 -m venv venv && source venv/bin/activate"
    echo "    pip install -r requirements.txt"
    echo "    cd ../frontend && npm install && npm run build"
    echo "    cd .. && ./istara.sh start"
    echo ""

# ── Windows ──────────────────────────────────────────────────────
elif [ "$PLATFORM" = "windows" ]; then
    EXE_URL="https://github.com/${REPO}/releases/download/v${VERSION}/Istara_*_x64-setup.exe"
    echo ""
    echo "  Download the Windows installer from:"
    echo "  https://github.com/${REPO}/releases/tag/v${VERSION}"
    echo ""
    echo "  Or use winget (coming soon):"
    echo "    winget install istara"
    echo ""
fi

echo ""
echo -e "  ${CYAN}Documentation:${NC}  https://github.com/${REPO}/wiki"
echo -e "  ${CYAN}Issues:${NC}         https://github.com/${REPO}/issues"
echo ""
