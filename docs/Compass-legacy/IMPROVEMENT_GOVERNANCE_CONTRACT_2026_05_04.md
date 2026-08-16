# Improvement Governance Contract

Date: 2026-05-04

Purpose: make Memento-Skills, HyperAgents/DGM-H-inspired tuning, ReasoningBank, and Karpathy-style autoresearch operate as one visible, auditable, reversible improvement system across Istara.

## Contract

Every self-improving subsystem must describe proposed changes through a shared proposal ledger before the change becomes a durable product behavior.

The ledger is implemented by:

- `backend/app/models/improvement_governance.py`
- `backend/app/core/improvement_governance.py`
- `backend/app/api/routes/improvement_governance.py`
- `backend/app/models/dgmh_archive.py`
- `backend/app/core/dgmh_archive.py`
- `backend/app/api/routes/dgmh_archive.py`
- `frontend/src/lib/improvementGovernanceTypes.ts`
- `frontend/src/lib/dgmhArchiveTypes.ts`
- `frontend/src/lib/api.ts` export `improvementGovernance`
- `frontend/src/lib/api.ts` export `dgmhArchive`

Persistence:

- Alembic revision `008_improvement_governance`
- SQL table `improvement_proposals`
- Alembic revision `009_dgmh_archive`
- SQL table `dgmh_archive_variants`

API:

- `GET /api/improvement-governance/proposals`
- `GET /api/improvement-governance/proposals/{proposal_id}`
- `POST /api/improvement-governance/proposals`
- `POST /api/improvement-governance/proposals/{proposal_id}/approve`
- `POST /api/improvement-governance/proposals/{proposal_id}/apply`
- `POST /api/improvement-governance/proposals/{proposal_id}/reject`
- `POST /api/improvement-governance/proposals/{proposal_id}/revert`
- `POST /api/improvement-governance/proposals/{proposal_id}/quarantine`
- `POST /api/improvement-governance/proposals/{proposal_id}/evaluation`
- `GET /api/improvement-governance/summary`
- `GET /api/improvement-governance/feature-contract`
- `GET /api/dgmh-archive/variants`
- `POST /api/dgmh-archive/variants`
- `GET /api/dgmh-archive/variants/{variant_id}`
- `GET /api/dgmh-archive/variants/{variant_id}/lineage`
- `POST /api/dgmh-archive/variants/{variant_id}/evaluation`
- `POST /api/dgmh-archive/variants/{variant_id}/approve`
- `POST /api/dgmh-archive/variants/{variant_id}/apply`
- `POST /api/dgmh-archive/variants/{variant_id}/confirm`
- `POST /api/dgmh-archive/variants/{variant_id}/revert`
- `POST /api/dgmh-archive/variants/{variant_id}/quarantine`
- `GET /api/dgmh-archive/select-parent`
- `GET /api/dgmh-archive/summary`

All routes are admin-only because proposals can expose prompts, runtime configuration, model behavior, integrations, and security-sensitive evidence.

## Approval Policy

Automatic:

- `memory`
- `telemetry`
- `evaluation`
- `documentation`

These are allowed to auto-apply only when risk is low. This lets ReasoningBank and telemetry learn continuously without forcing non-technical users to review every trace.

Human approval required:

- `prompts`
- `configs`
- `skills`
- `agents`
- `ui`
- `orchestration`

Admin approval required:

- `backend_code`
- `integrations`
- `mcp`
- `compute`
- `security`
- `connection_strings`

This means production self-evolution can exist for end users, but behavior changes still move through visible approve/apply/revert states.

## Producer Integrations

ReasoningBank:

- Safe reasoning memories continue to be recorded automatically.
- Memory and telemetry changes classify as low-risk auto-applied proposals when explicitly created through governance.
- Future UI work should expose memory edit/quarantine actions through the same proposal model.

Karpathy-style autoresearch:

- Kept experiments now register governance proposals through `AutoresearchEngine._register_improvement_proposals()`.
- Reverted experiments remain ReasoningBank caution memories rather than promotions.
- The governance proposal stores baseline score, candidate score, delta, score samples, uncertainty metadata, mutation description, and rollback strategy.
- Compute-affecting loops such as `model_temp` are admin-required because they can affect hardware use and pooled model routing.

HyperAgent / DGM-H archive evolution:

- Newly generated Meta-Hyperagent parameter proposals are mirrored into governance.
- Existing approval, reject, and revert UI actions now sync governance status.
- Every governance proposal now creates or reuses a DGM-H archive variant with lineage, mutation surface, artifact kind, metrics, evidence, rollback plan, and ReasoningBank trace ids.
- Parent selection uses a UCB-style score so archive evolution can balance measured performance and exploration.
- Variant state tracks candidate, approved, active, confirmed, reverted, failed, archived, and quarantined lifecycles.

Memento-Skills:

- Memento routing and task execution already write success/failure traces into ReasoningBank.
- Agent creation, skill update, skill creation, and self-evolution promotion paths now emit governance proposals and DGM-H archive variants for durable prompt, skill, or agent mutations.

Producer evidence hooks:

- Audio transcription background processing records language detection, confidence, ICR, tags, document ids, and failure evidence.
- Channel inbound processing records WhatsApp/Telegram-style persistence and deployment routing evidence.
- MCP server/client actions record toggle, policy, registration, discovery, and tool-call evidence without exposing secrets.
- Adaptive validation records ensemble/orchestration method outcomes with consensus score and success signals.
- Connection-string generation, compute donation strings, redemption, and network-token rotation record hashed-storage and revocation evidence.

## Feature Evidence Matrix

The feature contract returned by `/api/improvement-governance/feature-contract` covers:

- interviews audio upload, transcription, tagging, and document creation
- Memento skills and automatic agent creation
- HyperAgent meta tuning
- DGM-H archive evolution
- autoresearch
- ReasoningBank
- MCP and Aura-style integrations
- WhatsApp and Telegram channels
- ensemble model and LLM orchestration
- pooled compute connection strings
- desktop tray installation and lifecycle
- all menus and submenus

Each feature declares required evidence such as baseline metrics, language detection results, webhook validation, rollback paths, model eligibility, hardware telemetry, API contract coverage, and UI state checks.

## Verification

Added tests:

- `tests/test_improvement_governance.py`
- `tests/test_dgmh_archive.py`
- updated `tests/test_autoresearch.py`

Focused verification command:

```bash
pytest tests/test_dgmh_archive.py tests/test_improvement_governance.py tests/test_autoresearch.py tests/test_meta_hyperagent.py tests/test_reasoning_bank.py -q
```

Expected result for this slice: DGM-H archive, governance, autoresearch, meta-hyperagent, and ReasoningBank tests pass together.

## Remaining Work

The central contract is now present, but full paper-faithful implementation still needs:

- UI panels for governance proposals, ReasoningBank memory edit/quarantine, and visual impact tracking.
- Runner-specific autoresearch apply/revert adapters instead of generic rollback descriptions.
- Desktop tray and installation dependency checks reported into the feature contract.
- Deeper child-agent sandbox evaluation loops for generated backend/UI/code mutations before they are proposed for user approval.
