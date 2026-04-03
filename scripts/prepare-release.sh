#!/usr/bin/env bash
# Prepare an Istara release locally by syncing docs/integrity and bumping version.
#
# Usage:
#   ./scripts/prepare-release.sh --bump
#   ./scripts/prepare-release.sh 2026.04.03
#
# This script does not commit, tag, or push automatically. It standardizes the
# local release-preparation sequence so versioning, generated docs, and integrity
# checks stay aligned.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARG="${1:---bump}"

cd "$ROOT"

echo "==> Regenerating living docs"
python scripts/update_agent_md.py

echo "==> Checking integrity"
python scripts/check_integrity.py

echo "==> Updating version"
chmod +x scripts/set-version.sh
./scripts/set-version.sh "$ARG"

echo "==> Re-running integrity after version update"
python scripts/update_agent_md.py
python scripts/check_integrity.py

VERSION="$(cat VERSION | tr -d '[:space:]')"

echo ""
echo "Release prepared for version: $VERSION"
echo ""
echo "Recommended next steps:"
echo "  1. Review git diff and run any additional verification needed"
echo "  2. Commit: git commit -am 'release: $VERSION'"
echo "  3. Tag:    git tag v$VERSION"
echo "  4. Push:   git push origin <branch> && git push origin v$VERSION"
echo ""
echo "GitHub Release + installer publishing happen from the tag/workflow release flow."
