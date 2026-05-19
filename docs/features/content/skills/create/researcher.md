---
stable_id: skills.create
title: Create Skill
ui_path: Skills > Create
audience: researcher
status: needs-verification
related_features: ["skills.catalog", "agents.create"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/skills/SkillsView.tsx", "backend/app/api/routes/skills.py"]
api_references: ["backend/app/api/routes/skills.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Create Skill

## What It Does

Create Skill supports adding or configuring a new skill surface from inside Istara.

## Why It Exists

Create Skill exists so the work represented by Skills > Create has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Skills > Create
- Navigation group: Skills
- Primary component: `SkillsView`

## How UX Researchers Use It

- Open Skills > Create from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with create skill in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Skills > Create when the current research task needs create skill.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Review autonomous creation proposals only for the active project before any generated skill can be approved.
- Move to related surfaces when needed: skills.catalog, agents.create.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with create skill.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Verify, approve, and reject actions require the proposal's source project to match the active project.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [skills.catalog](../../skills/catalog/researcher.md)
- [agents.create](../../agents/create/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/skills/SkillsView.tsx`, `backend/app/api/routes/skills.py`
- API references: `backend/app/api/routes/skills.py`
- Tests: none recorded
