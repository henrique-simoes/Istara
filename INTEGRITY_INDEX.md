# Istara Development Docs Index

**Status**: Secondary navigation doc
**Authority**: Do not start here. Start with `AGENT_ENTRYPOINT.md`.

This file exists to help humans and agents navigate the documentation landscape without confusing historical/supporting docs for the live development system.

## Canonical Start

If you are changing Istara, start here:

1. `AGENT_ENTRYPOINT.md`
2. `SYSTEM_PROMPT.md`
3. `AGENT.md`
4. `COMPLETE_SYSTEM.md`
5. `SYSTEM_CHANGE_MATRIX.md`
6. `CHANGE_CHECKLIST.md`
7. `SYSTEM_INTEGRITY_GUIDE.md` and `Tech.md` when deeper detail is needed

## Current Development Authority

### Primary docs

- `AGENT_ENTRYPOINT.md`
  Canonical first document for humans and agents.
- `SYSTEM_PROMPT.md`
  Repo-wide doctrine and non-negotiable rules.
- `SYSTEM_CHANGE_MATRIX.md`
  Change-impact map: if X changes, what else must move.
- `CHANGE_CHECKLIST.md`
  Execution checklist for safe implementation and release work.
- `AGENT.md`
  Generated fast inventory of the current system.
- `COMPLETE_SYSTEM.md`
  Generated broader architecture and coverage map.
- `SYSTEM_INTEGRITY_GUIDE.md`
  Deep reference manual.
- `Tech.md`
  Narrative technical explanation of the live system.

### Supporting docs

- `CLAUDE.md`
- `GEMINI.md`
- `CONTRIBUTING.md`
- `README.md`
- `README.pt-BR.md`

### Historical/supporting docs

- `INVESTIGATION_SUMMARY.md`
  Historical investigation snapshot, not live authority.
- `docs/AUDIT-REPORT.md`
  Dated audit report, not live authority.
- `docs/ARCHITECTURE_EVOLUTION.md`
  Architecture history, not live authority.
- `docs/AGENTIC-ARCHITECTURE.md`
  Specialized pipeline deep dive, not canonical system authority.

## Task-Based Navigation

### I am making a code change

Read:

1. `AGENT_ENTRYPOINT.md`
2. `SYSTEM_CHANGE_MATRIX.md`
3. `CHANGE_CHECKLIST.md`
4. `AGENT.md` and `COMPLETE_SYSTEM.md`

### I am reviewing a PR

Read:

1. `AGENT_ENTRYPOINT.md`
2. `SYSTEM_CHANGE_MATRIX.md`
3. `CHANGE_CHECKLIST.md`
4. `Tech.md`

### I need deeper architecture detail

Read:

1. `COMPLETE_SYSTEM.md`
2. `SYSTEM_INTEGRITY_GUIDE.md`
3. `Tech.md`

### I need historical context

Read:

1. `INVESTIGATION_SUMMARY.md`
2. `docs/AUDIT-REPORT.md`
3. `docs/ARCHITECTURE_EVOLUTION.md`

## Rule of Thumb

If documents ever conflict:

1. code is the source of truth
2. generated docs (`AGENT.md`, `COMPLETE_SYSTEM.md`) come next
3. prompt/checklist/matrix docs define process and governance
4. historical reports are context only
