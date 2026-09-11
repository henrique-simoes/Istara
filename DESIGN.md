# Istara interface system

This is the portable design contract for the authenticated product UI. It applies to
Settings, Project Settings, Chat, and future control surfaces. Production behavior and
API contracts remain owned by tested code; this document owns the visual and interaction
language.

## Direction

- **Genre:** modern-minimal, technical but humane.
- **Audience:** research practitioners and project administrators, not AI engineers.
- **Primary job:** choose a trustworthy engine/model and understand what the next request
  will cost and how much context it uses.
- **Tone:** calm, explicit, capable. Never make users infer a provider capability from a
  raw identifier.
- **App macrostructure:** Workbench — a clear page heading, one explanatory lead, then
  task-oriented sections with a single focal control per section.
- **Information hierarchy:** section title → plain-language explanation → choice/control →
  status/evidence. Do not bury high-impact configuration inside a status grid.

## Semantic tokens

The current product uses the existing Istara green and slate palette. New UI must consume
semantic roles rather than inventing one-off colors:

- `--ui-surface` / `--ui-surface-raised`: page and panel surfaces.
- `--ui-ink` / `--ui-ink-muted`: primary and secondary text.
- `--ui-rule` / `--ui-rule-strong`: boundaries and selected controls.
- `--ui-accent` / `--ui-accent-soft`: primary action and selected state.
- `--ui-focus`: keyboard focus ring; never animated.
- `--ui-danger` / `--ui-warning` / `--ui-success`: state plus an icon or text label.
- `--ui-radius-panel` (16px), `--ui-radius-control` (10px), `--ui-radius-pill` (999px).
- `--ui-control-height` (44px) for every input, select, button, and touch target.

Light and dark modes must preserve the same semantic roles and a minimum WCAG 2.2 AA
contrast ratio: 4.5:1 for body text and 3:1 for controls, icons, and focus indicators.

## Token architecture

Three layers. New UI consumes layer 2 (semantic) or higher; raw primitives in component
code are a review finding.

**Layer 1 — primitives.** The project accent ramp lives in `frontend/tailwind.config.js`
(`istara-50…950`, green family; `600` is deliberately darker than Tailwind's default green
for AA compliance). Neutrals are Tailwind v3 `slate`; state hues use Tailwind `amber`,
`red`, and `blue`. Primitives are never referenced directly by product components.

**Layer 2 — semantic aliases.** Implemented once as CSS variables in
`frontend/src/app/globals.css` (`:root` and `.dark`). These values are normative:

| Role | Light | Dark | Used for |
| --- | --- | --- | --- |
| `--ui-surface` | `#ffffff` | `#0f172a` | page panels (`.ui-panel`) |
| `--ui-surface-raised` | `#f8fafc` | `#172033` | raised cards, menus |
| `--ui-surface-soft` | `#f1f5f9` | `#1e293b` | soft wells, tiles |
| `--ui-ink` | `#0f172a` | `#f8fafc` | primary text |
| `--ui-ink-muted` | `#475569` | `#cbd5e1` | secondary text |
| `--ui-ink-subtle` | `#64748b` | `#94a3b8` | helper/metadata text |
| `--ui-rule` | `#e2e8f0` | `#334155` | hairline boundaries |
| `--ui-rule-strong` | `#cbd5e1` | `#475569` | emphasized boundaries |
| `--ui-accent` | `#15803d` | `#4ade80` | selected state, primary action |
| `--ui-accent-soft` | `#f0fdf4` | `#052e16` | accent tint backgrounds |
| `--ui-focus` | `#2563eb` | `#93c5fd` | keyboard focus ring; never animated |
| `--ui-danger` | `#b91c1c` | `#fca5a5` | destructive/error, always with a label |
| `--ui-warning` | `#a16207` | `#facc15` | caution, always with a label |
| `--ui-success` | `#166534` | `#86efac` | success, always with a label |

Shape and control metrics: `--ui-radius-panel` 16px, `--ui-radius-control` 10px,
`--ui-radius-pill` 999px, `--ui-control-height` 44px.

**Layer 3 — portable export.** `docs/design/tokens.json` is generated from the two sources
above by `python scripts/export_design_tokens.py` (W3C DTCG format). It is never
hand-edited; CI-style checks run `--check` to fail on drift. This is the file design tools
and other agents consume; `DESIGN.md` remains the human authority.

**Enforcement.** `scripts/check_a11y_contrast.py` composites every alpha-modified pair over
its real parent chain and measures both modes against the 4.5:1 / 3:1 bar;
`tests/test_a11y_contrast.py` fails the suite when a token or class change breaks it.
Adding a surface means adding its pairs to that audit in the same change.

## Typography and spacing

- Preserve the repository's system UI font stack for compatibility; use weight and space
  for hierarchy rather than adding a display face to an application control surface.
- Body text is at least 16px; helper text is at least 14px; compact metadata is at least
  12px and never carries essential meaning alone.
- Use the existing 4px-derived Tailwind rhythm. Prefer 8/12/16/24/32px gaps.
- Prose and explanations target 45–75 characters per line.
- Numeric telemetry uses tabular figures and explicit units.

## Components

### Browseable combobox

A model/provider picker always supports both paths: (1) click the chevron or focus the
field to browse a visible list, and (2) type to filter/autocomplete. It uses a labelled
`role="combobox"`, `aria-expanded`, a `role="listbox"`, arrow-key navigation, Enter to
select, Escape to close, an explicit result count, and a no-results recovery message.
The list is positioned as a popover so it never pushes or clips the page.

### Engine choice

Agentic Core is a first-class section, never a row in System Status. Global and project
scope use the same comparison component. Pi and Istara each show: what it is, who it is
for, what changes, the shared embedding invariant, and the source-linked provisional
benchmark snapshot. Benchmark numbers are never invented or presented as accepted
research evidence.

### Chat model controls

The chat toolbar is a compact workbench, not a string of tiny unlabeled dropdowns. It
shows the selected agent, provider/model, and exact model effort. The model menu supports
browse + autocomplete and makes unavailable/unconfigured models visibly unavailable with
an explanation. The effort menu is generated from the selected model's `thinkingLevels`;
no generic “High” label replaces a provider's exact levels. Usage is always visible in a
compact summary and expandable detail view: input, output, total, cache read/write, cost,
context used, source (provider-reported vs estimated), and last stop reason.

## States and motion

Every interactive control implements default, hover (pointer-capable devices only),
`:focus-visible`, active, disabled, loading, error, and success states without changing
layout geometry. Focus rings appear immediately with a 2px outline. Controls never use
`transition: all`.

- Dropdown open/close: opacity + translateY, 180ms in / 140ms out, ease-out/ease-in.
- Status changes: opacity-only, ≤150ms under reduced motion.
- Save success is silent when the visible value changed; failures explain what happened
  and how to recover.
- All motion is disabled or reduced under `prefers-reduced-motion: reduce`.

## Responsive and accessibility acceptance

Prove Settings, Project Settings, and Chat at 320, 375, 414, 768, and 1280 CSS pixels.
There is no horizontal document scroll. Buttons and primary controls remain at least
44×44px. Clickable labels do not wrap into two lines. Menus are keyboard reachable and
screen-reader labelled. Color is never the only state signal. Permission-denied,
loading, empty, error, and success states are part of the interaction contract.

## Governance — authority model and change flow

| Domain | Authority |
| --- | --- |
| User-visible behavior, routes, data, component props | Tested production code |
| Visual language, token names/roles, component contracts | This document + `docs/design/tokens.json` |
| Token values as consumed at runtime | `globals.css` / `tailwind.config.js` (projections of this doc) |
| Research-validity claims in any UI copy | The research spine contract; benchmarks stay provisional |

When code and this document disagree, stop the affected slice, reconcile the authority
first, then update projections (tokens export, components) — never silently pick the
newest timestamp.

Meaningful visual-system changes run through Compass Forge with Build Stream evidence:
spec → slice → `scripts/check_a11y_contrast.py` + `export_design_tokens.py --check` →
feature-docs regeneration → review. Do/don'ts: don't invent one-off colors, don't hardcode
focus-ring hues outside `--ui-focus`, don't animate layout or delay focus visibility, don't
ship a state you have not measured in both modes.
