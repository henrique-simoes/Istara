#!/usr/bin/env bash
set -euo pipefail

echo "🐾 Istara Installer"
echo "==================="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found."
    echo ""
    echo "Please install Docker first:"
    echo "  macOS/Windows: https://docs.docker.com/desktop/"
    echo "  Linux: https://docs.docker.com/engine/install/"
    echo ""
    exit 1
fi

echo "✅ Docker found: $(docker --version)"

# Check Docker is running
if ! docker info &> /dev/null 2>&1; then
    echo "❌ Docker daemon is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check for docker compose
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Docker Compose not found."
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker Compose found"
echo ""

# Clone or update repo
INSTALL_DIR="${ISTARA_DIR:-$HOME/istara}"
REPO="henrique-simoes/Istara"

get_latest_release_version() {
    local version=""
    version=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
        | sed -n 's/.*"tag_name":[[:space:]]*"v\{0,1\}\([^"]*\)".*/\1/p' | head -1 || true)
    if [ -z "$version" ]; then
        version=$(git ls-remote --tags --refs --sort="v:refname" "https://github.com/${REPO}.git" "v*" 2>/dev/null \
            | tail -1 | sed 's#.*refs/tags/v##')
    fi
    echo "$version"
}

TARGET_VERSION="$(get_latest_release_version)"
if [ -z "$TARGET_VERSION" ]; then
    echo "❌ Could not determine the latest published Istara release."
    exit 1
fi

echo "📦 Latest published release: v$TARGET_VERSION"

if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Found existing installation at $INSTALL_DIR"
    echo "   Syncing to latest published release..."
    cd "$INSTALL_DIR"
    git fetch --tags origin
    git checkout -- . 2>/dev/null || true
    git clean -fd 2>/dev/null || true
else
    echo "📥 Cloning Istara to $INSTALL_DIR..."
    git clone "https://github.com/${REPO}.git" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

git fetch --tags origin
git checkout -B "release-$TARGET_VERSION" "tags/v$TARGET_VERSION" >/dev/null 2>&1 || {
    echo "❌ Could not check out release v$TARGET_VERSION"
    exit 1
}

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
fi

# Create required directories
echo "📁 Creating data directories..."
mkdir -p data/watch data/uploads data/projects data/lance_db

echo ""
echo "🚀 Starting Istara..."
echo ""

$COMPOSE_CMD up -d --build

echo ""
echo "✅ Istara is starting up!"
echo ""
echo "🌐 Open http://localhost:3000 in your browser"
echo ""
echo "First run may take a few minutes while models are downloaded."
echo ""
echo "Useful commands:"
echo "  $COMPOSE_CMD logs -f          # View logs"
echo "  $COMPOSE_CMD down             # Stop Istara"
echo "  $COMPOSE_CMD up -d            # Start Istara"
echo "  $COMPOSE_CMD pull && $COMPOSE_CMD up -d --build  # Update"
echo ""
echo "🐾 Happy researching!"
