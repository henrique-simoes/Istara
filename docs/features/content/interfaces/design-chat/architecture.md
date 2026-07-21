---
stable_id: interfaces.design-chat
title: Interface Design Chat
ui_path: Interfaces > Design Chat
audience: architecture
status: documented
related_features: ["interfaces.generate", "interfaces.findings-picker"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/InterfacesView.tsx", "frontend/src/components/interfaces/DesignChatTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces.py"]
api_references: ["backend/app/api/routes/interfaces.py"]
test_references: ["tests/test_pi_replacement_candidate.py", "tests/pi_production/test_w1_agentic_contract.py"]
last_verified: 2026-07-21
compass: CF-SPEC-53 / CF-657
---

# Interface Design Chat Architecture

## Implementation Summary

Design Chat is the conversational starting point for generating, refining, and reasoning about interface concepts.

## Frontend Surface

- `frontend/src/components/interfaces/InterfacesView.tsx`
- `frontend/src/components/interfaces/DesignChatTab.tsx`
- `frontend/src/stores/interfacesStore.ts`
- `backend/app/api/routes/interfaces.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/InterfacesView.tsx` and the UI navigation path recorded in the inventory.
- Native-tool and text-fallback design-chat loops enter through `AgenticDispatcher`. Its legacy executor keeps project scope and design-tool authorization intact while forwarding native provider content into the existing SSE envelope as it arrives.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_pi_replacement_candidate.py`
- `tests/pi_production/test_w1_agentic_contract.py`

## Related Features

- [interfaces.generate](../../interfaces/generate/architecture.md)
- [interfaces.findings-picker](../../interfaces/findings-picker/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
