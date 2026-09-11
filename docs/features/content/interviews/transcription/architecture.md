---
stable_id: interviews.transcription
title: Interview Transcription
ui_path: Interviews > Transcription
audience: architecture
status: needs-verification
related_features: ["interviews.files", "findings.evidence"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/interviews/InterviewView.tsx", "frontend/src/components/interviews/AudioPlayer.tsx", "backend/app/core/transcription.py"]
api_references: ["backend/app/api/routes/files.py"]
test_references: ["tests/real_user_benchmark/run.mjs"]
last_verified: 2026-05-20
compass: CF-SPEC-53 / CF-657; CF-SPEC-121
---

# Interview Transcription Architecture

## Implementation Summary

Interview audio processing uses backend transcription capabilities to turn recordings into usable research text. The real-user benchmark exercises the credential-free interview path through uploaded transcripts and `analyze-interview` task review; live participant-channel deployment remains optional unless explicit bounded test credentials are provided. The Whisper primary/optional alternate pass exposes a provisional transcription-quality agreement signal for `needs_review`; its legacy `icr_*` fields are not formal Research Spine inter-coder reliability.

## Frontend Surface

- `frontend/src/components/interviews/InterviewView.tsx`
- `frontend/src/components/interviews/AudioPlayer.tsx`
- `backend/app/core/transcription.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interviews/InterviewView.tsx` and the UI navigation path recorded in the inventory.
- Benchmark interview evidence should include uploaded transcript sources plus an approved interview-analysis task. Telegram/AURA live participant conversations are recorded as future improvement when no local simulator or channel credentials are available.
- `backend/app/core/transcription.py` compares at most the primary Whisper result and an optional alternate pass using heuristic keyword-category consensus. The result is explicitly marked `formal_reliability: false`, `research_spine_eligible: false`, and `validation_scope: transcription_quality_signal`.
- Formal Fleiss' Kappa/alpha is computed only after the transcript becomes source evidence units and three independent Research Spine coders rate the same units; transcription agreement cannot promote a transcript, nugget, fact, insight, recommendation, or report.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/real_user_benchmark/run.mjs`

## Related Features

- [interviews.files](../../interviews/files/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-121
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
