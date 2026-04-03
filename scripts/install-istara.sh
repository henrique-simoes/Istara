#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Installer
#
#   curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash
#
# Installs Istara (server or client) with all dependencies.
# Interactive terminal wizard for first-time configuration.
# ═══════════════════════════════════════════════════════════════════
{ # Wraps entire script so partial downloads don't execute

set -eo pipefail

# Show where the script fails if it crashes
trap 'echo ""; echo "  ✗ Installation failed at line $LINENO. Please report this at:"; echo "    https://github.com/henrique-simoes/Istara/issues"; echo ""' ERR

REPO="henrique-simoes/Istara"
INSTALL_DIR="${ISTARA_DIR:-$HOME/.istara}"
VERSION=""

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
ask()     { printf "  ${BOLD}?${NC} %s" "$*"; }
note()    { printf "  ${DIM}%s${NC}\n" "$*"; }

prompt_default() {
    local q="$1" d="$2"
    # Must write prompt to /dev/tty, NOT stdout — because callers use $(prompt_default ...)
    # which captures stdout. Without this, the prompt is invisible and the script hangs.
    printf "  ${BOLD}?${NC} %s ${DIM}[%s]${NC}: " "$q" "$d" >/dev/tty
    local r; read -r r </dev/tty
    echo "${r:-$d}"
}

prompt_password() {
    printf "  ${BOLD}?${NC} %s: " "$1" >/dev/tty
    local p; read -rs p </dev/tty; printf "\n" >/dev/tty
    echo "$p"
}

confirm() {
    local q="$1" d="${2:-y}"
    local yn; [ "$d" = "y" ] && yn="[Y/n]" || yn="[y/N]"
    ask "$q $yn: "
    local r; read -r r </dev/tty
    r="${r:-$d}"
    case "$r" in [Yy]*) return 0 ;; *) return 1 ;; esac
}

print_mode_summary() {
    echo ""
    if [ "$1" = "server" ]; then
        echo "  ${BOLD}What this machine will become:${NC}"
        echo "    • An Istara ${BOLD}server${NC} with backend, frontend, and local data"
        echo "    • A local AI workstation using ${BOLD}LM Studio${NC} or ${BOLD}Ollama${NC}"
        echo "    • A desktop companion app in ${BOLD}Server mode${NC} for start/stop, donation, and updates"
        echo ""
        note "Use this when this computer will host the main Istara workspace."
    else
        echo "  ${BOLD}What this machine will become:${NC}"
        echo "    • An Istara ${BOLD}client${NC} that joins an existing server"
        echo "    • A desktop companion app in ${BOLD}Client mode${NC}"
        echo "    • An optional compute donor if you enable local LM Studio or Ollama later"
        echo ""
        note "Use this when an admin already gave you an rcl_ connection string."
    fi
}

print_homebrew_help() {
    echo ""
    echo "  ${BOLD}Homebrew is not installed yet.${NC}"
    echo "  Homebrew is the standard package manager for macOS."
    echo "  Istara uses it to install and update tools like Python, Node.js, and Git safely."
    echo "  You can keep using Istara normally afterward — Homebrew just manages the underlying packages."
    echo ""
}

print_llm_provider_help() {
    echo ""
    echo "  Istara needs one local AI engine on the ${BOLD}server${NC} machine."
    echo ""
    echo "  1) ${BOLD}LM Studio${NC} ${DIM}(recommended for most people)${NC}"
    echo "     Desktop app with a visual interface for browsing, downloading, and loading models."
    echo "     Best if you want the clearest first-time setup."
    echo ""
    echo "  2) ${BOLD}Ollama${NC}"
    echo "     Lightweight command-line local model runner."
    echo "     Best if you prefer terminal workflows or a headless setup."
    echo ""
}

print_first_model_steps() {
    echo ""
    echo "  ${BOLD}Next step: install your first model${NC}"
    if [ "$1" = "ollama" ]; then
        echo "    1. Run ${CYAN}ollama pull qwen3:latest${NC}"
        echo "    2. If Ollama is not already serving, run ${CYAN}ollama serve${NC}"
        echo "    3. Start Istara and it will use Ollama at ${CYAN}http://localhost:11434${NC}"
    else
        echo "    1. Open ${BOLD}LM Studio${NC}"
        echo "    2. Download a chat model such as ${BOLD}Qwen 3${NC} from the model library"
        echo "    3. Start the local server in LM Studio so it listens on ${CYAN}http://localhost:1234${NC}"
        echo "    4. Start Istara and it will detect the running LM Studio server"
    fi
    echo ""
}

print_client_connection_help() {
    echo ""
    echo "  ${BOLD}What to paste here${NC}"
    echo "  Your server admin should give you a one-line invite that starts with ${BOLD}rcl_${NC}."
    echo "  That string already contains the server address and relay credentials."
    echo "  You do ${BOLD}not${NC} need to type URLs or tokens manually."
    echo ""
}

# ── OS Detection ─────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *) fail "Unsupported platform: $OS"; exit 1 ;;
esac

# ── Version comparison (no sort -V, works on all macOS) ──────────
version_ge() {
    local v1="$1" v2="$2"
    local major1 minor1 major2 minor2
    major1=$(echo "$v1" | cut -d. -f1)
    minor1=$(echo "$v1" | cut -d. -f2)
    major2=$(echo "$v2" | cut -d. -f1)
    minor2=$(echo "$v2" | cut -d. -f2)
    [ "${major1:-0}" -gt "${major2:-0}" ] && return 0
    [ "${major1:-0}" -eq "${major2:-0}" ] && [ "${minor1:-0}" -ge "${minor2:-0}" ] && return 0
    return 1
}

# ── Dependency detection ─────────────────────────────────────────
detect_python() {
    local paths=(
        "/opt/homebrew/bin/python3.12"
        "/opt/homebrew/bin/python3"
        "/usr/local/bin/python3"
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
        "$HOME/.pyenv/shims/python3"
        "python3"
    )
    for py in "${paths[@]}"; do
        # Skip if not executable
        if ! command -v "$py" >/dev/null 2>&1 && ! [ -x "$py" ]; then
            continue
        fi
        # Get version (skip Apple CLI tools stub which opens a dialog)
        local ver=""
        ver=$("$py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || true)
        if [ -n "$ver" ] && version_ge "$ver" "3.11"; then
            echo "$py"
            return 0
        fi
    done
    return 1
}

detect_node() {
    local paths=(
        "node"
        "/opt/homebrew/bin/node"
        "/usr/local/bin/node"
        "/opt/homebrew/opt/node/bin/node"
        "/opt/homebrew/opt/node@20/bin/node"
        "/opt/homebrew/opt/node@22/bin/node"
    )
    # nvm
    [ -f "$HOME/.nvm/alias/default" ] && {
        local v; v=$(cat "$HOME/.nvm/alias/default")
        paths+=("$HOME/.nvm/versions/node/$v/bin/node")
    }
    # fnm
    [ -d "$HOME/.local/share/fnm" ] && {
        for nd_dir in "$HOME/.local/share/fnm/node-versions"/*/installation/bin; do
            [ -x "$nd_dir/node" ] && paths+=("$nd_dir/node")
        done
    }
    for nd in "${paths[@]}"; do
        if command -v "$nd" >/dev/null 2>&1 || [ -x "$nd" ]; then
            local ver; ver=$("$nd" --version 2>&1 | grep -oE '[0-9]+' | head -1)
            if [ "${ver:-0}" -ge 18 ]; then
                echo "$nd"; return 0
            fi
        fi
    done
    return 1
}

detect_npm() {
    local nd; nd=$(detect_node 2>/dev/null) || nd=""
    if [ -n "$nd" ]; then
        local npm_path="$(dirname "$nd")/npm"
        [ -x "$npm_path" ] && { echo "$npm_path"; return 0; }
    fi
    command -v npm >/dev/null 2>&1 && { echo "npm"; return 0; }
    # Check keg-only Homebrew paths
    for keg in "/opt/homebrew/opt/node/bin/npm" "/opt/homebrew/opt/node@22/bin/npm" "/opt/homebrew/opt/node@20/bin/npm"; do
        [ -x "$keg" ] && { echo "$keg"; return 0; }
    done
    return 1
}

detect_git() { command -v git >/dev/null 2>&1; }

detect_brew() {
    command -v brew >/dev/null 2>&1 && return 0
    [ -x "/opt/homebrew/bin/brew" ] && { eval "$(/opt/homebrew/bin/brew shellenv)"; return 0; }
    [ -x "/usr/local/bin/brew" ] && { eval "$(/usr/local/bin/brew shellenv)"; return 0; }
    return 1
}

detect_lm_studio() {
    [ -d "/Applications/LM Studio.app" ] && return 0
    curl -s --connect-timeout 2 http://localhost:1234/v1/models >/dev/null 2>&1 && return 0
    return 1
}

detect_ollama() {
    command -v ollama >/dev/null 2>&1 && return 0
    [ -d "/Applications/Ollama.app" ] && return 0
    curl -s --connect-timeout 2 http://localhost:11434/api/tags >/dev/null 2>&1 && return 0
    return 1
}

# ── Install missing dependencies ─────────────────────────────────
ensure_homebrew() {
    detect_brew && return 0
    print_homebrew_help
    if ! confirm "Install Homebrew now so Istara can install missing dependencies?" "y"; then
        fail "Homebrew is required to install missing dependencies on macOS."
        exit 1
    fi
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/tty
    # Activate in current shell
    if [ -x "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    ok "Homebrew installed"
}

ensure_python() {
    local found_py=""
    found_py=$(detect_python 2>/dev/null) || found_py=""
    if [ -n "$found_py" ]; then
        local pyver; pyver=$("$found_py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        ok "Python $pyver ($found_py)"
        return 0
    fi
    info "Installing Python 3.12..."
    ensure_homebrew
    brew install python@3.12
    ok "Python 3.12 installed"
}

ensure_node() {
    local found_node=""
    found_node=$(detect_node 2>/dev/null) || found_node=""
    if [ -n "$found_node" ]; then
        local nver; nver=$("$found_node" --version 2>&1 || echo "unknown")
        ok "Node $nver ($found_node)"
        # Make sure this node's bin dir is in PATH for npm
        local node_bin; node_bin="$(dirname "$found_node")"
        case ":$PATH:" in
            *":$node_bin:"*) ;;  # already in PATH
            *) export PATH="$node_bin:$PATH" ;;
        esac
        return 0
    fi
    info "Installing Node.js..."
    ensure_homebrew
    # Install 'node' (main formula, links properly) not 'node@20' (keg-only, link conflicts)
    brew install node 2>/dev/null || {
        # If main formula fails, try node@22 or node@20 and add keg path
        brew install node@22 2>/dev/null || brew install node@20 2>/dev/null || {
            fail "Failed to install Node.js via Homebrew"
            exit 1
        }
    }
    # Add Homebrew keg-only node paths if needed
    for keg in node node@22 node@20; do
        local keg_path; keg_path="$(brew --prefix "$keg" 2>/dev/null)/bin" || continue
        if [ -x "$keg_path/node" ]; then
            export PATH="$keg_path:$PATH"
            break
        fi
    done
    # Verify it actually works
    found_node=$(detect_node 2>/dev/null) || found_node=""
    if [ -z "$found_node" ]; then
        fail "Node.js installed but not found in PATH. Try: brew link --overwrite node"
        exit 1
    fi
    ok "Node $($(detect_node) --version 2>&1) installed"
}

ensure_git() {
    detect_git && { ok "Git $(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"; return 0; }
    info "Installing Git..."
    if [ "$PLATFORM" = "macos" ]; then
        xcode-select --install 2>/dev/null || true
    else
        sudo apt-get install -y git 2>/dev/null || sudo yum install -y git 2>/dev/null || true
    fi
    ok "Git installed"
}

# ── Generate secrets ─────────────────────────────────────────────
gen_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 32 | tr -d '/+=' | cut -c1-32
    else
        LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32
    fi
}

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

echo ""
echo -e "  ${BOLD}🐾 Istara Installer${NC}"
echo -e "  ${DIM}Local-first AI agents for UX Research${NC}"
echo ""

# ── Step 1: Choose mode ──────────────────────────────────────────
header "Step 1: Installation Mode"
echo "  1) ${BOLD}Server${NC} — Full Istara with AI agents, web UI, and LLM inference"
echo "  2) ${BOLD}Client${NC} — Connect to an existing Istara server (relay + tray app)"
echo ""
ask "Choose [1/2]: "
MODE_CHOICE=""; read -r MODE_CHOICE </dev/tty
case "$MODE_CHOICE" in
    2) MODE="client" ;;
    *) MODE="server" ;;
esac
ok "Mode: $MODE"
print_mode_summary "$MODE"

# ── Step 2: Check/install dependencies ───────────────────────────
header "Step 2: Dependencies"

ensure_git

if [ "$MODE" = "server" ]; then
    ensure_python
    ensure_node

    # Check for LLM provider
    LLM_PROVIDER=""
    if detect_lm_studio && detect_ollama; then
        ok "LM Studio and Ollama detected"
        echo ""
        echo "  Both local AI providers are available on this machine."
        ask "Which one should Istara use by default? [1=LM Studio/2=Ollama]: "
        provider_choice=""; read -r provider_choice </dev/tty
        case "$provider_choice" in
            2) LLM_PROVIDER="ollama" ;;
            *) LLM_PROVIDER="lmstudio" ;;
        esac
    elif detect_lm_studio; then
        ok "LM Studio detected"
        LLM_PROVIDER="lmstudio"
    elif detect_ollama; then
        ok "Ollama detected"
        LLM_PROVIDER="ollama"
    else
        warn "No LLM provider detected"
        print_llm_provider_help
        ask "Choose your provider [1=LM Studio/2=Ollama/skip]: "
        llm_choice=""; read -r llm_choice </dev/tty
        case "$llm_choice" in
            2)
                info "Installing Ollama..."
                curl -fsSL https://ollama.com/install.sh | sh
                ok "Ollama installed"
                LLM_PROVIDER="ollama"
                ;;
            1|"")
                info "Opening LM Studio download page..."
                open "https://lmstudio.ai" 2>/dev/null || true
                LLM_PROVIDER="lmstudio"
                ;;
            *) warn "Skipped — you can install LM Studio or Ollama later" ;;
        esac
    fi

    if [ -n "${LLM_PROVIDER:-}" ]; then
        ok "Default LLM provider: $LLM_PROVIDER"
        print_first_model_steps "$LLM_PROVIDER"
    fi
else
    ensure_node
fi

# ── Step 3: Download Istara ──────────────────────────────────────
header "Step 3: Installing Istara"

if [ -d "$INSTALL_DIR/.git" ]; then
    info "Existing installation found at $INSTALL_DIR — updating..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || git pull
    ok "Updated to latest"
else
    info "Cloning Istara to $INSTALL_DIR..."
    git clone "https://github.com/${REPO}.git" "$INSTALL_DIR"
    ok "Cloned to $INSTALL_DIR"
fi

cd "$INSTALL_DIR"
VERSION=$(cat VERSION 2>/dev/null || echo "dev")
ok "Version: $VERSION"

# ── Step 4: Setup (server only) ──────────────────────────────────
if [ "$MODE" = "server" ]; then
    header "Step 4: Backend Setup"

    PYTHON=$(detect_python) || { fail "Python 3.11+ not found. Install it and try again."; exit 1; }
    info "Using Python: $PYTHON"

    # Create venv
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        info "Creating Python virtual environment..."
        "$PYTHON" -m venv "$INSTALL_DIR/venv" || { fail "Failed to create venv. Is python3-venv installed?"; exit 1; }
        ok "Virtual environment created"
    else
        ok "Virtual environment exists"
    fi

    # Install pip deps
    info "Upgrading pip..."
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip 2>&1 | tail -1
    info "Installing backend dependencies (this takes 1-3 minutes)..."
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt" 2>&1 | grep -E "^(Collecting|Installing|Successfully)" | head -20 || true
    ok "Backend dependencies installed"

    # Frontend
    header "Step 5: Frontend Setup"
    NPM=$(detect_npm) || { fail "npm not found. Install Node.js and try again."; exit 1; }
    info "Using npm: $NPM"
    info "Installing frontend dependencies (this takes 1-2 minutes)..."
    cd "$INSTALL_DIR/frontend"
    "$NPM" ci 2>&1 | tail -3 || "$NPM" install 2>&1 | tail -3
    ok "Frontend dependencies installed"

    info "Building frontend (this takes 1-2 minutes)..."
    NEXT_PUBLIC_API_URL="http://localhost:8000" \
    NEXT_PUBLIC_WS_URL="ws://localhost:8000" \
    "$NPM" run build 2>&1 | tail -5 || { fail "Frontend build failed"; exit 1; }
    ok "Frontend built"

    # Data directories
    cd "$INSTALL_DIR"
    mkdir -p data/{uploads,projects,lance_db,backups,channel_audio}
    ok "Data directories created"

# ── Step 6: Configuration ──────────────────────────────────────
    if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
        header "Step 6: Configuration"

        BACKEND_PORT=$(prompt_default "Backend API port" "8000")
        FRONTEND_PORT=$(prompt_default "Frontend port" "3000")

        # Team Mode / Security
        echo ""
        echo "  ${BOLD}Security Mode:${NC}"
        echo "  1) ${BOLD}Local${NC} — No login required. Safe only for localhost (your computer)."
        echo "  2) ${BOLD}Team${NC}  — Username/password required. Essential for servers or networks."
        echo ""
        ask "Choose [1/2]: "
        TEAM_CHOICE=""; read -r TEAM_CHOICE </dev/tty
        if [ "$TEAM_CHOICE" = "2" ]; then
            TEAM_MODE="true"
            ok "Mode: Team (Secure)"
        else
            TEAM_MODE="false"
            warn "Mode: Local (Unauthenticated)"
            info "Anyone on your network will have full access to Istara."
        fi

        [ -z "${LLM_PROVIDER:-}" ] && LLM_PROVIDER="lmstudio"

        case "$LLM_PROVIDER" in
            ollama) LLM_HOST="http://localhost:11434"; LLM_MODEL="qwen3:latest" ;;
            *)      LLM_HOST="http://localhost:1234";  LLM_MODEL="default" ;;
        esac

        JWT_SECRET=$(gen_secret)
        ENCRYPT_KEY=$(gen_secret)
        NET_TOKEN=$(gen_secret)

        cat > "$INSTALL_DIR/backend/.env" <<ENVEOF
# Istara Backend Configuration — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
# NOTE: NEXT_PUBLIC_* vars are frontend-only (baked into the Next.js build).
# They are NOT needed here — the backend ignores them.

LLM_PROVIDER=${LLM_PROVIDER}
$(echo "$LLM_PROVIDER" | tr '[:lower:]' '[:upper:]')_HOST=${LLM_HOST}
$(echo "$LLM_PROVIDER" | tr '[:lower:]' '[:upper:]')_MODEL=${LLM_MODEL}

DATABASE_URL=sqlite+aiosqlite:///./data/istara.db
JWT_SECRET=${JWT_SECRET}
DATA_ENCRYPTION_KEY=${ENCRYPT_KEY}
NETWORK_ACCESS_TOKEN=${NET_TOKEN}
TEAM_MODE=${TEAM_MODE}

CORS_ORIGINS=http://localhost:${FRONTEND_PORT}

RAG_CHUNK_SIZE=1500
RAG_CHUNK_OVERLAP=200
RAG_TOP_K=6
RAG_SCORE_THRESHOLD=0.35
RESOURCE_RESERVE_RAM_GB=4
RESOURCE_RESERVE_CPU_PERCENT=30
ENVEOF

        chmod 600 "$INSTALL_DIR/backend/.env"
        ok "Configuration saved"
    else
        ok "Configuration exists (backend/.env)"
    fi

    # Relay setup
    cd "$INSTALL_DIR/relay"
    "$NPM" install --silent 2>/dev/null || true
    ok "Relay dependencies installed"

else
    # Client mode — just install relay
    header "Step 4: Client Setup"
    NPM=$(detect_npm)
    cd "$INSTALL_DIR/relay"
    "$NPM" install --silent 2>/dev/null || true
    ok "Relay installed"

    print_client_connection_help
    ask "Paste your connection string (from server admin): "
    CONN_STR=""; read -r CONN_STR </dev/tty
    mkdir -p "$HOME/.istara"
    if [ -n "$CONN_STR" ]; then
        CLIENT_DONATE="true"
        ok "Connection string saved for Client mode"
    else
        CLIENT_DONATE="false"
        warn "No connection string saved yet — you can add one later in the desktop app"
    fi
    cat > "$HOME/.istara/config.json" <<CEOF
{
  "mode": "client",
  "server_url": "",
  "ws_url": "",
  "connection_string": "$CONN_STR",
  "donate_compute": $CLIENT_DONATE,
  "install_dir": "$INSTALL_DIR"
}
CEOF
fi

# ── Step 7: Create launcher script ───────────────────────────────
header "Setting up launcher"

mkdir -p "$INSTALL_DIR/bin"
cat > "$INSTALL_DIR/bin/istara" <<'LAUNCHER'
#!/usr/bin/env bash
ISTARA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ISTARA_DIR/istara.sh" "$@"
LAUNCHER
chmod +x "$INSTALL_DIR/bin/istara"

# Add to PATH
PROFILE=""
if [ "${SHELL#*zsh}" != "$SHELL" ]; then
    PROFILE="${ZDOTDIR:-$HOME}/.zshrc"
elif [ "${SHELL#*bash}" != "$SHELL" ]; then
    PROFILE="$HOME/.bashrc"
    [ -f "$HOME/.bash_profile" ] && PROFILE="$HOME/.bash_profile"
else
    PROFILE="$HOME/.profile"
fi

if [ -f "$PROFILE" ] && ! grep -qF "$INSTALL_DIR/bin" "$PROFILE" 2>/dev/null; then
    printf '\n# Istara\nexport PATH="%s/bin:$PATH"\n' "$INSTALL_DIR" >> "$PROFILE"
    ok "Added to PATH in $PROFILE"
fi
export PATH="$INSTALL_DIR/bin:$PATH"

# Save server config
if [ "$MODE" = "server" ]; then
    mkdir -p "$HOME/.istara"
    cat > "$HOME/.istara/config.json" <<SEOF
{
  "mode": "server",
  "server_url": "http://localhost:${FRONTEND_PORT:-3000}",
  "ws_url": "ws://localhost:${BACKEND_PORT:-8000}/ws/relay",
  "connection_string": "",
  "donate_compute": false,
  "install_dir": "$INSTALL_DIR"
}
SEOF
fi

# ── Step 8: Install Desktop App Companion ───────────────────
# This entire section is failure-safe — desktop app install errors must not kill the installer.
if [ "$PLATFORM" = "macos" ]; then
    if [ ! -d "/Applications/Istara.app" ] && [ ! -d "$HOME/Applications/Istara.app" ]; then
        echo ""
        header "Step 8: Install Istara Desktop App"
        echo "  Istara Desktop is the companion app that lives in your menu bar."
        echo "  It reads the mode you chose above and adapts automatically:"
        echo "    • ${BOLD}Server mode${NC}: start/stop Istara, check local AI status, updates"
        echo "    • ${BOLD}Client mode${NC}: open the remote workspace, paste/change invites, donate compute"
        echo ""
        # Run in a subshell so set -e doesn't kill the parent on failure
        (
            set +e  # Disable exit-on-error for this subshell
            info "Downloading latest Istara.app..."
            # Get latest DMG URL from GitHub releases
            API_RESPONSE=$(curl -sL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null || echo "")
            LATEST_DMG=$(echo "$API_RESPONSE" | grep -o '"browser_download_url":[[:space:]]*"[^"]*\.dmg"' 2>/dev/null \
                | head -1 | sed 's/.*"browser_download_url":[[:space:]]*"//' | sed 's/"$//' 2>/dev/null || echo "")
            if [ -n "$LATEST_DMG" ]; then
                TMPDIR_DMG=$(mktemp -d)
                curl -fSL "$LATEST_DMG" -o "$TMPDIR_DMG/Istara.dmg" 2>/dev/null
                if [ -f "$TMPDIR_DMG/Istara.dmg" ]; then
                    hdiutil attach "$TMPDIR_DMG/Istara.dmg" -quiet -nobrowse -mountpoint "$TMPDIR_DMG/mnt" 2>/dev/null
                    if [ -d "$TMPDIR_DMG/mnt/Istara.app" ]; then
                        mkdir -p "$HOME/Applications" 2>/dev/null || true
                        cp -R "$TMPDIR_DMG/mnt/Istara.app" /Applications/ 2>/dev/null || \
                            cp -R "$TMPDIR_DMG/mnt/Istara.app" "$HOME/Applications/" 2>/dev/null
                        hdiutil detach "$TMPDIR_DMG/mnt" -quiet 2>/dev/null
                        ok "Istara.app installed to Applications"
                        info "Launch it from Applications or Spotlight — it will open in $MODE mode."
                    else
                        hdiutil detach "$TMPDIR_DMG/mnt" -quiet 2>/dev/null
                        warn "DMG did not contain Istara.app — you can install it manually later"
                    fi
                else
                    warn "Download failed — you can install the desktop app manually from GitHub Releases"
                fi
                rm -rf "$TMPDIR_DMG" 2>/dev/null
            else
                warn "No DMG found in latest release (GitHub API may be rate-limited)."
                warn "You can install the desktop app later from: https://github.com/${REPO}/releases"
            fi
        ) || true  # Ensure subshell failure doesn't kill the installer
    else
        ok "Istara.app already installed"
    fi
fi

# ═══════════════════════════════════════════════════════════════════
# Done!
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "  ${GREEN}${BOLD}✓ Istara $VERSION installed successfully!${NC}"
echo ""

if [ "$MODE" = "server" ]; then
    echo -e "  ${BOLD}Start the server:${NC}"
    echo -e "    ${CYAN}istara start${NC}"
    echo ""
    echo -e "  ${BOLD}Open in browser:${NC}"
    echo -e "    ${CYAN}http://localhost:${FRONTEND_PORT:-3000}${NC}"
    echo ""
    echo -e "  ${BOLD}Connection string for clients:${NC}"
    echo -e "    Generate one in ${BOLD}Settings → Connection Strings${NC} after starting"
    echo ""

    if confirm "Start Istara now?"; then
        # If tray app is installed, launch it (it auto-starts the server)
        if [ -d "/Applications/Istara.app" ] || [ -d "$HOME/Applications/Istara.app" ]; then
            info "Launching Istara tray app (it will start the server automatically)..."
            open -a Istara 2>/dev/null || true
            sleep 3
            ok "Istara tray app launched — check your menu bar for the tray icon"
            info "Opening browser..."
            open "http://localhost:${FRONTEND_PORT:-3000}" 2>/dev/null || true
        else
            cd "$INSTALL_DIR"
            ./istara.sh start
            info "Opening browser..."
            open "http://localhost:${FRONTEND_PORT:-3000}" 2>/dev/null || true
        fi
    fi
else
    echo -e "  ${BOLD}Client setup complete:${NC}"
    if [ -n "${CONN_STR:-}" ]; then
        echo -e "    ${CYAN}Open Istara Desktop${NC} from Applications or Spotlight"
        echo -e "    It will use your saved ${BOLD}rcl_${NC} invite and open in ${BOLD}Client mode${NC}."
    else
        echo -e "    ${CYAN}Open Istara Desktop${NC}, then choose ${BOLD}Change Server / Invite...${NC}"
        echo -e "    and paste the ${BOLD}rcl_${NC} invite from your admin."
    fi
    echo ""
    echo -e "  ${BOLD}Need to help your server with local AI compute later?${NC}"
    echo -e "    Start LM Studio or Ollama on this machine, then turn on ${BOLD}Compute Donation${NC}"
    echo -e "    from the desktop app."
    echo ""
fi

echo -e "  ${DIM}Documentation: https://github.com/${REPO}/wiki${NC}"
echo -e "  ${DIM}Issues:        https://github.com/${REPO}/issues${NC}"
echo ""

} # End of wrapper — prevents partial-download execution
