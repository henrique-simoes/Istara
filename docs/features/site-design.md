# Istara Documentation Website Design

This file is copied into `docs/features/site/design.md` whenever the feature
documentation site is generated. It is the durable design contract for the
public website.

## Purpose

The website is Istara's public entry point. It must help visitors understand
what Istara is, install it quickly, see the real product, and then move into
the feature documentation without feeling like they have landed inside an
internal engineering artifact.

## Homepage Strategy

The homepage is product-led and install-first:

- The first viewport must show the value proposition, recommended install
  command, GitHub/docs actions, and real Istara screenshots.
- The product name should be obvious, but the H1 should explain the outcome:
  traceable, report-ready UX research decisions.
- The install command must be visible above the fold and repeated in a full
  install section with Homebrew, shell installer, and source checkout paths.
- Use static sections rather than carousels or hidden interactions.
- Show a broad range of core capabilities early: source ingestion, skills,
  tasks, research validation, retrieval/traceability, and local operation.
- Use real screenshots as proof. Screenshots must show the product surface, not
  decorative atmosphere.
- Search and navigation remain obvious because the site is also documentation.

## Visual Direction

The site uses warm product minimalism: parchment surfaces, forest-green action
states, charcoal text, compact information hierarchy, and product screenshots
as the primary visual signal. The sample HTML used during exploration is
visual inspiration only; visible copy, metadata, dates, version labels, and
snippets must be written specifically for Istara.

- Use `#f8f2e6` (parchment cream) as the dominant page background. This matches the background of the schematic diagrams exactly, allowing them to blend seamlessly into the pages without rigid bounding boxes.
- The schematic diagrams utilize light themes that contrast elegantly with the surrounding layout elements and each other, which must be preserved as a core part of the visual system.
- Use `#1b1b1b` / charcoal text for readable primary content.
- Use `#6B6B5F` for secondary text and navigation metadata.
- Use `#DCD9CE` or nearby stone tones for borders and section separation.
- Use `#2F4F2F` / `#18381a` for high-impact install actions and focused
  navigation states.
- Use the Istara logo as a brand mark, not as a giant decorative background.
- Avoid novelty gradients, decorative orbs, heavy shadows, giant hero type,
  metadata rails, auto-rotating carousels, and distorted type scale.
- Product imagery must show real Istara surfaces where possible. Screenshots
  should explain the workflow, not decorate the page.

## Layout

- The hero uses a two-column desktop layout: copy and install command on the
  left, product screenshot composition on the right.
- On mobile, the hero collapses into a single column with one clear screenshot
  preview and no horizontal overflow.
- The 10 core capability and technical architecture points are transformed into full-bleed, alternating sections directly on the homepage. Each section features a detailed copy block and technical pillars on one side, and a large-format schematic diagram on the other side, separated by clean, horizontal border boundaries (`1px solid var(--border)`).
- Documentation pages keep the left feature map, search, audience tabs, and
  page table of contents so users can navigate without losing context.
- Generated feature pages must retain stable landmarks: skip link, banner,
  search, nav, main, and page-section aside.
- The homepage answers, in order: what Istara does, how to install it, which
  features matter, what the workspace looks like, and how research becomes
  reportable.

## Type Scale

- Use Inter for the generated site.
- Body copy should stay around 16px with readable line height.
- Feature-page headings should be compact enough for dense documentation.
- Hero text may be larger, but the H1 must not dominate the full screen.
- Letter spacing stays at `0` for generated CSS.
- Buttons and cards should use concise labels, not marketing paragraphs.

## Components

- Primary buttons use the forest-green action token with white text in light
  mode.
- Secondary buttons use parchment or white surfaces with stone borders.
- Controls use a 4px radius. Large repeated cards and screenshot frames use an
  8px radius.
- Cards should rely on tonal backgrounds, borders, and very soft hover depth
  rather than heavy elevation.
- Interactive Technology Sections:
  - Homepage capability and technical architecture cards are transformed into full-width alternating sections directly on the homepage, presenting detailed feature summaries and their large schematic diagrams side-by-side.
  - Each section includes a button (`Explore Architecture Deep-Dive →`) linking to its dedicated deep-dive explanation page (`technology/<id>.html`).
  - Technology deep-dive subpages follow this same pure white background format and use a responsive two-column layout (`.tech-detail-layout`) showing the comprehensive system copy and source code references on the left, and a large-format schematic diagram on the right.
- Long install commands must wrap or scroll without creating horizontal page
  overflow.

## Accessibility And Heuristics

- Maintain visible keyboard focus with `:focus-visible`.
- Preserve semantic landmarks and accessible labels.
- Keep normal text and button labels at or above WCAG AA contrast.
- Do not use dark green text on dark green buttons; primary install actions use
  `--action-bg: #2f4f2f` with `--action-text: #ffffff` in light mode.
- Avoid horizontal overflow on mobile and long command strings.
- Do not hide install options behind hover-only interactions.
- Respect reduced cognitive load: clear headings, predictable navigation, and
  copyable commands.

## Generation Contract

The source of truth is:

- `scripts/feature_docs.py` for page structure and generated artifacts.
- `scripts/feature_docs_assets.py` for CSS and JavaScript.
- `scripts/feature_docs_home.py` for homepage conversion sections and product
  screenshot assets.
- `docs/features/assets/istara-logo.png` for the optimized web logo.
- `tests/test_feature_docs.py` for generated-site contract checks.
- `.github/workflows/pages.yml` for GitHub Pages build and deployment.

After changing website design or navigation, run:

```bash
python scripts/feature_docs.py --seed-missing --generate-site --check
pytest tests/test_feature_docs.py -q
```
