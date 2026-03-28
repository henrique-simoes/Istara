#!/usr/bin/env bash
set -euo pipefail

OUTPUT="${1:-.env.secrets}"
echo "Generating secure secrets..."

JWT_SECRET=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=')

cat > "$OUTPUT" <<EOF
# Auto-generated secrets — do NOT commit this file
# Source this file or copy values to your .env
JWT_SECRET=$JWT_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
EOF

chmod 600 "$OUTPUT"
echo "Secrets written to $OUTPUT (chmod 600)"
echo "Copy values to your .env or run: source $OUTPUT"
