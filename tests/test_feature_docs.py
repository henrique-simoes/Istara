from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DOCS = ROOT / "docs/features"
SITE_ROOT = FEATURE_DOCS / "site"


def test_feature_docs_generator_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/feature_docs.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "feature docs check passed" in result.stdout


def test_feature_docs_manifest_matches_inventory() -> None:
    inventory = json.loads((FEATURE_DOCS / "inventory.json").read_text(encoding="utf-8"))
    manifest = json.loads((SITE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    inventory_ids = {feature["id"] for feature in inventory["features"]}
    manifest_ids = {feature["id"] for feature in manifest["features"]}

    assert manifest_ids == inventory_ids
    assert len(inventory_ids) >= 80


def test_feature_docs_generated_site_has_all_pages_and_indexes() -> None:
    inventory = json.loads((FEATURE_DOCS / "inventory.json").read_text(encoding="utf-8"))
    features = inventory["features"]
    glossary_terms = list((FEATURE_DOCS / "glossary").glob("*.md"))
    html_pages = list(SITE_ROOT.rglob("*.html"))

    assert len(html_pages) == len(features) * 2 + len(glossary_terms) + 2
    assert (SITE_ROOT / "assets/site.css").exists()
    assert (SITE_ROOT / "assets/site.js").exists()
    assert (SITE_ROOT / "assets/istara-logo.png").exists()
    assert (SITE_ROOT / ".nojekyll").exists()
    assert (SITE_ROOT / "search-index.json").exists()
    assert (SITE_ROOT / "glossary/index.html").exists()

    for feature in features:
        base = SITE_ROOT / "features" / feature["id"].replace(".", "/")
        assert (base / "researcher.html").exists()
        assert (base / "architecture.html").exists()


def test_feature_docs_source_markdown_links_resolve() -> None:
    for source in (FEATURE_DOCS / "content").rglob("*.md"):
        text = source.read_text(encoding="utf-8")
        for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)", text):
            target_path = raw_target.split("#", 1)[0]
            resolved = (source.parent / target_path).resolve()
            assert resolved.exists(), f"{source.relative_to(ROOT)} has broken markdown link {raw_target}"


def test_feature_docs_site_shell_has_accessible_landmarks_and_theme_support() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
    feature = (SITE_ROOT / "features/chat/overview/researcher.html").read_text(encoding="utf-8")
    css = (SITE_ROOT / "assets/site.css").read_text(encoding="utf-8")

    for html in (index, feature):
        assert '<a class="skip-link" href="#main">' in html
        assert 'role="banner"' in html
        assert 'role="search"' in html
        assert 'aria-label="Feature documentation navigation"' in html
        assert '<main id="main"' in html
        assert 'for="doc-search">Search documentation</label>' in html
        assert 'data-theme-toggle' in html

    assert 'id="install"' in index
    assert "brew install --cask henrique-simoes/istara/istara" in index
    assert "scripts/install-istara.sh | bash" in index
    assert 'data-copy-command' in index
    assert "brand-logo" in index
    assert "navigator.clipboard.writeText" in (SITE_ROOT / "assets/site.js").read_text(encoding="utf-8")
    assert 'aria-current="page"' in feature
    assert ':focus-visible' in css
    assert 'prefers-color-scheme: dark' in css
    assert ':root[data-theme="dark"]' in css
    assert ".home-page .doc-panel" in css
    assert "istara-logo.png" in css


def test_feature_docs_github_pages_workflow_builds_and_deploys_site() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "python scripts/feature_docs.py --seed-missing --generate-site --check" in workflow
    assert "pytest tests/test_feature_docs.py -q" in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "actions/upload-pages-artifact@v4" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "path: docs/features/site" in workflow
