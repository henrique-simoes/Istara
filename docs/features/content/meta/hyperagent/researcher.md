---
stable_id: meta.hyperagent
title: Meta-Agent
ui_path: Meta-Agent
audience: researcher
status: documented
related_features: ["settings.governed-evolution", "agents.registry"]
related_glossary: ["a2a", "compass-forge"]
code_references: ["frontend/src/components/meta/MetaHyperagentView.tsx", "backend/app/api/routes/meta_hyperagent.py", "backend/app/core/meta_hyperagent.py", "backend/app/skills/skill_usage.py"]
api_references: ["backend/app/api/routes/meta_hyperagent.py"]
test_references: ["tests/test_meta_hyperagent.py", "tests/test_project_scope_contracts.py", "tests/test_security_benchmark.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Meta-Agent

## What It Does

The Meta-Agent surface exposes the meta-hyperagent system for inspecting or governing higher-level agentic improvement behavior for the active project.

## Why It Exists

Meta-Agent exists so the work represented by Meta-Agent has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Meta-Agent
- Navigation group: Secondary
- Primary component: `MetaHyperagentView`

## How UX Researchers Use It

- Open Meta-Agent from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with meta-agent in the active project context; no proposal, variant, or observation list is loaded without an active project.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Meta-Agent when the current research task needs meta-agent.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.governed-evolution, agents.registry.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped observations, proposals, variants, and review actions associated with meta-agent.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Meta-Hyperagent state is not a global project feed. If a project has no observations or proposals, it should render empty even when other projects have active history.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.governed-evolution](../../settings/governed-evolution/researcher.md)
- [agents.registry](../../agents/registry/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/meta/MetaHyperagentView.tsx`, `backend/app/api/routes/meta_hyperagent.py`, `backend/app/core/meta_hyperagent.py`, `backend/app/skills/skill_usage.py`
- API references: `backend/app/api/routes/meta_hyperagent.py`
- Tests: `tests/test_meta_hyperagent.py`, `tests/test_project_scope_contracts.py`, `tests/test_security_benchmark.py`
