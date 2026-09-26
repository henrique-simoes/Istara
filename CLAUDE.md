# Istara — Claude Code instructions

@AGENTS.md

Everything in `AGENTS.md` applies. This file adds only what is specific to Claude agents.
Codex and other harnesses: the browser and design rules below apply to you too.

## Delivery: build-stream + Compass Forge, one agent

All non-trivial work in Istara (features, fixes touching more than one surface, spine, auth,
pi, CI, releases) runs through the **`build-stream`** and **`compass-forge`** skills: frame
with the owner → Compass Forge spec → plan → execute → verify → ship, recorded in one
lifecycle file under `docs/build-stream/`.

- Do not use subagents or multi-agent pipelines (the owner's standing rule). Review coverage
  is recorded honestly as self-only unless the owner arranges an independent review.
- Trivial edits (typos, single-file docs, lookups) may skip the lifecycle file but still follow
  the Compass Forge pre/post-edit protocol in `AGENTS.md` §2.
- Branching follows `AGENTS.md` §3.

## Definition of done

1. CF impact + test-impact read before editing; gates run after.
2. Targeted automated tests pass (`TESTING.md` "Choosing Tests For A Change").
3. **The change is exercised in the UI as a real user would** — see below — including an
   agentic chat turn on both engines when chat, tools, models, or the spine are affected.
4. Scenario added/updated in `tests/simulation/scenarios/`; evidence attached to the CF task.
5. `Tech.md`, personas, feature docs, and telemetry/benchmark results updated when their CI
   obligations trigger.

## UI verification

- **Prefer the browser extension over Playwright for inspection**: use the Claude in Chrome
  tools (or the in-app Browser pane) to navigate, click, fill, read the accessibility tree,
  and check console/network while walking the user flow. Codex agents use their browser
  extension equivalently. Playwright is for the committed, repeatable scenarios in
  `tests/simulation/`, not for ad-hoc inspection.
- Target a disposable QA stack (`scripts/istara-qa.sh up --run-id <branch>-<date> --profile ui`),
  never the protected `never-delete-official-*` containers. Starting servers or making live
  model calls still needs owner permission (`AGENTS.md` §9).
- Walk every menu and sub-menu the change can reach: happy path, empty/loading/error states,
  role differences, light/dark, 375px width, keyboard focus. Report what you saw, with
  screenshots, not what the code implies.

## Design work

- Load the **`interface-design`** skill for any UI change, audit, or visual debug; follow
  `DESIGN.md` tokens (Tailwind primitives → `globals.css` semantic variables →
  `docs/design/tokens.json` via `python scripts/export_design_tokens.py`) and run
  `python scripts/check_a11y_contrast.py`.
- Use Anthropic's design skills where they fit: `artifact-design` / `dataviz` for reports,
  benchmark dashboards, and charts; `design` for mockups before building.

## Subagent hygiene

- Give subagents file paths and the exact question; ask for conclusions, not dumps.
- Read-only recon never edits; implementers own disjoint files.
- Never let a subagent stop, remove, or prune Docker containers or volumes.
