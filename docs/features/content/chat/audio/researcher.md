---
stable_id: chat.audio
title: Chat Audio Conversation
ui_path: Chat > Audio
audience: researcher
status: needs-verification
related_features: ["chat.overview", "interviews.transcription"]
related_glossary: ["wcag"]
code_references: ["frontend/src/hooks/useVoiceRecorder.ts", "frontend/src/components/chat/ChatView.tsx", "backend/app/api/routes/chat_voice.py", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/chat_voice.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Chat Audio Conversation

### Model availability

Audio works only when an administrator has configured a supported audio profile.
Local Whisper, compatible remote Whisper, and supported diarized providers are
advertised separately. Unavailable providers do not silently route audio to a
text model, and transcription output remains provisional until reviewed.

## What It Does

The chat audio flow records user speech through the browser, sends it to the voice route, and returns transcription or voice-assisted chat input.

## Why It Exists

Chat Audio Conversation exists so the work represented by Chat > Audio has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Chat > Audio
- Navigation group: Chat
- Primary component: `useVoiceRecorder`

## How UX Researchers Use It

- Open Chat > Audio from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with chat audio conversation in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Chat > Audio when the current research task needs chat audio conversation.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: chat.overview, interviews.transcription.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with chat audio conversation.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [chat.overview](../../chat/overview/researcher.md)
- [interviews.transcription](../../interviews/transcription/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/hooks/useVoiceRecorder.ts`, `frontend/src/components/chat/ChatView.tsx`, `backend/app/api/routes/chat_voice.py`, `backend/app/core/transcription.py`
- API references: `backend/app/api/routes/chat_voice.py`
- Tests: none recorded
