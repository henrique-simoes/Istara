# Build Stream — Settings List Collapse & Chat Model Integration

<!-- STATUS BLOCK -->
```yaml
item: settings-collapse-chat-model-integration
branch: testing
phase: "Phase 3 — Gates, evidence, close"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T14:41:33Z, ledger: L-003 }
next_action: "Owner review on QA; no merge without explicit outward-action approval."
```
<!-- /STATUS BLOCK -->

## Plan Overview & Roadmap

### S0 Frame (owner-approved in chat, DEC-1)
1. **Settings collapse:** every card list with >5 items collapses to 5 with
   `Click to see N more {noun}` / `Show fewer {noun}` (SessionManager pattern,
   threshold unified 3→5). Covers: Active Sessions, Governed Evolution
   proposals/archive/reasoning/contract, Pi connected-models + research
   preferences. DESIGN.md: semantic tokens only, labelled controls,
   `aria-expanded`, 44px targets, no layout animation, both modes.
2. **Chat picker integration bug:** ready Pi endpoints whose model id is absent
   from the shipped catalog (proven live: `glm-5.3-flash`, local/custom models)
   can never match a catalog row, so they show permanently disabled. Fix:
   normalize provider compare (+`provider_kind` fallback), append configured-
   but-unmatched endpoints as standalone enabled choices, badge ready choices
   `Configured`, keep disabled rows as `Configure in Settings`. Effort menu
   unchanged (generated from matched model's `thinkingLevels`, generic fallback
   otherwise); selection writes `model_override` + `endpoint_override` as before.

### Phases
| Phase | Scope | Exit |
| :--- | :--- | :--- |
| 1 | `SeeMoreList` + apply to 7 lists; chat matcher extraction + fix + badges | vitest green, `next build` green |
| 2 | QA sync (frontend only → rebuild `qa-ui`), Playwright prove both items | screenshots + report, no console/net regressions |
| 3 | CF gate-after/evidence, docs, ledger close | 0 new drift, status done |

### Decision log
- **DEC-1** (2026-09-08, S0, owner): scope approved in chat — collapse threshold 5
  everywhere including sessions (was 3); chat fix is frontend-only, backend
  projection already supplies all needed fields.

## Append-Only Ledger

- **L-001** (2026-09-08): Plan opened from owner request. Live diagnosis on QA:
  catalog (1307 models) lacks `glm-5.3-flash` and local model ids, so ready
  endpoints `pi-zai-glm`/`pi-local-*` can never satisfy the catalog-row match in
  `ChatModelControls.tsx:254-257` — root cause of "available models not shown".
- **L-002** (2026-09-07T14:04:00Z): SHIP — both items delivered, verified, live on QA.
  Collapse: new `SeeMoreList.tsx` (>5 → 5 + `Click to see N more`/Show fewer,
  `aria-expanded`/`aria-controls`, 44px target, no animation) applied to Active
  Sessions (threshold unified 3→5), evolution proposals/archive/reasoning/
  contract, Pi connected-models + research preferences (`ul`/`ol` converted to
  `role=list`/`listitem` to stay valid HTML). Chat: matcher extracted to
  `modelCatalog.ts` (`normalizeProviderId`, `buildChatModelChoices`,
  `resolveChatModelChoice`) — normalized provider compare with
  `provider_kind` fallback, ready-but-unmatched endpoints appended as standalone
  enabled rows, `Configured` badge on ready rows, disabled rows keep
  `Configure in Settings`; effort coupling and selection writes unchanged.
  Verified: vitest 79/79 (5 new matcher tests, red→green), `next build` green,
  backend focused 53/53, security 28/28 100%, feature docs 86/224 ok,
  `git diff --check` clean. QA (`qa-ui` rebuilt only, backend untouched):
  Playwright proof — 12 proposals + 85 sessions toggles expand/collapse with
  restore; `glm-5.3-flash` 1/1 enabled+badged (was invisible), `gpt-5.6-luna`
  1 enabled+badged of 13 (rest honestly disabled); no console/net regressions.
  CF: CF-SPEC-14 (a duplicate empty draft spec from a double CLI call left
  untouched), CF-126/CF-127 evidenced (943/944, asserted) and finished; gate
  after 0 new failures. Notes: one junk evidence row on CF-126 from a status
  check typo (`ledger-close check`) — ignored, no content impact; CF-SPEC-14
  left unaccepted (auto-generated process tasks open).
  Residual: legacy-engine projects keep legacy-first ordering (parity);
  reasoning-bank tool link still unwired (no producer).
- **L-003** (2026-09-07T14:41:33Z): Follow-up review closed (owner report: list
  still incomplete; old session missing luna). Forensics FIRST: local :3000 →
  `qa-ui-1` (my rebuilt image) and :8000 → proxy→backend — stale-container
  hypothesis REFUTED (tunnel `ssh -f -N -L 3000/8000 macstudio`, remote
  `docker ps` port map). Live sessions API showed session `f6cd0aae` carrying
  `model_override=models/gemini-2.5-flash` — the picker was correctly displaying
  the session's persisted choice, not luna. Real gap #2: on legacy engine the
  order was legacy + catalog-order, burying ready rows mid-list (luna's enabled
  row was 1-of-13, browsing showed bedrock spam). Fix: legacy order is now
  legacy → enabled Pi → disabled (`modelCatalog.ts`, test red→green).
  Verified: 80/80 unit, build green, `diff --check` clean, CF impact/test-impact
  high/complete, gate after CF-127 0 new, evidence 949 asserted. QA (`qa-ui`
  rebuilt): browse rows 0–1 legacy, 2–9 ALL 8 ready configured+badged, 10+
  honestly disabled; picking luna drives provider-native effort
  (server_default/xhigh/max/minimal); selection restored and sessions API
  identical after (no residue). No Blockers; session-override display is
  per-session design (switch with one click), explained to owner.
