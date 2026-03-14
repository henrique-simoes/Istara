#!/usr/bin/env bash
set -euo pipefail

echo "🐾 ReClaw Installer"
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
INSTALL_DIR="${RECLAW_DIR:-$HOME/reclaw}"

if [ -d "$INSTALL_DIR" ]; then
    echo "📁 Found existing installation at $INSTALL_DIR"
    echo "   Pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || echo "   ⚠️  Could not pull (local changes?). Continuing with current version."
else
    echo "📥 Cloning ReClaw to $INSTALL_DIR..."
    git clone https://github.com/your-org/reclaw.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
fi

echo ""
echo "🚀 Starting ReClaw..."
echo ""

$COMPOSE_CMD up -d --build

echo ""
echo "✅ ReClaw is starting up!"
echo ""
echo "🌐 Open http://localhost:3000 in your browser"
echo ""
echo "First run may take a few minutes while models are downloaded."
echo ""
echo "Useful commands:"
echo "  $COMPOSE_CMD logs -f          # View logs"
echo "  $COMPOSE_CMD down             # Stop ReClaw"
echo "  $COMPOSE_CMD up -d            # Start ReClaw"
echo "  $COMPOSE_CMD pull && $COMPOSE_CMD up -d --build  # Update"
echo ""
echo "🐾 Happy researching!"
