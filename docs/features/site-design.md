# Istara Documentation Website Design

This file is copied into `docs/features/site/design.md` whenever the feature
documentation site is generated. It is the durable design contract for the
public website.

## Purpose

The website is Istara's public entry point. It must help visitors understand
what Istara is, install it, and move into the feature documentation without
feeling like they have landed inside an internal engineering artifact.

## Visual Direction

- Use the Istara logo as the primary visual anchor.
- Match the page background to the logo background color: `#bdb6a4`.
- Keep the hero quiet, editorial, and product-focused rather than oversized.
- Avoid novelty gradients, decorative orbs, and distorted type scale.
- Use dark green as the main action color and warm neutral surfaces for reading.

## Layout

- The first viewport must show the product name, local-first UX research value
  proposition, install action, docs action, and GitHub action.
- Installation commands must be visible on the homepage, copyable, and grouped
  by operating-system/setup path.
- Documentation pages keep the left feature map, search, audience tabs, and
  page table of contents so users can navigate without losing context.
- Generated feature pages must retain stable landmarks: skip link, banner,
  search, nav, main, and page-section aside.

## Type Scale

- Body copy should stay around 15px with readable line height.
- Feature-page headings should be compact enough for dense documentation.
- Hero text may be larger, but the H1 must not dominate the full screen.
- Buttons and cards should use concise labels, not marketing paragraphs.

## Accessibility And Heuristics

- Maintain visible keyboard focus with `:focus-visible`.
- Preserve semantic landmarks and accessible labels.
- Keep contrast sufficient on the warm logo-background palette.
- Avoid horizontal overflow on mobile and long command strings.
- Do not hide install options behind hover-only interactions.
- Respect reduced cognitive load: clear headings, predictable navigation, and
  copyable commands.

## Generation Contract

The source of truth is:

- `scripts/feature_docs.py` for page structure and generated artifacts.
- `scripts/feature_docs_assets.py` for CSS and JavaScript.
- `docs/features/assets/istara-logo.png` for the optimized web logo.
- `tests/test_feature_docs.py` for generated-site contract checks.
- `.github/workflows/pages.yml` for GitHub Pages build and deployment.

After changing website design or navigation, run:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
```
