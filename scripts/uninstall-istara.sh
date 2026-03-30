#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Uninstaller
#
#   curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/uninstall-istara.sh | bash
#
# Removes Istara and optionally all dependencies it installed.
#
# ⚠  WARNING: This is DESTRUCTIVE. Back up your data FIRST.
#    Your research projects, uploads, and database will be deleted.
#    This cannot be undone.
# ═══════════════════════════════════════════════════════════════════
{ # Wraps entire script so partial downloads don't execute

set -eo pipefail

INSTALL_DIR="${ISTARA_DIR:-$HOME/.istara}"
CONFIG_FILE="$HOME/.istara/config.json"

# ── Colours ──────────────────────────────────────────────────────
if [ -t 1 ]; then
    BOLD=$(printf '\033[1m')
    CYAN=$(printf '\033[0;36m')
    GREEN=$(printf '\033[0;32m')
    YELLOW=$(printf '\033[1;33m')
    RED=$(printf '\033[0;31m')
    DIM=$(printf '\033[2m')
    NC=$(printf '\033[0m')
else
    BOLD='' CYAN='' GREEN='' YELLOW='' RED='' DIM='' NC=''
fi

info()    { printf "  ${CYAN}▸${NC} %s\n" "$*"; }
ok()      { printf "  ${GREEN}✓${NC} %s\n" "$*"; }
warn()    { printf "  ${YELLOW}⚠${NC} %s\n" "$*"; }
fail()    { printf "  ${RED}✗${NC} %s\n" "$*" >&2; }
header()  { printf "\n${BOLD}${CYAN}%s${NC}\n\n" "$*"; }

confirm() {
    local q="$1" d="${2:-n}"
    local yn; [ "$d" = "y" ] && yn="[Y/n]" || yn="[y/N]"
    printf "  ${BOLD}?${NC} %s %s: " "$q" "$yn" >/dev/tty
    local r; read -r r </dev/tty
    r="${r:-$d}"
    case "$r" in [Yy]*) return 0 ;; *) return 1 ;; esac
}

confirm_type() {
    local expected="$1"
    printf "  ${BOLD}?${NC} Type ${RED}%s${NC} to confirm: " "$expected" >/dev/tty
    local r; read -r r </dev/tty
    [ "$r" = "$expected" ]
}

# ── Try to read install_dir from config ─────────────────────────
if [ -f "$CONFIG_FILE" ]; then
    SAVED_DIR=$(grep -o '"install_dir"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" 2>/dev/null \
        | head -1 | sed 's/.*"install_dir"[[:space:]]*:[[:space:]]*"//' | sed 's/"//')
    if [ -n "$SAVED_DIR" ] && [ -d "$SAVED_DIR" ]; then
        INSTALL_DIR="$SAVED_DIR"
    fi
fi

# ── OS Detection ─────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *) PLATFORM="unknown" ;;
esac

# ═══════════════════════════════════════════════════════════════════
# WARNING BANNER
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "  ${RED}${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${RED}${BOLD}║              ⚠  ISTARA UNINSTALLER  ⚠                    ║${NC}"
echo -e "  ${RED}${BOLD}║                                                           ║${NC}"
echo -e "  ${RED}${BOLD}║  This will permanently delete Istara and all its data.    ║${NC}"
echo -e "  ${RED}${BOLD}║  Your research projects, uploads, database, and config    ║${NC}"
echo -e "  ${RED}${BOLD}║  will be PERMANENTLY DESTROYED. This cannot be undone.    ║${NC}"
echo -e "  ${RED}${BOLD}║                                                           ║${NC}"
echo -e "  ${RED}${BOLD}║  Back up ~/.istara/data/ BEFORE continuing.               ║${NC}"
echo -e "  ${RED}${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Show what we found ──────────────────────────────────────────
header "Detected Installation"

FOUND_ANYTHING=false

if [ -d "$INSTALL_DIR" ]; then
    INSTALL_SIZE=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1 || echo "unknown")
    info "Install directory: ${BOLD}$INSTALL_DIR${NC} ($INSTALL_SIZE)"
    FOUND_ANYTHING=true

    # Count data files
    if [ -d "$INSTALL_DIR/data" ]; then
        DATA_SIZE=$(du -sh "$INSTALL_DIR/data" 2>/dev/null | cut -f1 || echo "unknown")
        warn "Research data: ${BOLD}$DATA_SIZE${NC} in $INSTALL_DIR/data/"
    fi
    if [ -f "$INSTALL_DIR/backend/.env" ]; then
        info "Configuration: $INSTALL_DIR/backend/.env"
    fi
    if [ -d "$INSTALL_DIR/venv" ]; then
        VENV_SIZE=$(du -sh "$INSTALL_DIR/venv" 2>/dev/null | cut -f1 || echo "unknown")
        info "Python venv: $VENV_SIZE"
    fi
    if [ -d "$INSTALL_DIR/frontend/node_modules" ]; then
        NM_SIZE=$(du -sh "$INSTALL_DIR/frontend/node_modules" 2>/dev/null | cut -f1 || echo "unknown")
        info "Frontend node_modules: $NM_SIZE"
    fi
    if [ -d "$INSTALL_DIR/frontend/.next" ]; then
        info "Frontend build cache: $INSTALL_DIR/frontend/.next/"
    fi
else
    warn "Install directory not found at $INSTALL_DIR"
fi

if [ -f "$CONFIG_FILE" ]; then
    info "Config: $CONFIG_FILE"
    FOUND_ANYTHING=true
fi

# Desktop app
DESKTOP_APP=""
if [ "$PLATFORM" = "macos" ]; then
    if [ -d "/Applications/Istara.app" ]; then
        info "Desktop app: /Applications/Istara.app"
        DESKTOP_APP="/Applications/Istara.app"
        FOUND_ANYTHING=true
    fi
    if [ -d "$HOME/Applications/Istara.app" ]; then
        info "Desktop app: $HOME/Applications/Istara.app"
        DESKTOP_APP="$HOME/Applications/Istara.app"
        FOUND_ANYTHING=true
    fi
fi

# LaunchAgent
LAUNCHAGENT="$HOME/Library/LaunchAgents/com.istara.server.plist"
if [ -f "$LAUNCHAGENT" ]; then
    info "LaunchAgent: $LAUNCHAGENT"
    FOUND_ANYTHING=true
fi

# Application Support (Tauri data dir)
TAURI_DATA=""
if [ "$PLATFORM" = "macos" ] && [ -d "$HOME/Library/Application Support/com.istara.desktop" ]; then
    TAURI_DATA="$HOME/Library/Application Support/com.istara.desktop"
    info "Tauri app data: $TAURI_DATA"
    FOUND_ANYTHING=true
fi

# Log files
LOGS_FOUND=false
if [ -f "/tmp/istara-stdout.log" ] || [ -f "/tmp/istara-stderr.log" ]; then
    info "Log files: /tmp/istara-*.log"
    LOGS_FOUND=true
    FOUND_ANYTHING=true
fi

# Homebrew cask
BREW_CASK=false
if command -v brew >/dev/null 2>&1; then
    if brew list --cask 2>/dev/null | grep -q "istara"; then
        info "Homebrew cask: henrique-simoes/istara/istara"
        BREW_CASK=true
        FOUND_ANYTHING=true
    fi
fi

# PATH entry in shell config
SHELL_PROFILES=()
for p in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    if [ -f "$p" ] && grep -qF ".istara/bin" "$p" 2>/dev/null; then
        info "PATH entry in: $p"
        SHELL_PROFILES+=("$p")
        FOUND_ANYTHING=true
    fi
done

echo ""

if [ "$FOUND_ANYTHING" = false ]; then
    ok "No Istara installation found. Nothing to uninstall."
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
# FIRST CONFIRMATION
# ═══════════════════════════════════════════════════════════════════
if ! confirm "Have you backed up any data you want to keep?" "n"; then
    echo ""
    info "Back up your data first:"
    echo -e "    ${CYAN}cp -r $INSTALL_DIR/data ~/Desktop/istara-backup${NC}"
    echo -e "    ${CYAN}cp $INSTALL_DIR/backend/.env ~/Desktop/istara-env-backup${NC}"
    echo ""
    info "Run this uninstaller again when you're ready."
    exit 0
fi

echo ""
warn "This will ${RED}permanently delete${NC} everything listed above."
echo ""

if ! confirm_type "uninstall"; then
    echo ""
    info "Uninstall cancelled. Nothing was changed."
    exit 0
fi

echo ""

# ═══════════════════════════════════════════════════════════════════
# STOP RUNNING PROCESSES
# ═══════════════════════════════════════════════════════════════════
header "Step 1: Stopping Istara processes"

# Stop backend (uvicorn)
if pgrep -f "uvicorn.*app.main:app" >/dev/null 2>&1; then
    info "Stopping backend server..."
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
    sleep 1
    ok "Backend stopped"
else
    ok "Backend not running"
fi

# Stop frontend (next)
if pgrep -f "next.*start\|next.*dev" >/dev/null 2>&1; then
    info "Stopping frontend server..."
    pkill -f "next.*start\|next.*dev" 2>/dev/null || true
    sleep 1
    ok "Frontend stopped"
else
    ok "Frontend not running"
fi

# Stop relay (node relay)
if pgrep -f "node.*relay.*index" >/dev/null 2>&1; then
    info "Stopping relay..."
    pkill -f "node.*relay.*index" 2>/dev/null || true
    sleep 1
    ok "Relay stopped"
else
    ok "Relay not running"
fi

# Stop desktop app
if [ "$PLATFORM" = "macos" ] && pgrep -x "Istara" >/dev/null 2>&1; then
    info "Closing Istara desktop app..."
    osascript -e 'tell application "Istara" to quit' 2>/dev/null || pkill -x "Istara" 2>/dev/null || true
    sleep 2
    ok "Desktop app closed"
fi

# ═══════════════════════════════════════════════════════════════════
# REMOVE LAUNCHAGENT
# ═══════════════════════════════════════════════════════════════════
header "Step 2: Removing auto-start"

if [ -f "$LAUNCHAGENT" ]; then
    info "Unloading LaunchAgent..."
    launchctl unload "$LAUNCHAGENT" 2>/dev/null || true
    rm -f "$LAUNCHAGENT"
    ok "LaunchAgent removed"
else
    ok "No LaunchAgent found"
fi

# ═══════════════════════════════════════════════════════════════════
# REMOVE DESKTOP APP
# ═══════════════════════════════════════════════════════════════════
header "Step 3: Removing desktop app"

if [ "$BREW_CASK" = true ]; then
    info "Uninstalling Homebrew cask..."
    brew uninstall --cask istara 2>/dev/null || true
    brew untap henrique-simoes/istara 2>/dev/null || true
    ok "Homebrew cask removed"
elif [ -n "$DESKTOP_APP" ] && [ -d "$DESKTOP_APP" ]; then
    info "Removing $DESKTOP_APP..."
    rm -rf "$DESKTOP_APP"
    ok "Desktop app removed"
else
    ok "No desktop app found"
fi

# Tauri Application Support data
if [ -n "$TAURI_DATA" ] && [ -d "$TAURI_DATA" ]; then
    info "Removing Tauri app data..."
    rm -rf "$TAURI_DATA"
    ok "Tauri app data removed"
fi

# ═══════════════════════════════════════════════════════════════════
# REMOVE INSTALL DIRECTORY (the big one)
# ═══════════════════════════════════════════════════════════════════
header "Step 4: Removing Istara files"

if [ -d "$INSTALL_DIR" ]; then
    info "Removing $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    ok "Install directory removed"
else
    ok "Install directory already gone"
fi

# Config directory (if different from install dir)
if [ -d "$HOME/.istara" ]; then
    rm -rf "$HOME/.istara"
    ok "Config directory removed (~/.istara)"
fi

# ═══════════════════════════════════════════════════════════════════
# CLEAN UP PATH AND SHELL CONFIG
# ═══════════════════════════════════════════════════════════════════
header "Step 5: Cleaning shell configuration"

for profile in "${SHELL_PROFILES[@]}"; do
    if [ -f "$profile" ]; then
        info "Removing Istara PATH from $profile..."
        # Remove the "# Istara" comment line and the export PATH line
        sed -i.bak '/# Istara/d' "$profile" 2>/dev/null || true
        sed -i.bak '/\.istara\/bin/d' "$profile" 2>/dev/null || true
        # Clean up backup
        rm -f "${profile}.bak"
        ok "Cleaned $profile"
    fi
done

if [ ${#SHELL_PROFILES[@]} -eq 0 ]; then
    ok "No shell config changes to revert"
fi

# ═══════════════════════════════════════════════════════════════════
# REMOVE LOG FILES
# ═══════════════════════════════════════════════════════════════════
header "Step 6: Removing logs"

rm -f /tmp/istara-stdout.log /tmp/istara-stderr.log 2>/dev/null
ok "Log files removed"

# ═══════════════════════════════════════════════════════════════════
# OPTIONAL: REMOVE DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════
header "Step 7: Dependencies (optional)"

echo -e "  ${DIM}The installer may have installed these via Homebrew.${NC}"
echo -e "  ${DIM}Only remove them if nothing else on your system needs them.${NC}"
echo ""

if command -v brew >/dev/null 2>&1; then
    # Python
    if brew list python@3.12 >/dev/null 2>&1; then
        if confirm "Remove Python 3.12 (Homebrew)?" "n"; then
            info "Removing Python 3.12..."
            brew uninstall python@3.12 2>/dev/null || true
            ok "Python 3.12 removed"
        else
            ok "Kept Python 3.12"
        fi
    fi

    # Node
    if brew list node@20 >/dev/null 2>&1; then
        if confirm "Remove Node.js 20 (Homebrew)?" "n"; then
            info "Removing Node.js 20..."
            brew uninstall node@20 2>/dev/null || true
            ok "Node.js 20 removed"
        else
            ok "Kept Node.js 20"
        fi
    fi
    if brew list node >/dev/null 2>&1; then
        if confirm "Remove Node.js (Homebrew)?" "n"; then
            info "Removing Node.js..."
            brew uninstall node 2>/dev/null || true
            ok "Node.js removed"
        else
            ok "Kept Node.js"
        fi
    fi
fi

# Ollama
if command -v ollama >/dev/null 2>&1 || [ -d "/Applications/Ollama.app" ]; then
    if confirm "Remove Ollama?" "n"; then
        info "Removing Ollama..."
        if [ "$PLATFORM" = "macos" ]; then
            # Stop Ollama
            pkill -x "Ollama" 2>/dev/null || true
            launchctl unload "$HOME/Library/LaunchAgents/com.ollama.server.plist" 2>/dev/null || true
            # Remove app
            rm -rf "/Applications/Ollama.app" 2>/dev/null || true
            rm -rf "$HOME/Applications/Ollama.app" 2>/dev/null || true
            # Remove CLI
            rm -f "/usr/local/bin/ollama" 2>/dev/null || true
            # Remove models and data
            rm -rf "$HOME/.ollama" 2>/dev/null || true
            rm -f "$HOME/Library/LaunchAgents/com.ollama.server.plist" 2>/dev/null || true
            ok "Ollama removed (app, CLI, and models)"
        else
            # Linux
            sudo rm -f /usr/local/bin/ollama 2>/dev/null || true
            sudo rm -rf /usr/share/ollama 2>/dev/null || true
            rm -rf "$HOME/.ollama" 2>/dev/null || true
            ok "Ollama removed"
        fi
    else
        ok "Kept Ollama"
    fi
fi

# ═══════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "  ${GREEN}${BOLD}✓ Istara has been completely uninstalled.${NC}"
echo ""
echo -e "  ${DIM}What was removed:${NC}"
echo -e "    ${DIM}• Istara source code, venv, and node_modules${NC}"
echo -e "    ${DIM}• Research data, database, and uploads${NC}"
echo -e "    ${DIM}• Configuration and secrets (.env)${NC}"
echo -e "    ${DIM}• Desktop app and auto-start agent${NC}"
echo -e "    ${DIM}• Shell PATH entries and log files${NC}"
echo ""
echo -e "  ${DIM}Restart your terminal for PATH changes to take effect.${NC}"
echo ""
echo -e "  ${DIM}We're sorry to see you go. Feedback welcome at:${NC}"
echo -e "  ${DIM}  https://github.com/henrique-simoes/Istara/issues${NC}"
echo ""

} # End of wrapper — prevents partial-download execution
