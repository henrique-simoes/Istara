# Agentic Papers Implementation Audit

Date: 2026-05-04

Scope: audit Istara's implementation of Memento-Skills, HyperAgents / DGM-H, and Karpathy-style autoresearch; assess system integration; define how ReasoningBank should be implemented to improve orchestration, self-evolution, and production hardening.

Inputs:

- `Hyper-agents.pdf` - Zhang et al. (2026), "HyperAgents", arXiv:2603.19461.
- `Memento-agents.pdf` - Zhou et al. (2026), "Memento-Skills: Let Agents Design Agents", arXiv:2603.18743.
- `Reasoning_Bank.pdf` - Ouyang et al. (2026), "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory", arXiv:2509.25140.
- Karpathy autoresearch reference: https://github.com/karpathy/autoresearch.
- Compass Forge: snapshot 40, impact map focused on agent runtime, `meta_hyperagent`, autoresearch routes/runners, skills, MCP/API surfaces, and frontend API/type drift. Before gate recorded `warn` with no new failures.

## Executive Verdict

Istara has meaningful production scaffolding inspired by all three existing ideas, but the current code is not a faithful implementation of Memento-Skills or HyperAgents. It is closer to a guarded, local-first self-improvement platform with:

- skill and agent creation proposals inspired by Memento,
- bounded parameter-tuning proposals inspired by HyperAgents,
- greedy autoresearch loops inspired by Karpathy's small-loop pattern.

That framing is healthy for production safety. The risky part is that README and architecture language can overstate paper fidelity. The system should either narrow the claims or implement the missing mechanisms.

Highest priority findings:

1. Memento router path is broken: `backend/app/core/agent.py` returns `None` before semantic skill matching runs, so the behavior-aligned read step is effectively keyword-only.
2. HyperAgent meta-tuning contains dead knobs: `agent_factory.coverage_threshold` can be changed by `meta_hyperagent`, but `AgentFactory.detect_capability_gap()` still hardcodes `0.6`.
3. HyperAgents are not actually implemented as DGM-H: there is no archive of variants, parent selection, self-modifying meta agent, empirical child-agent evaluation loop, or transfer/evolution record.
4. Autoresearch has the right hypothesize/mutate/evaluate/revert skeleton, but several runners rely on LLM-as-judge self-scoring, no held-out gold set, inconsistent persistence, and no isolated worktree/sandbox for source-file mutation.
5. ReasoningBank is highly applicable to Istara. It should be implemented as a cross-agent reasoning-memory layer that distills successful and failed trajectories into structured, retrievable strategy memories, then feeds those memories into tasks, skill routing, autoresearch, meta-agent proposal generation, MCP/browser work, and interview/transcription workflows.

## Paper Mechanism Summary

### Memento-Skills

Core mechanism:

- The agent maintains reusable skills as external writable memory.
- Every interaction follows an Observe -> Read -> Act -> Feedback -> Write loop.
- Read: a behavior-aligned skill router selects a skill conditioned on current task and accumulated memory.
- Act: selected skill executes a multi-step workflow.
- Feedback: a judge evaluates outcome and trace.
- Write: failure attribution updates a target skill, adds generalizable tips, or creates a new skill when coverage is missing.
- Mutations are gated by synthetic tests and judge checks before promotion.

Production implication for Istara:

Memento is not only "agents create agents." It is a read/write policy iteration loop over skill artifacts, router behavior, trace feedback, utility, and verification gates.

### HyperAgents / DGM-H

Core mechanism:

- A hyperagent combines task agent and meta agent into one editable program.
- The meta-level improvement procedure is also editable, enabling metacognitive self-modification.
- DGM-H keeps an archive of scored agent variants.
- Each iteration selects parents, lets them generate modified children, evaluates children on tasks, validates them, and adds valid children to the archive.
- Open-ended exploration and meta-agent self-improvement are both central; ablations without either are weaker.
- Safety constraints matter: sandboxing, predefined tasks and metrics, resource limits, and human oversight.

Production implication for Istara:

A bounded meta-tuner is safer than DGM-H, but it is not equivalent to DGM-H unless it has a variant archive, evaluated child agents, modifiable improvement mechanism, and a scored selection process.

### Karpathy Autoresearch

Core mechanism from the reference implementation:

- A small, controlled loop mutates one scoped target, runs a fixed-budget experiment, measures a single comparable metric, keeps or discards the change, logs the experiment, and repeats.
- The original uses a tightly constrained editable surface (`train.py`), fixed wall-clock budget, one metric (`val_bpb`), and simple reproducible setup.

Production implication for Istara:

Istara's adaptation is sensible because UX research optimization is not single-GPU nanochat training. But it must preserve the invariants that make autoresearch rigorous: scoped mutation, fixed budget, comparable metrics, holdouts, rollback, and non-polluting logs.

### ReasoningBank

Core mechanism:

- Agents process a stream of tasks without ground-truth feedback during test time.
- After each task, an LLM-as-judge or proxy correctness signal labels the trajectory.
- Successful and failed trajectories are distilled into structured memory items: title, description, content.
- New tasks retrieve relevant memories and inject them into the system instruction.
- Memory-aware test-time scaling (MaTTS) allocates extra compute to produce contrastive trajectories, then uses parallel self-contrast or sequential self-refinement to curate better memories.

Production implication for Istara:

ReasoningBank is the missing middle between Istara's local memory files, skill usage stats, and autoresearch logs. It can turn failures, kept experiments, reverted experiments, MCP tool traces, transcription/import outcomes, and agent collaborations into reusable strategy memory.

## Implementation Map

### Memento-Adjacent Code

Files:

- `backend/app/core/agent_factory.py`
- `backend/app/core/agent.py`
- `backend/app/core/self_evolution.py`
- `backend/app/core/agent_learning.py`
- `backend/app/skills/skill_manager.py`
- `backend/app/api/routes/agents.py`
- `backend/app/api/routes/skills.py`
- `backend/app/agents/orchestrator.py`

What is implemented:

- Runtime skill overlays under `settings.runtime_skills_dir`.
- Runtime persona overlays under `settings.runtime_personas_dir`.
- Skill usage stats and utility scores.
- Skill improvement proposals and creation proposals.
- Agent creation proposals when routing falls back to `istara-main`.
- Persona self-evolution from structured learnings into `CORE.md`, `SKILLS.md`, `PROTOCOLS.md`, and `MEMORY.md`.
- Admin approval routes for skill creation, agent creation, and self-evolution promotion.
- ContentGuard scan for proposed skill prompts.
- Verification gate for proposed skills using a synthetic execution.

Key gaps:

- `backend/app/core/agent.py:1419` returns before semantic skill matching; the fallback at lines 1421-1427 is unreachable.
- Skill routing is keyword plus a broken semantic fallback, not a behavior-aligned router trained with positives and hard negatives.
- There is no explicit `TipMemory` equivalent or task-conditioned reusable strategy memory.
- Skill creation from `agent.py` is triggered by successful/high-finding tasks, not by failure attribution against missing or bad skills.
- `AgentFactory.propose_agent_creation()` uses static templates and fixed `confidence=65`; it does not synthesize protocols, skills, evaluation tasks, or domain-specific acceptance criteria.
- `approve_proposal()` in `agents.py` does not use `proposed_core_md` as the authoritative scaffold; it creates generic persona files from the system prompt.
- Post-approval agent scaffolding, worker start, and websocket broadcast still swallow failures, so a proposal can look fully approved while the runtime worker did not start.

Soundness verdict:

Partial implementation. Istara has the artifact lifecycle and human approval model, but it lacks the central Read/Write router-learning and trace-driven update loop. Fixing the unreachable semantic router is a release-grade bug. Adding ReasoningBank would supply the missing memory substrate.

### HyperAgents-Adjacent Code

Files:

- `backend/app/core/meta_hyperagent.py`
- `backend/app/api/routes/meta_hyperagent.py`
- `frontend/src/components/meta/MetaHyperagentView.tsx`
- `tests/test_meta_hyperagent.py`

What is implemented:

- Optional admin-controlled background observation loop.
- Observes task routing, self-evolution thresholds, skill usage, verification stats, and agent proposals.
- Generates bounded parameter proposals from simple rules.
- Requires explicit admin approval before applying variants.
- Limits active variants to 3.
- Persists confirmed overrides to disk and reapplies them at startup.
- Supports revert and confirm actions.

Key gaps:

- This is a rule-based meta-tuner, not DGM-H.
- No scored archive of agent variants.
- No probabilistic parent selection or open-ended exploration.
- No child-agent generation loop.
- No evaluation tasks for each candidate variant.
- No self-modification of the meta-agent logic.
- `metrics_before` and `metrics_after` exist on `MetaVariant` but are not populated or used to recommend confirm/revert.
- Rule 2 proposes lowering self-evolution `min_occurrences` simply because the threshold is above 2, not because observed promotion rate is low.
- `agent_factory.coverage_threshold` is applied to a module attribute but not read by `AgentFactory.detect_capability_gap()`, which still hardcodes `0.6`.
- The skill similarity threshold override is undermined by the unreachable semantic fallback in `agent.py`.

Soundness verdict:

Production-safe as a bounded meta-parameter assistant. Not a sound HyperAgents / DGM-H implementation. README wording should call it "inspired by HyperAgents" or the implementation should grow an archive/evaluation layer.

### Autoresearch Code

Files:

- `backend/app/core/autoresearch_engine.py`
- `backend/app/core/autoresearch_isolation.py`
- `backend/app/core/autoresearch_rate_limiter.py`
- `backend/app/core/autoresearch_runners/*`
- `backend/app/api/routes/autoresearch.py`
- `backend/app/models/autoresearch_experiment.py`
- `tests/test_autoresearch.py`

What is implemented:

- The core loop measures baseline, hypothesizes, mutates, measures, keeps/reverts, persists the experiment, and broadcasts progress.
- Autoresearch is disabled by default and admin-gated.
- Background start/stop routes exist.
- Daily and per-target rate limiting exists.
- ContextVar isolation avoids polluting production agent learning and skill usage stats.
- Persona locks avoid collisions between persona autoresearch and self-evolution.
- Keep rule has `min_delta` and an optional 95 percent CI guard when repeated measurement is enabled.
- Runners cover skill prompts, UI simulation, RAG params, persona files, question banks, and model/temperature search.

Key gaps:

- `autoresearch_measurement_repeats` defaults to 1, so the CI guard is normally inactive.
- No paired-control measurement; candidate scores are compared to historical `best_score`, not a simultaneously remeasured baseline under the same noise conditions.
- Skill and model runners depend on LLM-as-judge scores without a fixed holdout corpus or human-calibrated rubric.
- UI runner writes directly to the requested file path with no allowlist, isolated worktree, compile/test gate, or crash-safe rollback.
- Question-bank and persona runners use synthetic participants and synthetic scoring only.
- RAG params are mutated in memory; kept changes are not clearly persisted to durable config.
- Skill prompt, persona, question bank, and UI runners have different persistence/rollback semantics.
- Start route validates loop type but not that target paths/entities are in allowed project scope.

Soundness verdict:

The architectural loop is sound and much improved versus a naive auto-edit loop, especially with isolation and CI/min-delta checks. Statistical rigor and mutation isolation are still below production-hardening level for autonomous code/config mutation.

## ReasoningBank Integration Blueprint

### Data Model

Add a durable reasoning memory model:

- `ReasoningMemoryItem`
- Fields:
  - `id`
  - `project_id`
  - `agent_id`
  - `source_kind`: `task`, `skill`, `autoresearch`, `mcp`, `interview`, `transcription`, `channel`, `meta_variant`
  - `source_id`
  - `outcome`: `success`, `failure`, `mixed`, `unknown`
  - `title`
  - `description`
  - `content`
  - `tags`
  - `domain`
  - `evidence_refs`
  - `judge_score`
  - `confidence`
  - `embedding`
  - `created_at`
  - `updated_at`
  - `expires_at`
  - `status`: `candidate`, `active`, `merged`, `rejected`, `quarantined`

Store only distilled strategies by default. Raw trajectories should remain linked evidence with redaction and retention controls.

### Retrieval Path

Inject ReasoningBank memories in four places:

1. Task routing: augment `route_task()` and `AgentOrchestrator._select_skill()` with top-k strategy memories for task text and detected specialties.
2. Skill execution: pass relevant memory items into `SkillInput.user_context` or a dedicated `reasoning_memory` field.
3. Persona prompt composition: `prompt_rag.compose_dynamic_prompt()` should retrieve both persona sections and ReasoningBank items.
4. MCP/browser/tool actions: tool selection and step planning should retrieve memories about prior tool failures, auth quirks, rate limits, selectors, and recovery strategies.

### Extraction Path

Create a `ReasoningMemoryService` that consumes:

- completed tasks,
- failed task traces,
- skill validation results,
- autoresearch kept and reverted experiments,
- meta-hyperagent applied/reverted variants,
- transcription/import failures,
- MCP client call failures,
- channel inbound failures,
- browser/UI audit traces.

For each trace:

- judge outcome with domain-specific proxy checks,
- extract 1-3 candidate memory items,
- mark whether each item came from success or failure,
- redact secrets/PII,
- deduplicate against existing memory,
- write as `candidate` or `active` based on confidence.

### Consolidation

Run a scheduled consolidation loop:

- merge near-duplicate memories,
- demote stale or contradicted memories,
- preserve project boundaries,
- require admin approval for global memories,
- track which memories improved future outcomes.

This is where ReasoningBank can outperform raw persona append-only memory. The memory item is small, scoped, and evaluable.

### Memory-Aware Test-Time Scaling

Add MaTTS modes to high-impact flows:

- `parallel`: run k independent attempts for the same task with different models/prompts, compare success/failure traces, distill robust memories.
- `sequential`: run a self-refinement pass after an attempt, capture the correction trail, distill what changed.

Use compute budgets:

- default k=1 for normal work,
- k=3 for failed or high-value tasks,
- k=5 only for explicit admin/autoresearch runs,
- integrate with `compute_registry` queue/load and strict routing.

### Where It Improves Istara Immediately

1. Memento router: replaces the unreachable/static semantic router with behavior-grounded retrieval from previous outcomes.
2. Autoresearch: converts kept and reverted experiments into strategy memory, not just database rows.
3. Meta-hyperagent: proposals can cite actual memory-backed failure modes and observed variant deltas.
4. Interviews/transcription: failed language detection, bad diarization, missing ffmpeg/Whisper dependencies, and tagging mistakes become reusable install/runtime memories.
5. MCP/integrations: repeated connection/auth/tool schema failures become tool-selection and recovery memories.
6. Ensemble validation: successful disagreement-resolution patterns can be stored and retrieved for similar analyses.

## Priority Fix Plan

### P0 - Correct Broken Claimed Behavior

1. Move semantic skill matching before the early `return None` in `AgentOrchestrator._select_skill()`.
2. Wire `_META_SKILL_SIMILARITY_THRESHOLD` into `_semantic_skill_match()`.
3. Wire `_META_COVERAGE_THRESHOLD` into `AgentFactory.detect_capability_gap()`.
4. Add unit tests proving semantic fallback runs and threshold overrides affect behavior.
5. Add unit tests proving `agent_factory.coverage_threshold` variants change gap detection.

### P1 - Harden Autoresearch Before Production Autonomy

1. Add target validation:
   - UI runner may only edit allowlisted frontend component paths.
   - Persona runner may only edit runtime persona overlays.
   - Question-bank runner must verify deployment/project ownership.
2. Run candidates in an isolated worktree or temp overlay with explicit apply/commit/rollback.
3. Require syntax/build checks for UI edits before keep.
4. Add fixed evaluation corpora per runner.
5. Raise production default `autoresearch_measurement_repeats` to at least 3 for autonomous keep decisions, or require manual review when repeats=1.
6. Persist kept RAG parameter changes through the settings persistence path, or label them as session-only.

### P2 - Upgrade Memento Fidelity

1. Create a behavior-aligned router evaluation dataset from task/skill outcomes.
2. Add hard-negative skill-router tests.
3. Make skill creation failure-driven, not only success-driven.
4. Include `proposed_core_md`, proposed protocols, and proposed skill ACLs in approved agent scaffolding.
5. Replace fixed confidence with evidence-based confidence from coverage, traces, and verification.

### P3 - Upgrade HyperAgents Fidelity Safely

1. Reframe `meta_hyperagent` as "bounded meta-tuner" in docs until archive/evaluation exists.
2. Add `MetaEvaluationRun` records for each variant with metrics before/after.
3. Auto-populate `metrics_before` and `metrics_after`.
4. Require variant confirm only after observation-window evidence or explicit admin override.
5. Add an archive table for parameter/persona/prompt variants and parent links.
6. Add UCB-style parent selection only inside a sandboxed autoresearch profile, not production default.

### P4 - Implement ReasoningBank

1. Add backend models and migration for `reasoning_memory_items`.
2. Add `ReasoningMemoryService` with retrieval, extraction, and consolidation.
3. Add redaction and cross-project isolation tests.
4. Integrate retrieval into task routing, prompt composition, skill execution, autoresearch, and MCP/browser tooling.
5. Add UI panels for memory provenance, approval, quarantine, and quality impact.
6. Add MaTTS budget controls tied to compute pool load and admin settings.

### Implementation Update - 2026-05-04

Implemented in this slice:

- Added `ReasoningMemoryItem`, Alembic revision `007_reasoning_memory_items`, `ReasoningMemoryService`, and admin routes under `/api/reasoning-bank/*`.
- Added deterministic trace extraction, secret redaction, project-scoped retrieval, duplicate consolidation, summary metrics, and frontend API/types.
- Repaired the Memento semantic router by removing the unreachable early return in `AgentOrchestrator._select_skill()`.
- Connected Memento task execution to ReasoningBank, including successful verified outputs, failed verification, and skill exceptions.
- Made HyperAgent `agent_factory.coverage_threshold` variants operational by replacing the hardcoded `0.6` in `AgentFactory.detect_capability_gap()`.
- Connected Karpathy-style autoresearch experiments to ReasoningBank so kept and reverted iterations become reusable strategy or caution memories.
- Added ReasoningBank summary to `MetaHyperagent.observe_cycle()` and `/api/meta-hyperagent/status`.
- Added the Improvement Governance contract: `ImprovementProposal`, Alembic revision `008_improvement_governance`, `ImprovementGovernanceService`, admin routes under `/api/improvement-governance/*`, and frontend API/types.
- Wired kept autoresearch experiments into governance proposals with baseline/candidate metrics, uncertainty metadata, ReasoningBank memory ids, affected surfaces, and rollback plans.
- Wired Meta-Hyperagent proposal generation plus approve/reject/revert UI actions into the same governance ledger.
- Added the feature evidence matrix covering interviews/transcription, Memento skills, agent creation, HyperAgent tuning, autoresearch, ReasoningBank, MCP/Aura-style integrations, WhatsApp/Telegram, ensemble LLM orchestration, pooled compute connection strings, desktop tray, and all menus/submenus.
- Added the DGM-H archive: `DGMHArchiveVariant`, Alembic revision `009_dgmh_archive`, `DGMHArchiveService`, admin routes under `/api/dgmh-archive/*`, and frontend API/types.
- Governance proposals now automatically create archive variants with lineage, parent/root ids, mutation surface, artifact kind, rollback plan, metrics, evidence, UCB-style parent selection scores, and ReasoningBank trace ids.
- Added producer evidence hooks for transcription/document creation, Memento agent creation, skill updates, skill creation, self-evolution promotions, MCP server/client operations, channel inbound routing, adaptive validation, and connection-string generation/redemption/rotation.

Still intentionally not overclaimed:

- DGM-H archive evolution is now first-class, but deep child-agent sandbox evaluation for arbitrary backend/UI/code mutations remains follow-up hardening before code self-modification can be considered paper-complete.
- ReasoningBank currently uses deterministic extraction and lexical retrieval. Vector retrieval, LLM-assisted memory refinement, quarantine/approval UX, and compute-aware MaTTS scheduling remain follow-up hardening.
- Governance now defines the system-wide contract, but UI panels and runner-specific apply/revert adapters remain follow-up work.

## Test Plan

Targeted tests to add:

- `tests/test_agent_skill_routing.py`
  - semantic fallback executes when keyword match fails,
  - meta threshold override changes match/no-match behavior,
  - no embedding crash leaks into task execution.
- `tests/test_agent_factory.py`
  - coverage threshold override changes gap detection,
  - invalid JSON specialties do not crash detection,
  - approval uses proposed persona content or returns partial-failure diagnostics.
- `tests/test_meta_hyperagent.py`
  - proposals require real observed evidence,
  - variant stores metrics before/after,
  - confirm without observation evidence is blocked unless override flag is set.
- `tests/test_autoresearch_hardening.py`
  - UI runner rejects paths outside allowlist,
  - failed candidate reverts even if measurement fails,
  - RAG kept config is persisted or explicitly reported session-only,
  - repeats=1 cannot auto-keep in production mode.
- `tests/test_reasoning_memory.py`
  - success and failure traces extract structured memory items,
  - PII/secrets redaction,
  - retrieval respects project boundaries,
  - consolidation merges duplicates and preserves evidence refs.
- `tests/test_improvement_governance.py`
  - auto-apply policy is limited to low-risk learning/telemetry,
  - behavioral, compute, integration, and code changes require approval/admin review,
  - proposals preserve evidence, metrics, rollback, quarantine, and revert state,
  - autoresearch and HyperAgent proposals enter the shared ledger.
- `tests/test_dgmh_archive.py`
  - governance proposals create and sync DGM-H variants,
  - UCB-style parent selection is deterministic under measured scores,
  - archive API approval/apply/list/summary routes require admin access.
- `tests/test_reasoning_bank_integration.py`
  - task routing receives relevant memories,
  - skill execution prompt includes bounded memory context,
  - autoresearch kept/reverted experiments produce memory candidates.

Broader verification:

- `pytest tests/test_agents.py tests/test_autoresearch.py tests/test_meta_hyperagent.py tests/test_skills.py tests/test_mcp.py tests/test_compute.py -q`
- `python -m compileall -q backend/app`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
- `compass-forge gate after --task CF-91 --report-format json`

## Documentation Updates Needed

README references should include ReasoningBank in both English and Portuguese READMEs:

- Ouyang et al. (2026), "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory", arXiv:2509.25140.

Architecture docs now describe ReasoningBank as implemented for the first production slice, with remaining scope called out separately so paper fidelity is not overstated.

## Bottom Line

Istara is on a good path, but the production posture should be precise:

- Memento: partial but improved, with semantic routing repaired and a first behavior-aligned ReasoningBank write loop in place.
- HyperAgents: now implemented as a bounded meta-tuner plus a first-class governed DGM-H archive with lineage, selection, evaluation, rollback, and ReasoningBank traces.
- Autoresearch: structurally present, but needs better statistical rigor, scoped mutation, target validation, and runner-specific evaluation harnesses.
- ReasoningBank: now acts as the first shared memory layer that lets Memento-style skill evolution, HyperAgent-style meta observation, and autoresearch loops compound rather than operate as separate subsystems.
- Improvement Governance and DGM-H Archive: now provide the system-wide production contract for approval, evidence, lineage, rollback, and feature coverage across these subsystems.
