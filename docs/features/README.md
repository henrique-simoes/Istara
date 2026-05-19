# Istara Living Feature Documentation

This directory is the source and generated output for Istara's UI-organized feature documentation system.

## Structure

- `inventory.json` is the code-evidence-backed feature inventory. It mirrors the current Istara menus, tabs, sub-tabs, and major feature surfaces.
- `content/<feature-id>/researcher.md` is the UX researcher and user-facing version of a feature page.
- `content/<feature-id>/architecture.md` is the engineering and AI architecture version of the same feature page.
- `glossary/*.md` explains shared concepts linked from feature docs.
- `site/` is generated hostable HTML and machine-readable output. It includes an app-like navigation shell, light/dark theme toggle, search/filter controls, per-feature audience tabs, generated glossary pages, and WCAG-conscious landmarks, focus states, and contrast.
- `llms.txt` is the agent entrypoint for quickly locating source docs and generated manifests.

## Update Workflow

Run the generator after any UI menu, route, store, agent, skill, model, test, or workflow change that affects feature behavior:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
```

Use `--overwrite-source` only when intentionally regenerating source docs from `inventory.json`; it will replace manually edited feature pages.

## Evidence Expectations

Feature claims must cite source files in `inventory.json` and in each page's frontmatter. If behavior is visible as a component, tab, route, or store but has not been verified through an interactive walkthrough or focused test, mark the feature `needs-verification` and document the uncertainty plainly.

Before finishing Compass Forge work that changes a documented surface, attach evidence for:

- the files or routes inspected,
- the feature docs or glossary pages updated,
- `scripts/feature_docs.py --check`,
- generated `docs/features/site/manifest.json`, `feature-graph.json`, `search-index.json`, `sitemap.xml`, glossary HTML pages, and `llms.txt`,
- unresolved gaps or intentionally deferred walkthroughs.

The generator validates that every inventoried feature has researcher and architecture HTML pages, every glossary source has a generated glossary page, and local generated links resolve. Do not hand-edit `docs/features/site/`; update `inventory.json`, source pages, glossary pages, or `scripts/feature_docs.py`, then regenerate.
