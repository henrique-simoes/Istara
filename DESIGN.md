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
