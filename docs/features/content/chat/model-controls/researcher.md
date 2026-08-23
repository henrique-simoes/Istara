---
stable_id: chat.model-controls
title: Chat Model Controls
ui_path: Chat > Model Controls
audience: researcher
status: documented
related_features: ["settings.llm-servers", "settings.general", "compute.pool"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/chat/ChatView.tsx", "frontend/src/components/chat/ChatModelControls.tsx", "frontend/src/components/chat/chatViewParts.tsx", "frontend/src/stores/chatStore.ts", "frontend/src/stores/sessionStore.ts", "frontend/src/lib/chatApi.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/sessions.py"]
test_references: ["frontend/src/lib/modelProviders.test.ts", "tests/test_chat.py", "tests/pi_production/test_pi_catalog_ux.py"]
last_verified: 2026-08-23
compass: CF-SPEC-53 / CF-657
---

# Chat Model Controls

## What It Does

Chat exposes a workbench-style model and effort menu. Users can browse or autocomplete configured Pi providers/models, choose the exact provider-native effort levels supported by the selected model, and inspect token, cache, context, cost, engine, and estimate status in Usage.

## Why It Exists

Chat Model Controls exists so the work represented by Chat > Model Controls has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat > Model Controls
- Navigation group: Chat
- Primary component: `ChatView / chatViewParts`

## How UX Researchers Use It

- Open Chat > Model Controls from the Istara navigation or the parent tab.
- Click the model chevron to browse, or type to autocomplete a provider/model.
- Choose the exact effort level shown for the selected model, then send the next turn.
- Open Usage to inspect input/output/total tokens, cache read/write, cost, context used, turns, engine, stop reason, and exact-vs-estimated status.

## Supported Workflows

- Start from Chat > Model Controls when the current research task needs chat model controls.
- Unconfigured catalog entries remain visible but disabled; connect them from Settings > Pi Model Management.
- Change the model and effort for the next turn without leaving the conversation.

## Inputs, Outputs, And Expected Outcomes

- The active session stores the selected model, endpoint identity, and effort additively.
- The usage ledger returns content-free per-session totals; provider-reported values are marked exact and missing-provider values are marked estimated.
- Existing transcript events remain unchanged; governed turns add a usage event for the menu.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.general](../../settings/general/researcher.md)
- [settings.project](../../settings/project/researcher.md)
- [compute.pool](../../compute/pool/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/chat/ChatView.tsx`, `frontend/src/components/chat/ChatModelControls.tsx`, `frontend/src/stores/chatStore.ts`, `frontend/src/lib/chatApi.ts`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/sessions.py`
- API references: `backend/app/api/routes/chat.py`, `backend/app/api/routes/sessions.py`
- Tests: `frontend/src/lib/modelProviders.test.ts`, `tests/test_chat.py`, `tests/pi_production/test_pi_catalog_ux.py`
