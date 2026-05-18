---
stable_id: chat.audio
title: Chat Audio Conversation
ui_path: Chat > Audio
audience: architecture
status: needs-verification
related_features: ["chat.overview", "interviews.transcription"]
related_glossary: ["wcag"]
code_references: ["frontend/src/hooks/useVoiceRecorder.ts", "frontend/src/components/chat/ChatView.tsx", "backend/app/api/routes/chat_voice.py", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/chat_voice.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Audio Conversation Architecture

## Implementation Summary

The chat audio flow records user speech through the browser, sends it to the voice route, and returns transcription or voice-assisted chat input.

## Frontend Surface

- `frontend/src/hooks/useVoiceRecorder.ts`
- `frontend/src/components/chat/ChatView.tsx`
- `backend/app/api/routes/chat_voice.py`
- `backend/app/core/transcription.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/chat_voice.py`

## Architecture Notes

- The feature is mounted through `frontend/src/hooks/useVoiceRecorder.ts` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [chat.overview](../../chat/overview/architecture.md)
- [interviews.transcription](../../interviews/transcription/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
