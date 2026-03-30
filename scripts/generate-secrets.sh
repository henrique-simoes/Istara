#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# Istara Secret Generator
# Generates ALL security keys needed for a production deployment
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

OUTPUT="${1:-.env.secrets}"
echo "Generating secure secrets..."

JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=')
DATA_ENCRYPTION_KEY=$(openssl rand -base64 32)
NETWORK_ACCESS_TOKEN=$(openssl rand -base64 32 | tr -d '/+=')
RELAY_TOKEN=$(openssl rand -base64 24 | tr -d '/+=')

cat > "$OUTPUT" <<EOF
# ═══════════════════════════════════════════════════════════════════
# Istara Secrets — Auto-generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
# DO NOT commit this file. Copy values to your .env
# ═══════════════════════════════════════════════════════════════════

# JWT authentication (required)
JWT_SECRET=$JWT_SECRET

# Data encryption key for sensitive data at rest (required)
DATA_ENCRYPTION_KEY=$DATA_ENCRYPTION_KEY

# Network access token for non-localhost connections (required for team/relay)
NETWORK_ACCESS_TOKEN=$NETWORK_ACCESS_TOKEN

# Relay authentication token (for compute donation nodes)
RELAY_TOKEN=$RELAY_TOKEN

# PostgreSQL password (team mode only)
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
EOF

chmod 600 "$OUTPUT"
echo ""
echo "✅ Secrets written to $OUTPUT (chmod 600)"
echo ""
echo "Generated keys:"
echo "  JWT_SECRET          = ${JWT_SECRET:0:8}..."
echo "  DATA_ENCRYPTION_KEY = ${DATA_ENCRYPTION_KEY:0:8}..."
echo "  NETWORK_ACCESS_TOKEN= ${NETWORK_ACCESS_TOKEN:0:8}..."
echo "  RELAY_TOKEN         = ${RELAY_TOKEN:0:8}..."
echo "  POSTGRES_PASSWORD   = ${POSTGRES_PASSWORD:0:8}..."
echo ""
echo "Copy values to your .env or run: source $OUTPUT"
