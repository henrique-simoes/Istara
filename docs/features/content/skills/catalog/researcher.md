---
stable_id: skills.catalog
title: Skills Catalog
ui_path: Skills > Catalog
audience: researcher
status: documented
related_features: ["skills.proposals", "agents.registry"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/skills/SkillsView.tsx", "backend/app/api/routes/skills.py", "backend/app/core/agent_skill_tools.py"]
api_references: ["backend/app/api/routes/skills.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Skills Catalog

## What It Does

The Skills catalog lists available capabilities agents can use or propose for research workflows.

## Why It Exists

Skills Catalog exists so the work represented by Skills > Catalog has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Skills > Catalog
- Navigation group: Skills
- Primary component: `SkillsView`

## How UX Researchers Use It

- Open Skills > Catalog from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with skills catalog in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Skills > Catalog when the current research task needs skills catalog.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: skills.proposals, agents.registry.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with skills catalog.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [skills.proposals](../../skills/proposals/researcher.md)
- [agents.registry](../../agents/registry/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/skills/SkillsView.tsx`, `backend/app/api/routes/skills.py`, `backend/app/core/agent_skill_tools.py`
- API references: `backend/app/api/routes/skills.py`
- Tests: none recorded
