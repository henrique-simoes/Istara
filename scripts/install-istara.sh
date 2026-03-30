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

set -euo pipefail

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

prompt_default() {
    local q="$1" d="$2"
    ask "$q ${DIM}[$d]${NC}: "
    local r; read -r r </dev/tty
    echo "${r:-$d}"
}

prompt_password() {
    ask "$1: "
    local p; read -rs p </dev/tty; echo "" >&2
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

# ── OS Detection ─────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *) fail "Unsupported platform: $OS"; exit 1 ;;
esac

# ── Version comparison ───────────────────────────────────────────
version_ge() {
    local v1="$1" v2="$2"
    [ "$(printf '%s\n' "$v1" "$v2" | sort -V | head -n1)" = "$v2" ]
}

# ── Dependency detection ─────────────────────────────────────────
detect_python() {
    local paths=("python3" "/opt/homebrew/bin/python3" "/usr/local/bin/python3"
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
        "$HOME/.pyenv/shims/python3" "/usr/bin/python3")
    for py in "${paths[@]}"; do
        if command -v "$py" >/dev/null 2>&1 || [ -x "$py" ]; then
            local ver; ver=$("$py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            if version_ge "${ver:-0}" "3.11"; then
                echo "$py"; return 0
            fi
        fi
    done
    return 1
}

detect_node() {
    local paths=("node" "/opt/homebrew/bin/node" "/usr/local/bin/node")
    # nvm
    [ -f "$HOME/.nvm/alias/default" ] && {
        local v; v=$(cat "$HOME/.nvm/alias/default")
        paths+=("$HOME/.nvm/versions/node/$v/bin/node")
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
    local nd; nd=$(detect_node 2>/dev/null) || nd="node"
    local npm_path="$(dirname "$nd")/npm"
    [ -x "$npm_path" ] && { echo "$npm_path"; return 0; }
    command -v npm >/dev/null 2>&1 && { echo "npm"; return 0; }
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
    detect_python >/dev/null 2>&1 && { ok "Python $($(detect_python) --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"; return 0; }
    info "Installing Python 3.12..."
    ensure_homebrew
    brew install python@3.12
    ok "Python 3.12 installed"
}

ensure_node() {
    detect_node >/dev/null 2>&1 && { ok "Node $($(detect_node) --version 2>&1)"; return 0; }
    info "Installing Node.js 20..."
    ensure_homebrew
    brew install node@20
    export PATH="$(brew --prefix node@20)/bin:$PATH"
    ok "Node.js 20 installed"
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

# ── Step 2: Check/install dependencies ───────────────────────────
header "Step 2: Dependencies"

ensure_git

if [ "$MODE" = "server" ]; then
    ensure_python
    ensure_node

    # Check for LLM provider
    LLM_PROVIDER=""
    if detect_lm_studio; then
        ok "LM Studio detected"
        LLM_PROVIDER="lmstudio"
    elif detect_ollama; then
        ok "Ollama detected"
        LLM_PROVIDER="ollama"
    else
        warn "No LLM provider detected"
        echo ""
        echo "  Istara needs a local LLM. Install one:"
        echo "    ${BOLD}a)${NC} LM Studio — ${DIM}https://lmstudio.ai${NC} (GUI, recommended)"
        echo "    ${BOLD}b)${NC} Ollama    — ${DIM}https://ollama.com${NC} (CLI, lightweight)"
        echo ""
        ask "Install now? [a/b/skip]: "
        local llm_choice=""; read -r llm_choice </dev/tty
        case "$llm_choice" in
            a|A) open "https://lmstudio.ai" 2>/dev/null || true; LLM_PROVIDER="lmstudio" ;;
            b|B)
                info "Installing Ollama..."
                curl -fsSL https://ollama.com/install.sh | sh
                ok "Ollama installed"
                LLM_PROVIDER="ollama"
                ;;
            *) warn "Skipped — you can install LM Studio or Ollama later" ;;
        esac
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

    PYTHON=$(detect_python)

    # Create venv
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        info "Creating Python virtual environment..."
        "$PYTHON" -m venv "$INSTALL_DIR/venv"
        ok "Virtual environment created"
    else
        ok "Virtual environment exists"
    fi

    # Install pip deps
    info "Installing backend dependencies (this takes 1-2 minutes)..."
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt" --quiet
    ok "Backend dependencies installed"

    # Frontend
    header "Step 5: Frontend Setup"
    NPM=$(detect_npm)
    info "Installing frontend dependencies..."
    cd "$INSTALL_DIR/frontend"
    "$NPM" ci --silent 2>/dev/null || "$NPM" install --silent
    ok "Frontend dependencies installed"

    info "Building frontend (this takes 1-2 minutes)..."
    NEXT_PUBLIC_API_URL="http://localhost:8000" \
    NEXT_PUBLIC_WS_URL="ws://localhost:8000" \
    "$NPM" run build --silent
    ok "Frontend built"

    # Data directories
    cd "$INSTALL_DIR"
    mkdir -p data/{uploads,projects,lance_db,backups,channel_audio}
    ok "Data directories created"

    # Generate .env
    if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
        header "Step 6: Configuration"

        BACKEND_PORT=$(prompt_default "Backend API port" "8000")
        FRONTEND_PORT=$(prompt_default "Frontend port" "3000")

        [ -z "${LLM_PROVIDER:-}" ] && LLM_PROVIDER="lmstudio"

        case "$LLM_PROVIDER" in
            ollama) LLM_HOST="http://localhost:11434"; LLM_MODEL="qwen3:latest" ;;
            *)      LLM_HOST="http://localhost:1234";  LLM_MODEL="default" ;;
        esac

        JWT_SECRET=$(gen_secret)
        ENCRYPT_KEY=$(gen_secret)
        NET_TOKEN=$(gen_secret)

        cat > "$INSTALL_DIR/backend/.env" <<ENVEOF
# Istara Configuration — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)

LLM_PROVIDER=${LLM_PROVIDER}
$(echo "$LLM_PROVIDER" | tr '[:lower:]' '[:upper:]')_HOST=${LLM_HOST}
$(echo "$LLM_PROVIDER" | tr '[:lower:]' '[:upper:]')_MODEL=${LLM_MODEL}

DATABASE_URL=sqlite+aiosqlite:///./data/istara.db
JWT_SECRET=${JWT_SECRET}
DATA_ENCRYPTION_KEY=${ENCRYPT_KEY}
NETWORK_ACCESS_TOKEN=${NET_TOKEN}
TEAM_MODE=false

NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
NEXT_PUBLIC_WS_URL=ws://localhost:${BACKEND_PORT}
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

    echo ""
    ask "Paste your connection string (from server admin): "
    CONN_STR=""; read -r CONN_STR </dev/tty
    if [ -n "$CONN_STR" ]; then
        mkdir -p "$HOME/.istara"
        cat > "$HOME/.istara/config.json" <<CEOF
{
  "mode": "client",
  "server_url": "",
  "ws_url": "",
  "connection_string": "$CONN_STR",
  "donate_compute": true,
  "install_dir": "$INSTALL_DIR"
}
CEOF
        ok "Connection string saved"
    fi
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
        cd "$INSTALL_DIR"
        ./istara.sh start
    fi
else
    echo -e "  ${BOLD}Start the relay:${NC}"
    echo -e "    ${CYAN}cd $INSTALL_DIR/relay && node index.mjs --connection-string '$CONN_STR'${NC}"
    echo ""
fi

echo -e "  ${DIM}Documentation: https://github.com/${REPO}/wiki${NC}"
echo -e "  ${DIM}Issues:        https://github.com/${REPO}/issues${NC}"
echo ""

} # End of wrapper — prevents partial-download execution
