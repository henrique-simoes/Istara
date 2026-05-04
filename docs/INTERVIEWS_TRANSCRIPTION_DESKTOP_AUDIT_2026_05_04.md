# Interviews, Transcription, and Desktop Tray Audit

Date: 2026-05-04

## SDD Contracts

1. Audio uploaded from Interviews or Documents must create a `Document` immediately with `processing` status, then transition to `ready` only when a real transcript is available.
2. Transcription failures must not be indexed as research text. They must leave the document in `error` status with a typed dependency or runtime cause.
3. Whisper language auto-detection must be preserved unless a caller explicitly supplies a language. The detected language, confidence estimate, ICR result, review flag, and tags must be stored with the document.
4. Audio preview APIs must return stored transcript text for audio documents, plus media playback metadata.
5. Server installation must verify Python, Node, and FFmpeg before claiming backend dependencies are installed.
6. Desktop dependency detection must expose FFmpeg as a required server-mode dependency.
7. The tray app must not kill unrelated processes occupying Istara ports. It should report port conflicts instead.
8. Messaging-channel audio, including WhatsApp voice/audio webhooks, must be downloaded into bounded local storage, transcribed before dispatch, and routed through the same inbound persistence path as text messages.
9. Channel inbound processing must use the current `ChannelConversation` and `ChannelMessage` schema, persist inbound messages even when no deployment is active, and advance adaptive interview questions without repeating the previous prompt.

## Findings Addressed

- The Interviews preview path loaded media metadata from `/api/files/.../content/...`, but that route returned `content: null` for all audio files even after background transcription succeeded.
- The Documents preview path returned `content: null` for audio documents before falling back to stored `content_text`.
- Audio transcription errors were being chunked and indexed as if they were valid transcript text.
- The installer listed `openai-whisper` but did not install or detect FFmpeg, which Whisper requires for decoding.
- The shell installer masked backend `pip install` failures because the install command was piped through `grep ... || true`.
- The desktop setup wizard did not detect or install FFmpeg.
- Tray start/stop force-killed any process listening on ports 3000 or 8000, which is unsafe on production workstations.
- The transcription ICR fallback generated synthetic agreement from the original transcript. This is not statistically independent, so it now reports insufficient evidence unless an alternative model pass succeeds.
- WhatsApp audio no longer stops at a pending marker. The adapter downloads Graph API media with declared/actual byte caps, stores it in sanitized channel storage, runs local transcription, and dispatches transcript metadata with language, confidence, ICR, review flag, and tags.
- The channel router is now wired to the inbound processor at startup, and the inbound processor was updated to the current channel conversation/message schema.
- Adaptive interview routing now treats `current_question_index` as the next question to ask, so the first participant answer advances from Q1 to Q2 instead of repeating Q1.

## Remaining Follow-Up

- The transcript tagger is still keyword-based and mostly English. It is safe as metadata, but multilingual production tagging should move to a language-aware classifier or LLM-assisted review path.
- Tray port management now avoids destructive cleanup. A future enhancement can identify Istara-owned orphan processes by command line and stop only those.
