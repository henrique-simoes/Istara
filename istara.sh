#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# istara.sh — Start or stop Istara backend + frontend
#
# Usage:
#   ./istara.sh          Start both (or stop if already running)
#   ./istara.sh start    Start backend + frontend
#   ./istara.sh stop     Stop backend + frontend
#   ./istara.sh status   Show what's running
#   ./istara.sh restart  Stop then start
#   ./istara.sh logs     Tail both log files
# ─────────────────────────────────────────────────────────

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID_FILE="$ROOT/.istara-backend.pid"
FRONTEND_PID_FILE="$ROOT/.istara-frontend.pid"
BACKEND_LOG="$ROOT/.istara-backend.log"
FRONTEND_LOG="$ROOT/.istara-frontend.log"

BACKEND_PORT=8000
FRONTEND_PORT=3000

# Find the correct Python — prefer venv, then Homebrew, then system
_find_python() {
    [ -x "$ROOT/venv/bin/python" ] && { echo "$ROOT/venv/bin/python"; return; }
    [ -x "$ROOT/venv/bin/python3" ] && { echo "$ROOT/venv/bin/python3"; return; }
    command -v python3 >/dev/null 2>&1 && { echo "python3"; return; }
    [ -x "/opt/homebrew/bin/python3.12" ] && { echo "/opt/homebrew/bin/python3.12"; return; }
    [ -x "/opt/homebrew/bin/python3" ] && { echo "/opt/homebrew/bin/python3"; return; }
    echo "python3"  # last resort
}

# Find npm — prefer Homebrew linked, then keg-only paths
_find_npm() {
    command -v npm >/dev/null 2>&1 && { echo "npm"; return; }
    [ -x "/opt/homebrew/bin/npm" ] && { echo "/opt/homebrew/bin/npm"; return; }
    [ -x "/opt/homebrew/opt/node/bin/npm" ] && { echo "/opt/homebrew/opt/node/bin/npm"; return; }
    [ -x "/opt/homebrew/opt/node@22/bin/npm" ] && { echo "/opt/homebrew/opt/node@22/bin/npm"; return; }
    [ -x "/opt/homebrew/opt/node@20/bin/npm" ] && { echo "/opt/homebrew/opt/node@20/bin/npm"; return; }
    echo "npm"  # last resort
}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

_is_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

_status() {
    echo ""
    echo -e "${CYAN}═══ Istara Status ═══${NC}"
    echo ""

    if _is_running "$BACKEND_PID_FILE"; then
        local bpid=$(cat "$BACKEND_PID_FILE")
        echo -e "  Backend:  ${GREEN}● running${NC}  (PID $bpid)  http://localhost:$BACKEND_PORT"
    else
        echo -e "  Backend:  ${RED}○ stopped${NC}"
    fi

    if _is_running "$FRONTEND_PID_FILE"; then
        local fpid=$(cat "$FRONTEND_PID_FILE")
        echo -e "  Frontend: ${GREEN}● running${NC}  (PID $fpid)  http://localhost:$FRONTEND_PORT"
    else
        echo -e "  Frontend: ${RED}○ stopped${NC}"
    fi

    # Check LLM servers (informational only — we don't manage these)
    if curl -s --connect-timeout 2 "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
        local llm_status
        llm_status=$(curl -s --connect-timeout 2 "http://localhost:$BACKEND_PORT/api/settings/status" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('llm_connected','unknown'))" 2>/dev/null || echo "unknown")
        if [ "$llm_status" = "true" ] || [ "$llm_status" = "True" ]; then
            echo -e "  LLM:      ${GREEN}● connected${NC}  (via ComputeRegistry)"
        else
            echo -e "  LLM:      ${YELLOW}○ not connected${NC}  (start LM Studio, then register)"
        fi
    fi
    echo ""
}

_start() {
    echo ""
    echo -e "${CYAN}═══ Starting Istara ═══${NC}"
    echo ""

    # --- Backend ---
    if _is_running "$BACKEND_PID_FILE"; then
        echo -e "  Backend:  ${YELLOW}already running${NC} (PID $(cat "$BACKEND_PID_FILE"))"
    else
        local PYTHON; PYTHON=$(_find_python)
        if [ ! -x "$ROOT/venv/bin/python" ] && [ ! -x "$ROOT/venv/bin/python3" ]; then
            echo -e "\r  Backend:  ${RED}✗ venv not found${NC}  — run the installer first"
            echo -e "           ${YELLOW}curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash${NC}"
            return 1
        fi
        echo -n "  Backend:  starting..."
        cd "$ROOT/backend"
        nohup "$PYTHON" -m uvicorn app.main:app \
            --host 0.0.0.0 \
            --port $BACKEND_PORT \
            --log-level info \
            > "$BACKEND_LOG" 2>&1 &
        local bpid=$!
        echo "$bpid" > "$BACKEND_PID_FILE"
        cd "$ROOT"

        # Quick check — did it die immediately?
        sleep 0.5
        if ! kill -0 "$bpid" 2>/dev/null; then
            echo -e "\r  Backend:  ${RED}✗ crashed on startup${NC}"
            echo ""
            echo -e "  ${YELLOW}Error from $BACKEND_LOG:${NC}"
            tail -15 "$BACKEND_LOG" 2>/dev/null | sed 's/^/    /'
            echo ""
            rm -f "$BACKEND_PID_FILE"
            return 1
        fi

        # Wait for backend to be ready (up to 15s)
        local attempts=0
        while [ $attempts -lt 30 ]; do
            if curl -s --connect-timeout 1 "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
                echo -e "\r  Backend:  ${GREEN}● started${NC}  (PID $bpid)  http://localhost:$BACKEND_PORT"
                break
            fi
            sleep 0.5
            attempts=$((attempts + 1))
        done
        if [ $attempts -ge 30 ]; then
            # Check if process actually died
            if ! kill -0 "$bpid" 2>/dev/null; then
                echo -e "\r  Backend:  ${RED}✗ failed to start${NC}"
                echo ""
                echo -e "  ${YELLOW}Last lines from $BACKEND_LOG:${NC}"
                tail -10 "$BACKEND_LOG" 2>/dev/null | sed 's/^/    /'
                echo ""
                rm -f "$BACKEND_PID_FILE"
                return 1
            fi
            echo -e "\r  Backend:  ${YELLOW}⏳ starting slowly${NC} (PID $bpid) — check $BACKEND_LOG"
        fi
    fi

    # --- Frontend ---
    if _is_running "$FRONTEND_PID_FILE"; then
        echo -e "  Frontend: ${YELLOW}already running${NC} (PID $(cat "$FRONTEND_PID_FILE"))"
    else
        local NPM; NPM=$(_find_npm)
        echo -n "  Frontend: starting..."
        cd "$ROOT/frontend"
        # Use production server if built, otherwise fall back to dev
        if [ -d ".next" ]; then
            nohup "$NPM" start -- --port $FRONTEND_PORT \
                > "$FRONTEND_LOG" 2>&1 &
        else
            nohup "$NPM" run dev -- --port $FRONTEND_PORT \
                > "$FRONTEND_LOG" 2>&1 &
        fi
        local fpid=$!
        echo "$fpid" > "$FRONTEND_PID_FILE"
        cd "$ROOT"

        # Quick check — did it die immediately?
        sleep 0.5
        if ! kill -0 "$fpid" 2>/dev/null; then
            echo -e "\r  Frontend: ${RED}✗ crashed on startup${NC}"
            echo ""
            echo -e "  ${YELLOW}Error from $FRONTEND_LOG:${NC}"
            tail -15 "$FRONTEND_LOG" 2>/dev/null | sed 's/^/    /'
            echo ""
            rm -f "$FRONTEND_PID_FILE"
            return 1
        fi

        # Wait for frontend to be ready (up to 20s)
        local attempts=0
        while [ $attempts -lt 40 ]; do
            if curl -s --connect-timeout 1 "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
                echo -e "\r  Frontend: ${GREEN}● started${NC}  (PID $fpid)  http://localhost:$FRONTEND_PORT"
                break
            fi
            sleep 0.5
            attempts=$((attempts + 1))
        done
        if [ $attempts -ge 40 ]; then
            # Check if process actually died
            if ! kill -0 "$fpid" 2>/dev/null; then
                echo -e "\r  Frontend: ${RED}✗ failed to start${NC}"
                echo ""
                echo -e "  ${YELLOW}Last lines from $FRONTEND_LOG:${NC}"
                tail -10 "$FRONTEND_LOG" 2>/dev/null | sed 's/^/    /'
                echo ""
                rm -f "$FRONTEND_PID_FILE"
                return 1
            fi
            echo -e "\r  Frontend: ${YELLOW}⏳ starting slowly${NC} (PID $fpid) — check $FRONTEND_LOG"
        fi
    fi

    echo ""
    echo -e "  ${GREEN}Istara is up.${NC} Open ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
    echo ""
}

_stop() {
    echo ""
    echo -e "${CYAN}═══ Stopping Istara ═══${NC}"
    echo ""

    # --- Frontend first (less critical) ---
    if _is_running "$FRONTEND_PID_FILE"; then
        local fpid=$(cat "$FRONTEND_PID_FILE")
        # Kill the process group (npm spawns child processes)
        kill -- -"$fpid" 2>/dev/null || kill "$fpid" 2>/dev/null || true
        # Also kill any next-server on the port
        lsof -ti:$FRONTEND_PORT 2>/dev/null | xargs kill 2>/dev/null || true
        rm -f "$FRONTEND_PID_FILE"
        echo -e "  Frontend: ${RED}○ stopped${NC}"
    else
        echo -e "  Frontend: ${YELLOW}not running${NC}"
    fi

    # --- Backend ---
    if _is_running "$BACKEND_PID_FILE"; then
        local bpid=$(cat "$BACKEND_PID_FILE")
        kill "$bpid" 2>/dev/null || true
        # Also kill any uvicorn on the port
        lsof -ti:$BACKEND_PORT 2>/dev/null | xargs kill 2>/dev/null || true
        rm -f "$BACKEND_PID_FILE"
        echo -e "  Backend:  ${RED}○ stopped${NC}"
    else
        echo -e "  Backend:  ${YELLOW}not running${NC}"
    fi

    echo ""
}

_toggle() {
    # If either is running, stop both. Otherwise start both.
    if _is_running "$BACKEND_PID_FILE" || _is_running "$FRONTEND_PID_FILE"; then
        _stop
    else
        _start
    fi
}

_logs() {
    echo -e "${CYAN}═══ Istara Logs (Ctrl+C to exit) ═══${NC}"
    echo ""
    tail -f "$BACKEND_LOG" "$FRONTEND_LOG" 2>/dev/null || echo "No log files found. Start Istara first."
}

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

case "${1:-toggle}" in
    start)   _start ;;
    stop)    _stop ;;
    restart) _stop; sleep 1; _start ;;
    status)  _status ;;
    logs)    _logs ;;
    toggle)  _toggle ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo "       $0          (toggle: start if stopped, stop if running)"
        exit 1
        ;;
esac
