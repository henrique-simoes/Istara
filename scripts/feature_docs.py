#!/usr/bin/env python3
"""Validate and build Istara's living feature documentation site."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import os
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from feature_docs_assets import site_css, site_js
from feature_docs_home import copy_home_screenshots, home_marketing_sections
from feature_docs_tech import TECH_PAGES


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs" / "features"
CONTENT_ROOT = DOCS_ROOT / "content"
GLOSSARY_ROOT = DOCS_ROOT / "glossary"
SITE_ROOT = DOCS_ROOT / "site"
INVENTORY_PATH = DOCS_ROOT / "inventory.json"
DESIGN_SOURCE = DOCS_ROOT / "site-design.md"
LOGO_SOURCE = DOCS_ROOT / "assets" / "istara-logo.png"
FALLBACK_LOGO_SOURCE = ROOT / "Istara.png"

AUDIENCES = ("researcher", "architecture")
REQUIRED_FRONTMATTER = {
    "stable_id",
    "title",
    "ui_path",
    "audience",
    "status",
    "related_features",
    "related_glossary",
    "code_references",
    "api_references",
    "test_references",
    "last_verified",
    "compass",
}


def load_inventory() -> dict[str, Any]:
    if not INVENTORY_PATH.exists():
        raise SystemExit(f"Missing inventory: {INVENTORY_PATH}")
    with INVENTORY_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data.get("features"), list):
        raise SystemExit("inventory.json must contain a features list")
    return data


def feature_dir(feature_id: str) -> Path:
    return CONTENT_ROOT / feature_id.replace(".", "/")


def doc_path(feature_id: str, audience: str) -> Path:
    return feature_dir(feature_id) / f"{audience}.md"


def today() -> str:
    return dt.date.today().isoformat()


def as_frontmatter_value(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return str(value)


def frontmatter_for(feature: dict[str, Any], audience: str) -> str:
    metadata = {
        "stable_id": feature["id"],
        "title": feature["title"],
        "ui_path": " > ".join(feature.get("ui_path", [])),
        "audience": audience,
        "status": feature.get("status", "documented"),
        "related_features": feature.get("related_features", []),
        "related_glossary": feature.get("glossary_terms", []),
        "code_references": feature.get("code_refs", []),
        "api_references": feature.get("api_refs", []),
        "test_references": feature.get("test_refs", []),
        "last_verified": feature.get("last_verified") or today(),
        "compass": feature.get("compass", "CF-SPEC-53 / CF-657"),
    }
    lines = ["---"]
    lines.extend(
        f"{key}: {as_frontmatter_value(value)}" for key, value in metadata.items()
    )
    lines.append("---")
    return "\n".join(lines)


def related_links(feature: dict[str, Any], audience: str) -> list[str]:
    links = []
    for related_id in feature.get("related_features", []):
        target = relative_doc_link(feature["id"], related_id, audience)
        links.append(f"- [{related_id}]({target})")
    return links or ["- None recorded."]


def glossary_links(feature: dict[str, Any]) -> list[str]:
    links = []
    prefix = "../" * (len(feature["id"].split(".")) + 1)
    for term_id in feature.get("glossary_terms", []):
        links.append(f"- [{term_id}]({prefix}glossary/{term_id}.md)")
    return links or ["- None recorded."]


def relative_doc_link(source_id: str, target_id: str, audience: str) -> str:
    source_depth = len(source_id.split("."))
    prefix = "../" * source_depth
    return f"{prefix}{target_id.replace('.', '/')}/{audience}.md"


def default_user_flows(feature: dict[str, Any]) -> list[str]:
    path = " > ".join(feature.get("ui_path", [])) or feature["title"]
    return [
        f"Open {path} from the Istara navigation or the parent tab.",
        f"Use the visible controls in this surface to work with {feature['title'].lower()} in the active project context.",
        "Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.",
    ]


def default_why(feature: dict[str, Any]) -> str:
    path = " > ".join(feature.get("ui_path", [])) or feature["title"]
    return f"{feature['title']} exists so the work represented by {path} has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools."


def default_workflows(feature: dict[str, Any]) -> list[str]:
    workflows = [
        f"Start from {(' > '.join(feature.get('ui_path', [])) or feature['title'])} when the current research task needs {feature['title'].lower()}.",
        "Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.",
    ]
    related = feature.get("related_features", [])
    if related:
        workflows.append(f"Move to related surfaces when needed: {', '.join(related)}.")
    return workflows


def default_outputs(feature: dict[str, Any]) -> list[str]:
    return [
        f"Project-scoped state or artifact updates associated with {feature['title'].lower()}.",
        "Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.",
    ]


def default_ai_architecture(feature: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    glossary_terms = set(feature.get("glossary_terms", []))
    if "mcp" in glossary_terms:
        notes.append(
            "MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component."
        )
    if "rag" in glossary_terms:
        notes.append(
            "RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes."
        )
    if "a2a" in glossary_terms:
        notes.append(
            "Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions."
        )
    if "webauthn" in glossary_terms or "totp" in glossary_terms:
        notes.append(
            "Authentication-factor behavior is security-sensitive and must be verified with the repository security benchmark when implementation changes."
        )
    if not notes:
        notes.append(
            "No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files."
        )
    return notes


def default_caveats(feature: dict[str, Any]) -> list[str]:
    return [
        "Needs interactive verification for exact empty, loading, error, and permission-denied states.",
        "Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.",
    ]


def default_architecture_notes(feature: dict[str, Any]) -> list[str]:
    refs = feature.get("code_refs", [])
    primary = refs[0] if refs else feature.get("component", "the referenced component")
    return [
        f"The feature is mounted through `{primary}` and the UI navigation path recorded in the inventory.",
        "The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.",
        "When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.",
    ]


def render_researcher_doc(feature: dict[str, Any]) -> str:
    flows = "\n".join(
        f"- {item}" for item in feature.get("user_flows") or default_user_flows(feature)
    )
    outputs = "\n".join(
        f"- {item}" for item in feature.get("outputs") or default_outputs(feature)
    )
    caveats = "\n".join(
        f"- {item}" for item in feature.get("caveats") or default_caveats(feature)
    )
    related = "\n".join(related_links(feature, "researcher"))
    glossary = "\n".join(glossary_links(feature))
    return f"""{frontmatter_for(feature, "researcher")}

# {feature["title"]}

## What It Does

{feature.get("summary", "").strip()}

## Why It Exists

{feature.get("why", default_why(feature)).strip()}

## Where It Lives

- UI path: {" > ".join(feature.get("ui_path", []))}
- Navigation group: {feature.get("nav_group", "unknown")}
- Primary component: `{feature.get("component", "needs verification")}`

## How UX Researchers Use It

{flows or "- Needs verification from interactive walkthrough."}

## Supported Workflows

{chr(10).join(f"- {item}" for item in feature.get("workflows") or default_workflows(feature))}

## Inputs, Outputs, And Expected Outcomes

{outputs or "- Needs verification from code and product walkthrough."}

## Caveats

{caveats or "- No caveats recorded yet."}

## Related Features

{related}

## Related Concepts

{glossary}

## Evidence

- Source files: {", ".join(f"`{path}`" for path in feature.get("code_refs", [])) or "needs verification"}
- API references: {", ".join(f"`{path}`" for path in feature.get("api_refs", [])) or "none recorded"}
- Tests: {", ".join(f"`{path}`" for path in feature.get("test_refs", [])) or "none recorded"}
"""


def render_architecture_doc(feature: dict[str, Any]) -> str:
    notes = "\n".join(
        f"- {item}"
        for item in feature.get("architecture_notes")
        or default_architecture_notes(feature)
    )
    related = "\n".join(related_links(feature, "architecture"))
    glossary = "\n".join(glossary_links(feature))
    code_refs = "\n".join(f"- `{path}`" for path in feature.get("code_refs", []))
    api_refs = "\n".join(f"- `{path}`" for path in feature.get("api_refs", []))
    store_refs = "\n".join(f"- `{path}`" for path in feature.get("store_refs", []))
    test_refs = "\n".join(f"- `{path}`" for path in feature.get("test_refs", []))
    ai_notes = "\n".join(
        f"- {item}"
        for item in feature.get("ai_architecture") or default_ai_architecture(feature)
    )
    return f"""{frontmatter_for(feature, "architecture")}

# {feature["title"]} Architecture

## Implementation Summary

{feature.get("engineering_summary", feature.get("summary", "")).strip()}

## Frontend Surface

{code_refs or "- Needs verification."}

## State, API, And Backend Contracts

### Stores

{store_refs or "- None recorded."}

### API And Backend

{api_refs or "- None recorded."}

## Architecture Notes

{notes or "- Needs verification from implementation pass."}

## Agents, Skills, LLM, MCP, And Permissions

{ai_notes}

## Tests And Verification

{test_refs or "- No focused test reference recorded yet."}

## Related Features

{related}

## Related Concepts

{glossary}

## Compass Evidence

- Spec/task: {feature.get("compass", "CF-SPEC-53 / CF-657")}
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
"""


def seed_missing_docs(
    features: list[dict[str, Any]], overwrite: bool = False
) -> list[Path]:
    written: list[Path] = []
    for feature in features:
        for audience, renderer in (
            ("researcher", render_researcher_doc),
            ("architecture", render_architecture_doc),
        ):
            path = doc_path(feature["id"], audience)
            if path.exists() and not overwrite:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(renderer(feature).rstrip() + "\n", encoding="utf-8")
            written.append(path)
    return written


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data, body


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def feature_site_path(feature_id: str, audience: str) -> Path:
    return SITE_ROOT / "features" / feature_id.replace(".", "/") / f"{audience}.html"


def glossary_site_path(term_id: str) -> Path:
    return SITE_ROOT / "glossary" / f"{term_id}.html"


def relative_url(from_file: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file, start=from_file.parent)).as_posix()


def markdown_to_html(
    markdown: str,
    source_path: Path | None = None,
    output_path: Path | None = None,
    *,
    skip_first_h1: bool = False,
) -> str:
    _, body = parse_frontmatter(markdown)
    lines = body.splitlines()
    html_lines: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []
    skipped_h1 = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for line in lines:
        if line.startswith("```"):
            if in_code:
                html_lines.append(
                    "<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>"
                )
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            close_list()
            continue
        if line.startswith("# "):
            close_list()
            title = line[2:].strip()
            if skip_first_h1 and not skipped_h1:
                skipped_h1 = True
                continue
            html_lines.append(
                f'<h1 id="{slugify(title)}">{inline_markdown(title, source_path, output_path)}</h1>'
            )
        elif line.startswith("## "):
            close_list()
            title = line[3:].strip()
            html_lines.append(
                f'<h2 id="{slugify(title)}">{inline_markdown(title, source_path, output_path)}</h2>'
            )
        elif line.startswith("### "):
            close_list()
            title = line[4:].strip()
            html_lines.append(
                f'<h3 id="{slugify(title)}">{inline_markdown(title, source_path, output_path)}</h3>'
            )
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(
                f"<li>{inline_markdown(line[2:].strip(), source_path, output_path)}</li>"
            )
        else:
            close_list()
            html_lines.append(
                f"<p>{inline_markdown(line.strip(), source_path, output_path)}</p>"
            )
    close_list()
    if in_code:
        html_lines.append(
            "<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>"
        )
    return "\n".join(html_lines)


def resolve_markdown_href(
    target: str, source_path: Path | None, output_path: Path | None
) -> str:
    if not source_path or not output_path:
        return target.replace(".md", ".html").replace("../", "")
    if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
        return target

    path_part, fragment_sep, fragment = target.partition("#")
    path_part, query_sep, query = path_part.partition("?")
    if not path_part:
        return f"#{fragment}" if fragment_sep else target

    source_target = Path(path_part)
    if source_target.suffix != ".md":
        resolved_static = (source_path.parent / source_target).resolve()
        if resolved_static.exists():
            return relative_url(output_path, resolved_static)
        return target

    site_target: Path | None = None
    if "glossary" in source_target.parts:
        site_target = glossary_site_path(source_target.stem)
    else:
        resolved = (source_path.parent / source_target).resolve()
        try:
            rel_content = resolved.relative_to(CONTENT_ROOT.resolve())
            site_target = SITE_ROOT / "features" / rel_content.with_suffix(".html")
        except ValueError:
            try:
                rel_glossary = resolved.relative_to(GLOSSARY_ROOT.resolve())
                site_target = SITE_ROOT / "glossary" / rel_glossary.with_suffix(".html")
            except ValueError:
                site_target = None

    if site_target is None:
        return target.replace(".md", ".html")

    suffix = ""
    if query_sep:
        suffix += f"?{query}"
    if fragment_sep:
        suffix += f"#{fragment}"
    return relative_url(output_path, site_target) + suffix


def inline_markdown(
    text: str, source_path: Path | None = None, output_path: Path | None = None
) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        target = html.unescape(match.group(2))
        href = resolve_markdown_href(target, source_path, output_path)
        return f'<a href="{html.escape(href)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped)


def extract_headings(
    markdown: str, *, skip_first_h1: bool = False
) -> list[tuple[int, str, str]]:
    _, body = parse_frontmatter(markdown)
    headings: list[tuple[int, str, str]] = []
    skipped_h1 = False
    for line in body.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if skip_first_h1 and level == 1 and not skipped_h1:
            skipped_h1 = True
            continue
        headings.append((level, title, slugify(title)))
    return headings


def build_toc(headings: list[tuple[int, str, str]]) -> str:
    items = [item for item in headings if item[0] in (2, 3)]
    if not items:
        return '<p class="toc-empty">No page sections recorded.</p>'
    parts = ['<nav aria-label="On this page"><ul>']
    for level, title, slug in items:
        parts.append(
            f'<li class="toc-level-{level}"><a href="#{html.escape(slug)}">{html.escape(title)}</a></li>'
        )
    parts.append("</ul></nav>")
    return "\n".join(parts)


def page_shell(
    title: str,
    nav: str,
    content: str,
    *,
    current_path: Path,
    subtitle: str = "Living feature documentation",
    toc: str = "",
    body_class: str = "",
) -> str:
    css_href = relative_url(current_path, SITE_ROOT / "assets" / "site.css")
    js_href = relative_url(current_path, SITE_ROOT / "assets" / "site.js")
    logo_href = relative_url(current_path, SITE_ROOT / "assets" / "istara-logo.png")
    index_href = relative_url(current_path, SITE_ROOT / "index.html")
    docs_href = relative_url(current_path, SITE_ROOT / "docs.html")
    manifest_href = relative_url(current_path, SITE_ROOT / "manifest.json")
    llms_href = relative_url(current_path, SITE_ROOT / "llms.txt")
    content = content.strip()
    toc = toc.strip()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - Istara Feature Docs</title>
  <meta name="description" content="Istara documentation, installation, and feature map for local-first AI UX research.">
  <link rel="stylesheet" href="{html.escape(css_href)}">
</head>
<body class="{html.escape(body_class)}">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="topbar" role="banner">
    <a class="brand" href="{html.escape(index_href)}" aria-label="Istara feature documentation home">
      <img class="brand-logo" src="{html.escape(logo_href)}" alt="" aria-hidden="true">
      <span><strong>Istara Docs</strong><small>{html.escape(subtitle)}</small></span>
    </a>
    <button class="menu-button" type="button" data-nav-toggle aria-expanded="false" aria-controls="docs-sidebar">Menu</button>
    <form class="search-form" role="search">
      <label class="visually-hidden" for="doc-search">Search documentation</label>
      <input id="doc-search" name="q" type="search" autocomplete="off" placeholder="Search docs">
    </form>
    <nav class="utility-nav" aria-label="Machine-readable documentation">
      <a href="{html.escape(docs_href)}">Docs Hub</a>
      <a href="{html.escape(index_href)}#install">Install</a>
      <a href="https://github.com/henrique-simoes/Istara">GitHub</a>
      <a href="{html.escape(manifest_href)}">Manifest</a>
      <a href="{html.escape(llms_href)}">llms.txt</a>
      <button type="button" data-theme-toggle>Theme: system</button>
    </nav>
  </header>
  <div class="layout-shell">
    <aside id="docs-sidebar" class="sidebar" aria-label="Feature documentation navigation">
      <div class="sidebar-heading">
        <strong>Feature Map</strong>
        <span>UI organized</span>
      </div>
      {nav}
    </aside>
    <main id="main" class="content" tabindex="-1">
      <div class="content-grid">
        <article class="doc-panel">
          {content}
        </article>
        <aside class="toc-panel" aria-label="Page sections">
          <h2>On This Page</h2>
          {toc}
        </aside>
      </div>
    </main>
  </div>
  <script src="{html.escape(js_href)}" defer></script>
</body>
</html>
"""


def build_nav(
    features: list[dict[str, Any]],
    current_path: Path,
    *,
    current_feature_id: str | None = None,
    audience: str = "researcher",
) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        groups.setdefault(feature.get("nav_group", "Other"), []).append(feature)
    parts = ['<nav class="nav-tree" aria-label="Istara UI feature map">']
    for group, items in groups.items():
        parts.append('<section class="nav-section" data-nav-section>')
        parts.append(f"<h2>{html.escape(group)}</h2>")
        parts.append("<ul>")
        for feature in sorted(items, key=lambda item: item.get("order", 0)):
            href = relative_url(
                current_path, feature_site_path(feature["id"], audience)
            )
            ui_path = " > ".join(feature.get("ui_path", []))
            active = feature["id"] == current_feature_id
            aria = ' aria-current="page"' if active else ""
            css_class = ' class="active"' if active else ""
            search_text = f"{feature['title']} {ui_path} {feature.get('summary', '')}"
            parts.append(
                f'<li data-search-item data-search-text="{html.escape(search_text.lower())}">'
                f'<a{css_class}{aria} href="{html.escape(href)}">'
                f"<span>{html.escape(feature['title'])}</span>"
                f"<small>{html.escape(ui_path)}</small>"
                "</a></li>"
            )
        parts.append("</ul>")
        parts.append("</section>")
    parts.append("</nav>")
    return "\n".join(parts)


def audience_label(audience: str) -> str:
    return "Researcher/User" if audience == "researcher" else "Engineering/AI"


def feature_page_header(
    feature: dict[str, Any],
    features_by_id: dict[str, dict[str, Any]],
    audience: str,
    current_path: Path,
) -> str:
    ui_path = " > ".join(feature.get("ui_path", []))
    status = feature.get("status", "documented")
    researcher_href = relative_url(
        current_path, feature_site_path(feature["id"], "researcher")
    )
    architecture_href = relative_url(
        current_path, feature_site_path(feature["id"], "architecture")
    )
    related_links_html = []
    for related_id in feature.get("related_features", []):
        related = features_by_id.get(related_id, {"title": related_id})
        href = relative_url(current_path, feature_site_path(related_id, audience))
        related_links_html.append(
            f'<a href="{html.escape(href)}">{html.escape(related["title"])}</a>'
        )
    related = "\n".join(related_links_html) or "<span>None recorded</span>"
    glossary = ", ".join(feature.get("glossary_terms", [])) or "None recorded"
    researcher_current = ' aria-current="page"' if audience == "researcher" else ""
    architecture_current = ' aria-current="page"' if audience == "architecture" else ""
    return f"""
<header class="feature-hero">
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <a href="{html.escape(relative_url(current_path, SITE_ROOT / "docs.html"))}">Docs</a>
    <span>{html.escape(feature.get("nav_group", "Feature"))}</span>
    <span>{html.escape(feature["title"])}</span>
  </nav>
  <div class="feature-title-row">
    <div>
      <p class="eyebrow">{html.escape(audience_label(audience))} documentation</p>
      <h1>{html.escape(feature["title"])}</h1>
      <p class="lede">{html.escape(feature.get("summary", ""))}</p>
    </div>
    <span class="status-chip">{html.escape(status)}</span>
  </div>
  <nav class="audience-tabs" aria-label="Documentation audience">
    <a href="{html.escape(researcher_href)}"{researcher_current}>Researcher</a>
    <a href="{html.escape(architecture_href)}"{architecture_current}>Architecture</a>
  </nav>
  <dl class="meta-grid">
    <div><dt>UI Path</dt><dd>{html.escape(ui_path)}</dd></div>
    <div><dt>Component</dt><dd><code>{html.escape(feature.get("component", "needs verification"))}</code></dd></div>
    <div><dt>Source Refs</dt><dd>{len(feature.get("code_refs", []))}</dd></div>
    <div><dt>Tests</dt><dd>{len(feature.get("test_refs", []))}</dd></div>
  </dl>
  <div class="link-cluster" aria-label="Related feature links">{related}</div>
  <p class="concept-line"><strong>Concepts:</strong> {html.escape(glossary)}</p>
</header>
"""


def index_content(features: list[dict[str, Any]], current_path: Path) -> str:
    return home_marketing_sections()


def docs_content(features: list[dict[str, Any]], current_path: Path) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for feature in features:
        groups.setdefault(feature.get("nav_group", "Other"), []).append(feature)
    glossary_terms = sorted(path.stem for path in GLOSSARY_ROOT.glob("*.md"))
    metrics = f"""
<section id="metrics" class="metric-grid" aria-label="Documentation coverage">
  <article><strong>{len(features)}</strong><span>Tracked UI features</span></article>
  <article><strong>{len(features) * len(AUDIENCES)}</strong><span>Feature perspectives</span></article>
  <article><strong>{len(groups)}</strong><span>UI menu groups</span></article>
  <article><strong>{len(glossary_terms)}</strong><span>Shared concepts</span></article>
</section>
"""
    group_cards = []
    for group, items in groups.items():
        first = sorted(items, key=lambda item: item.get("order", 0))[:4]
        links = "\n".join(
            f'<li><a href="{html.escape(relative_url(current_path, feature_site_path(item["id"], "researcher")))}">'
            f"{html.escape(item['title'])}</a></li>"
            for item in first
        )
        search_text = f"{group} {' '.join(item['title'] for item in items)}"
        group_cards.append(
            f'<article class="group-card" data-feature-card data-search-text="{html.escape(search_text.lower())}">'
            f"<h2>{html.escape(group)}</h2><p>{len(items)} documented feature surfaces.</p><ul>{links}</ul></article>"
        )
    feature_cards = []
    for feature in sorted(features, key=lambda item: item.get("order", 0)):
        researcher = relative_url(
            current_path, feature_site_path(feature["id"], "researcher")
        )
        architecture = relative_url(
            current_path, feature_site_path(feature["id"], "architecture")
        )
        ui_path = " > ".join(feature.get("ui_path", []))
        search_text = f"{feature['title']} {ui_path} {feature.get('summary', '')} {feature.get('nav_group', '')}"
        feature_cards.append(
            f'<article class="feature-card" data-feature-card data-search-text="{html.escape(search_text.lower())}">'
            f'<div><p class="eyebrow">{html.escape(feature.get("nav_group", "Feature"))}</p>'
            f"<h2>{html.escape(feature['title'])}</h2><p>{html.escape(feature.get('summary', ''))}</p>"
            f'<p class="path-line">{html.escape(ui_path)}</p></div>'
            f'<div class="card-actions"><a href="{html.escape(researcher)}">Researcher</a>'
            f'<a href="{html.escape(architecture)}">Architecture</a></div></article>'
        )
    glossary_href = relative_url(current_path, SITE_ROOT / "glossary" / "index.html")
    manifest_href = relative_url(current_path, SITE_ROOT / "manifest.json")
    graph_href = relative_url(current_path, SITE_ROOT / "feature-graph.json")
    search_href = relative_url(current_path, SITE_ROOT / "search-index.json")
    sitemap_href = relative_url(current_path, SITE_ROOT / "sitemap.xml")
    llms_href = relative_url(current_path, SITE_ROOT / "llms.txt")
    return f"""
<header class="feature-hero">
  <p class="eyebrow">Istara Knowledge Base</p>
  <h1>Documentation Hub</h1>
  <p class="lede">Explore detailed researcher protocols and engineering architectures for all {len(features)}+ governed feature surfaces.</p>
</header>
{metrics}
<section id="feature-map" class="section-block">
  <div class="section-heading"><h2>Menu Structure</h2><p>Grouped the same way Istara exposes the documented surfaces.</p></div>
  <div class="group-grid">{"".join(group_cards)}</div>
</section>
<section id="all-features" class="section-block">
  <div class="section-heading"><h2>All Feature Pages</h2><p>Each feature has a researcher/user page and an engineering/AI architecture page.</p></div>
  <div class="feature-list">{"".join(feature_cards)}</div>
</section>
<section id="agent-entrypoints" class="section-block agent-block">
  <div class="section-heading"><h2>Agent Entrypoints</h2><p>Stable files for agents, validators, and static hosts.</p></div>
  <div class="resource-grid">
    <a href="{html.escape(manifest_href)}">Manifest JSON</a>
    <a href="{html.escape(graph_href)}">Feature Graph</a>
    <a href="{html.escape(search_href)}">Search Index</a>
    <a href="{html.escape(sitemap_href)}">Sitemap</a>
    <a href="{html.escape(llms_href)}">llms.txt</a>
  </div>
</section>
"""


def glossary_index_content(features: list[dict[str, Any]], current_path: Path) -> str:
    cards = []
    for source in sorted(GLOSSARY_ROOT.glob("*.md")):
        term_id = source.stem
        title = source.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        used_by = [
            feature
            for feature in features
            if term_id in feature.get("glossary_terms", [])
        ]
        href = relative_url(current_path, glossary_site_path(term_id))
        search_text = (
            f"{term_id} {title} {' '.join(feature['title'] for feature in used_by)}"
        )
        cards.append(
            f'<article class="glossary-card" data-glossary-card data-search-text="{html.escape(search_text.lower())}">'
            f'<h2><a href="{html.escape(href)}">{html.escape(title)}</a></h2>'
            f"<p>{len(used_by)} related feature pages.</p></article>"
        )
    return f"""
<header class="feature-hero">
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <a href="{html.escape(relative_url(current_path, SITE_ROOT / "docs.html"))}">Docs</a>
    <span>Glossary</span>
  </nav>
  <p class="eyebrow">Shared concepts</p>
  <h1>Glossary</h1>
  <p class="lede">Research, architecture, AI, and governance terms linked from Istara feature pages.</p>
</header>
<div class="glossary-grid">{"".join(cards)}</div>
"""


def glossary_page_content(
    source: Path, features: list[dict[str, Any]], current_path: Path
) -> tuple[str, str]:
    term_id = source.stem
    markdown = source.read_text(encoding="utf-8")
    title = markdown.splitlines()[0].lstrip("# ").strip()
    used_by = [
        feature for feature in features if term_id in feature.get("glossary_terms", [])
    ]
    links = (
        "\n".join(
            f'<a href="{html.escape(relative_url(current_path, feature_site_path(feature["id"], "researcher")))}">{html.escape(feature["title"])}</a>'
            for feature in used_by
        )
        or "<span>No related features recorded.</span>"
    )
    body = markdown_to_html(markdown, source, current_path, skip_first_h1=True)
    content = f"""
<header class="feature-hero">
  <nav class="breadcrumbs" aria-label="Breadcrumb">
    <a href="{html.escape(relative_url(current_path, SITE_ROOT / "docs.html"))}">Docs</a>
    <a href="{html.escape(relative_url(current_path, SITE_ROOT / "glossary" / "index.html"))}">Glossary</a>
    <span>{html.escape(title)}</span>
  </nav>
  <p class="eyebrow">Glossary term</p>
  <h1>{html.escape(title)}</h1>
</header>
{body}
<section class="related-panel">
  <h2>Related Features</h2>
  <div class="link-cluster">{links}</div>
</section>
"""
    return title, content


def generate_site(inventory: dict[str, Any]) -> list[Path]:
    features = inventory["features"]
    features_by_id = {feature["id"]: feature for feature in features}
    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
    SITE_ROOT.mkdir(parents=True, exist_ok=True)
    assets = SITE_ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "site.css").write_text(site_css(), encoding="utf-8")
    (assets / "site.js").write_text(site_js(), encoding="utf-8")
    written: list[Path] = [assets / "site.css", assets / "site.js"]
    logo_source = LOGO_SOURCE if LOGO_SOURCE.exists() else FALLBACK_LOGO_SOURCE
    if logo_source.exists():
        logo_target = assets / "istara-logo.png"
        shutil.copyfile(logo_source, logo_target)
        written.append(logo_target)
    written.extend(copy_home_screenshots(ROOT, assets))

    # Copy generated tech image assets
    for img_path in (DOCS_ROOT / "assets").glob("tech_*.png"):
        target = assets / img_path.name
        shutil.copyfile(img_path, target)
        written.append(target)

    nojekyll = SITE_ROOT / ".nojekyll"
    nojekyll.write_text("", encoding="utf-8")
    written.append(nojekyll)

    # Generate technology deep-dive pages
    for tech_id, tech in TECH_PAGES.items():
        target = SITE_ROOT / "technology" / f"{tech_id}.html"
        target.parent.mkdir(parents=True, exist_ok=True)

        code_refs_html = ""
        if tech.get("code_refs"):
            refs_li = "".join(
                f"<li><code>{ref}</code></li>" for ref in tech["code_refs"]
            )
            code_refs_html = f"""
            <div class="code-refs-box">
              <h4>Source Code Reference</h4>
              <ul>{refs_li}</ul>
            </div>
            """

        logo_rel = relative_url(target, SITE_ROOT / "assets" / "istara-logo.png")
        img_rel = relative_url(target, SITE_ROOT / "assets" / tech["image"])
        index_rel = relative_url(target, SITE_ROOT / "index.html")

        tech_content = f"""
        <a href="{html.escape(index_rel)}" class="tech-detail-back">Back to Homepage</a>
        <header class="feature-hero">
          <p class="eyebrow">{html.escape(tech["eyebrow"])}</p>
          <h1>{html.escape(tech["title"])}</h1>
          <p class="lede">{html.escape(tech["summary"])}</p>
        </header>
        <div class="tech-detail-layout">
          <div class="tech-detail-copy">
            {tech["content"]}
            {code_refs_html}
          </div>
          <div class="tech-detail-visual">
            <img src="{html.escape(img_rel)}" alt="{html.escape(tech["title"])} Diagram">
          </div>
        </div>
        """

        shell = page_shell(
            tech["title"],
            build_nav(features, target),
            tech_content,
            current_path=target,
            subtitle=tech["eyebrow"],
            toc='<nav aria-label="Page sections"><ul><li><a href="#main">Overview</a></li></ul></nav>',
            body_class="technology-page",
        )
        target.write_text(shell, encoding="utf-8")
        written.append(target)

    for feature in features:
        for audience in AUDIENCES:
            source = doc_path(feature["id"], audience)
            target = feature_site_path(feature["id"], audience)
            target.parent.mkdir(parents=True, exist_ok=True)
            markdown = source.read_text(encoding="utf-8")
            body = markdown_to_html(markdown, source, target, skip_first_h1=True)
            content = (
                feature_page_header(feature, features_by_id, audience, target) + body
            )
            shell = page_shell(
                feature["title"],
                build_nav(
                    features,
                    target,
                    current_feature_id=feature["id"],
                    audience=audience,
                ),
                content,
                current_path=target,
                subtitle=audience_label(audience),
                toc=build_toc(extract_headings(markdown, skip_first_h1=True)),
                body_class="feature-page",
            )
            target.write_text(shell, encoding="utf-8")
            written.append(target)

    glossary_index = SITE_ROOT / "glossary" / "index.html"
    glossary_index.parent.mkdir(parents=True, exist_ok=True)
    glossary_index.write_text(
        page_shell(
            "Glossary",
            build_nav(features, glossary_index),
            glossary_index_content(features, glossary_index),
            current_path=glossary_index,
            subtitle="Shared concepts",
            toc='<nav aria-label="Glossary sections"><ul><li><a href="#main">Glossary terms</a></li></ul></nav>',
            body_class="glossary-index",
        ),
        encoding="utf-8",
    )
    written.append(glossary_index)

    for source in sorted(GLOSSARY_ROOT.glob("*.md")):
        target = glossary_site_path(source.stem)
        title, content = glossary_page_content(source, features, target)
        target.write_text(
            page_shell(
                title,
                build_nav(features, target),
                content,
                current_path=target,
                subtitle="Shared concepts",
                toc=build_toc(
                    extract_headings(
                        source.read_text(encoding="utf-8"), skip_first_h1=True
                    )
                ),
                body_class="glossary-page",
            ),
            encoding="utf-8",
        )
        written.append(target)

    index_path = SITE_ROOT / "index.html"
    index_path.write_text(
        page_shell(
            "Istara: Rigorous Local-First UX Research Swarms",
            build_nav(features, index_path),
            index_content(features, index_path),
            current_path=index_path,
            subtitle="Local AI swarms",
            toc='<nav aria-label="Home sections"><ul><li><a href="#install">Install</a></li><li><a href="#product-tour">Capabilities</a></li><li><a href="#main-features">Technical Architecture</a></li><li><a href="#research-flow">Research Spine</a></li></ul></nav>',
            body_class="home-page",
        ),
        encoding="utf-8",
    )
    written.append(index_path)

    docs_path = SITE_ROOT / "docs.html"
    docs_path.write_text(
        page_shell(
            "Istara Documentation Hub",
            build_nav(features, docs_path),
            docs_content(features, docs_path),
            current_path=docs_path,
            subtitle="UI organized",
            toc='<nav aria-label="Docs sections"><ul><li><a href="#metrics">Coverage</a></li><li><a href="#feature-map">Menu Structure</a></li><li><a href="#all-features">All Feature Pages</a></li><li><a href="#agent-entrypoints">Agent Entrypoints</a></li></ul></nav>',
            body_class="docs-hub-page",
        ),
        encoding="utf-8",
    )
    written.append(docs_path)
    design_path = SITE_ROOT / "design.md"
    design_path.write_text(DESIGN_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    written.append(design_path)

    manifest = {
        "title": inventory.get("title", "Istara Feature Documentation"),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_inventory": "docs/features/inventory.json",
        "site_entrypoint": "docs/features/site/index.html",
        "search_index": "docs/features/site/search-index.json",
        "features": [
            {
                "id": feature["id"],
                "title": feature["title"],
                "ui_path": feature.get("ui_path", []),
                "nav_group": feature.get("nav_group"),
                "researcher_url": f"features/{feature['id'].replace('.', '/')}/researcher.html",
                "architecture_url": f"features/{feature['id'].replace('.', '/')}/architecture.html",
                "related_features": feature.get("related_features", []),
                "glossary_terms": feature.get("glossary_terms", []),
            }
            for feature in features
        ],
    }
    (SITE_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append(SITE_ROOT / "manifest.json")

    graph = {
        "nodes": [
            {"id": feature["id"], "title": feature["title"]} for feature in features
        ],
        "edges": [
            {"source": feature["id"], "target": target}
            for feature in features
            for target in feature.get("related_features", [])
        ],
    }
    (SITE_ROOT / "feature-graph.json").write_text(
        json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append(SITE_ROOT / "feature-graph.json")

    search_index = [
        {
            "kind": "feature",
            "id": feature["id"],
            "title": feature["title"],
            "ui_path": feature.get("ui_path", []),
            "summary": feature.get("summary", ""),
            "researcher_url": f"features/{feature['id'].replace('.', '/')}/researcher.html",
            "architecture_url": f"features/{feature['id'].replace('.', '/')}/architecture.html",
        }
        for feature in features
    ]
    for source in sorted(GLOSSARY_ROOT.glob("*.md")):
        title = source.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        search_index.append(
            {
                "kind": "glossary",
                "id": source.stem,
                "title": title,
                "url": f"glossary/{source.stem}.html",
            }
        )
    for tech_id, tech in TECH_PAGES.items():
        search_index.append(
            {
                "kind": "technology",
                "id": tech_id,
                "title": tech["title"],
                "summary": tech["summary"],
                "url": f"technology/{tech_id}.html",
            }
        )
    (SITE_ROOT / "search-index.json").write_text(
        json.dumps(search_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append(SITE_ROOT / "search-index.json")

    urls = ["index.html", "docs.html"]
    for tech_id in TECH_PAGES:
        urls.append(f"technology/{tech_id}.html")
    for feature in features:
        base = f"features/{feature['id'].replace('.', '/')}"
        urls.extend([f"{base}/researcher.html", f"{base}/architecture.html"])
    urls.append("glossary/index.html")
    urls.extend(
        f"glossary/{source.stem}.html" for source in sorted(GLOSSARY_ROOT.glob("*.md"))
    )
    base_url = os.environ.get("ISTARA_DOCS_BASE_URL", "").rstrip("/")
    sitemap = "\n".join(
        f"  <url><loc>{html.escape(f'{base_url}/{url}' if base_url else url)}</loc></url>"
        for url in urls
    )
    (SITE_ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap}\n</urlset>\n',
        encoding="utf-8",
    )
    written.append(SITE_ROOT / "sitemap.xml")

    llms = build_llms_txt(features)
    (SITE_ROOT / "llms.txt").write_text(llms, encoding="utf-8")
    (DOCS_ROOT / "llms.txt").write_text(llms, encoding="utf-8")
    written.extend([SITE_ROOT / "llms.txt", DOCS_ROOT / "llms.txt"])
    return written


def build_llms_txt(features: list[dict[str, Any]]) -> str:
    lines = [
        "# Istara Feature Documentation",
        "",
        "Purpose: agent-friendly map of Istara's UI-organized feature docs.",
        "Source inventory: docs/features/inventory.json",
        "HTML entrypoint: docs/features/site/index.html",
        "Machine manifest: docs/features/site/manifest.json",
        "Graph: docs/features/site/feature-graph.json",
        "Search index: docs/features/site/search-index.json",
        "Glossary: docs/features/site/glossary/index.html",
        "",
        "Feature pages:",
    ]
    for feature in sorted(features, key=lambda item: item.get("order", 0)):
        base = f"docs/features/content/{feature['id'].replace('.', '/')}"
        lines.append(
            f"- {feature['id']}: {feature['title']} | {base}/researcher.md | {base}/architecture.md"
        )
    return "\n".join(lines) + "\n"


def is_external_href(href: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*:", href)) or href.startswith("//")


def generated_link_errors() -> list[str]:
    errors: list[str] = []
    if not SITE_ROOT.exists():
        return ["Generated site root does not exist: docs/features/site"]

    id_cache: dict[Path, set[str]] = {}
    for html_file in SITE_ROOT.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        for raw_href in re.findall(r'href="([^"]+)"', text):
            href = html.unescape(raw_href)
            if is_external_href(href):
                continue
            path_part, fragment_sep, fragment = href.partition("#")
            path_part = path_part.split("?", 1)[0]
            target = (
                html_file if not path_part else (html_file.parent / path_part).resolve()
            )
            if path_part and not target.exists():
                errors.append(f"{html_file.relative_to(ROOT)} has broken link: {href}")
                continue
            if fragment_sep and target.suffix == ".html":
                if target not in id_cache:
                    target_text = target.read_text(encoding="utf-8")
                    id_cache[target] = set(re.findall(r'id="([^"]+)"', target_text))
                if fragment and fragment not in id_cache[target]:
                    errors.append(
                        f"{html_file.relative_to(ROOT)} links to missing anchor #{fragment}: {href}"
                    )
    return errors


def validate(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    features = inventory["features"]
    ids = [feature.get("id") for feature in features]
    id_set = set(ids)
    if len(id_set) != len(ids):
        errors.append("Feature IDs must be unique")

    for feature in features:
        feature_id = feature.get("id")
        if not feature_id or not re.match(r"^[a-z0-9][a-z0-9.-]*$", feature_id):
            errors.append(f"Invalid feature id: {feature_id!r}")
            continue
        for key in (
            "title",
            "summary",
            "ui_path",
            "nav_group",
            "component",
            "code_refs",
        ):
            if key not in feature:
                errors.append(f"{feature_id} missing inventory field {key}")
        for related in feature.get("related_features", []):
            if related not in id_set:
                errors.append(
                    f"{feature_id} references unknown related feature {related}"
                )
        for term in feature.get("glossary_terms", []):
            if not (GLOSSARY_ROOT / f"{term}.md").exists():
                errors.append(f"{feature_id} references missing glossary term {term}")
        for source in feature.get("code_refs", []):
            if not (ROOT / source).exists():
                errors.append(f"{feature_id} source reference does not exist: {source}")
        for audience in AUDIENCES:
            path = doc_path(feature_id, audience)
            if not path.exists():
                errors.append(f"Missing {audience} doc for {feature_id}: {path}")
                continue
            frontmatter, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            missing = REQUIRED_FRONTMATTER - set(frontmatter)
            if missing:
                errors.append(
                    f"{path} missing frontmatter: {', '.join(sorted(missing))}"
                )
            if frontmatter.get("stable_id") != feature_id:
                errors.append(f"{path} stable_id mismatch")
            if frontmatter.get("audience") != audience:
                errors.append(f"{path} audience mismatch")
            if "## Evidence" not in body and audience == "researcher":
                errors.append(f"{path} missing Evidence section")
            if "## Compass Evidence" not in body and audience == "architecture":
                errors.append(f"{path} missing Compass Evidence section")

            generated = feature_site_path(feature_id, audience)
            if not generated.exists():
                errors.append(
                    f"Missing generated {audience} HTML for {feature_id}: {generated}"
                )

    for source in sorted(GLOSSARY_ROOT.glob("*.md")):
        generated = glossary_site_path(source.stem)
        if not generated.exists():
            errors.append(
                f"Missing generated glossary page for {source.stem}: {generated}"
            )

    for required in (
        "index.html",
        "docs.html",
        "manifest.json",
        "feature-graph.json",
        "search-index.json",
        "sitemap.xml",
        "llms.txt",
        "assets/site.css",
        "assets/site.js",
        "glossary/index.html",
    ):
        if not (SITE_ROOT / required).exists():
            errors.append(
                f"Missing generated site artifact: docs/features/site/{required}"
            )
    errors.extend(generated_link_errors())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-missing",
        action="store_true",
        help="Create missing per-feature docs from inventory.",
    )
    parser.add_argument(
        "--overwrite-source",
        action="store_true",
        help="Overwrite per-feature markdown source docs.",
    )
    parser.add_argument(
        "--generate-site",
        action="store_true",
        help="Generate static HTML and machine-readable manifests.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate inventory, docs, and generated artifacts.",
    )
    args = parser.parse_args(argv)

    inventory = load_inventory()
    if args.seed_missing or args.overwrite_source:
        print(
            f"seeded {len(seed_missing_docs(inventory['features'], overwrite=args.overwrite_source))} feature doc file(s)"
        )
    if args.generate_site:
        print(f"generated {len(generate_site(inventory))} site artifact(s)")
    if args.check:
        errors = validate(inventory)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"feature docs check passed for {len(inventory['features'])} feature(s)")
    if not any(
        (args.seed_missing, args.overwrite_source, args.generate_site, args.check)
    ):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
