---
stable_id: chat.audio
title: Chat Audio Conversation
ui_path: Chat > Audio
audience: architecture
status: needs-verification
related_features: ["chat.overview", "interviews.transcription"]
related_glossary: ["wcag"]
code_references: ["frontend/src/hooks/useVoiceRecorder.ts", "frontend/src/components/chat/ChatView.tsx", "frontend/src/lib/chatApi.ts", "backend/app/api/routes/chat.py", "backend/app/api/routes/chat_voice.py", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/chat.py", "backend/app/api/routes/chat_voice.py"]
test_references: ["tests/e2e_test.py", "tests/simulation/scenarios/77-voice-transcription.mjs", "tests/simulation/scenarios/78-real-time-voice.mjs", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-109 / CF-1379
---

# Chat Audio Conversation Architecture

## Governed audio model settings

Audio transcription uses one explicit `AudioModelProfile` contract for interview
uploads, microphone chat, and channel audio. Supported provider families are
`local_whisper`, compatible `remote_whisper`, and `gpt4_diarization`. Settings
responses expose capabilities and an opaque credential reference only; secrets
and provider URLs are never returned. An empty or unsupported profile is
unavailable and does not fall back to a text/Pi model. Transcripts remain
provisional research source material until review gates pass.

## Implementation Summary

The chat audio flow records user speech through the browser, sends it to the voice route with the active `project_id`, and returns transcription or voice-assisted chat input only inside that project scope.

## Frontend Surface

- `frontend/src/hooks/useVoiceRecorder.ts`
- `frontend/src/components/chat/ChatView.tsx`
- `frontend/src/lib/chatApi.ts`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/chat_voice.py`
- `backend/app/core/transcription.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `frontend/src/lib/chatApi.ts` appends `project_id` to the voice transcription `FormData`.
- `frontend/src/hooks/useVoiceRecorder.ts` trims and validates the project id before transcribing, and stops the recording with a project-selection error when no active project is available.
- `backend/app/api/routes/chat.py` and `backend/app/api/routes/chat_voice.py` reject blank or unauthorized project ids before returning dummy or real transcription responses.

## Architecture Notes

- The feature is mounted through `frontend/src/hooks/useVoiceRecorder.ts` and the UI navigation path recorded in the inventory.
- Voice tests must use the runner's persistent simulation project. They must not fall back to placeholder project ids or the first project visible to a global admin.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/e2e_test.py` sends the created E2E project id to `/api/chat/voice-transcribe` without a fallback placeholder.
- `tests/simulation/scenarios/77-voice-transcription.mjs` posts a project-scoped `FormData` request and expects the route to fail on missing audio only after accepting the project scope.
- `tests/simulation/scenarios/78-real-time-voice.mjs` seeds the active project in browser storage before checking microphone controls.
- `tests/test_project_scope_contracts.py` prevents regression to placeholder project ids in voice and simulation harness checks.

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
