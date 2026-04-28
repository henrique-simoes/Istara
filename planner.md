# System Directive: Code Change Planning, Archiving & Review Workflow

**Planner version:** `2026-04-22.1`

**Objective:** This document defines the strict protocol for generating, evaluating, executing, reviewing, correcting, and archiving code change plans. All agents must follow it to preserve architectural integrity across `current_plans.md` and `old_plans.md` and to stay aligned with the Compass staging-first workflow.

**Authority order when rules conflict:**
1. The newest explicit user instruction
2. Compass and repo governance docs
3. This planner
4. Archived plan history

**Role rule:** An agent must act only in the phase implied by the current markers in `current_plans.md`. If the markers do not support the phase, the agent must not improvise a later phase.

**Branch rule:** Branch state is part of plan state. Agents must confirm the current branch, the intended base branch, and any known overlapping branches before acting on a non-trivial change.

**Role selection rule:** An agent must read both `planner.md` and the current plan's branch context before deciding its role.

## File Definitions
* **`current_plans.md`**: The active workspace. Holds draft proposals, the final verdict, execution status, and the review report.
* **`old_plans.md`**: The historical ledger. Permanent archive of all finalized, reviewed, and approved plans.

## Branch Protocol

1. Feature work starts from `staging` unless the newest explicit user instruction says otherwise.
2. `main` is not a working base branch.
3. Every plan must identify:
   - the current branch
   - the intended base branch
   - any overlapping active branches that matter for merge safety
4. If the branch is stale, misbased, or unexpectedly divergent, the agent must stop and report that before changing code.
5. If another active branch touches the same surface, the planner must note the overlap in `current_plans.md` before execution begins.
6. Archival notes should preserve branch provenance when the plan is written to `old_plans.md`.
7. A branch that is materially behind `main` is presumed stale unless the plan proves otherwise with a specific, bounded reason to keep it alive.
8. Stale branches must not be merged to `main` wholesale. They may only contribute by cherry-pick, rebase, or targeted extraction after explicit review.
9. A branch may be promoted to a `main` PR only when its changes are novel, current, and compatible with the present base.

### Deprecated Branches (DO NOT MERGE)

As of 2026-04-28, the following local branches exist but are **presumed stale and must not be merged into `main` or `staging` without explicit user approval**:

- `codex/main-stabilization-security-transcription` — already merged; 9 commits behind `main`
- `feat/beta-browser-evaluation` — 124 commits behind `main`
- `feat/high-quality-uxr-finetuning-datasets` — **MERGED into `main` on 2026-04-28**
- `feat/skill-methodology-audit` — 47 commits behind `main`
- `feat/system-audit-and-integration-check` — 46 commits behind `main`
- `feat/voice-transcription` — 124 commits behind `main`
- `fix-ci-validation` — 124 commits behind `main`
- `review/p0-infra` — 124 commits behind `main`
- `review/p1-steering` — 124 commits behind `main`
- `review/p2-testing` — 103 commits behind `main`
- `review/p3-observability` — 124 commits behind `main`
- `review/phase-zeta-context-mastery` — 103 commits behind `main`

**Agent rule:** If any plan references one of these branches as a merge candidate, the agent must STOP and ask the user for explicit confirmation before proceeding. These branches are salvage-only (cherry-pick or targeted extraction) and must be treated as historical artifacts, not integration paths.

## PR Reliability Rules

1. Open a PR to `main` only from a branch that has been checked against the current base branch and overlap set.
2. Before opening the PR, confirm:
   - branch divergence from `main` and `staging`
   - the exact files touched
   - whether the branch contains new code or only stale overlap
   - that required tests and docs sync have passed
3. If a branch is stale, do not open a `main` PR. Create a fresh branch from `staging` or `main` and transplant only the relevant work.
4. If a branch is a merge candidate for `main`, the PR description must state why the work is still current and what overlap risks were checked.
5. A PR to `main` must not be treated as a cleanup step for an unclear branch. It is the last step after the branch has already been proven fit for merge.

## Branch Context Requirement

Every active plan in `current_plans.md` must declare:

- Current branch
- Intended base branch
- Known overlapping branches
- Merge-risk level

If any of those fields are missing, stale, or inconsistent with the repository state, the agent must stop and correct the plan before proceeding.

If the branch context changes during work, the plan must be updated before any later phase is attempted.

## Workflow States

The plan file should move through these states in order:
1. Proposal state: one or more `plan:::` blocks, no `verdict:::` yet.
2. Verdict state: one `verdict:::` block, no `completion:::` yet.
3. Execution state: one `completion:::` block, no `review:::` yet.
4. Review state: one `review:::` block, then archive.
5. Correction state: one `correction:::` block, used only when Phase 4 or a later checker finds a real issue that must be fixed before archiving.

If the file is in the wrong state, the agent must restore the correct state rather than skipping ahead.

---

## CRITICAL RULE: ONE ROLE PER AGENT — THEN STOP

**An agent MUST perform exactly ONE role in the lifecycle and then STOP.**

- Read this file (`planner.md`) to understand the workflow.
- Read `current_plans.md` to determine the **current state** of the plan lifecycle.
- Assume **ONLY ONE role** based on the state triggers below.
- Complete that role fully.
- **STOP. Do not proceed to the next phase.**

**Never do two roles in succession. Never act as Planner 1 and then immediately become Planner 2. Never act as Executor and then immediately become Reviewer. Each phase transition requires a fresh agent context.**

**Why:** Each role benefits from independent perspective. The Evaluator must not be biased by having drafted one of the proposals. The Reviewer must not be biased by having written the code. The next phase always starts with a new agent reading `current_plans.md` cold.

---

## How to Determine Your Role

1. Read `current_plans.md`.
2. Scan for these markers IN ORDER:
   - If NO `plan:::` blocks exist → **You are Planner 1 (Phase 1)**
   - If exactly ONE `plan:::` block exists and NO `verdict:::` → **You are Planner 2 (Phase 1)**
   - If TWO OR MORE `plan:::` blocks exist and NO `verdict:::` → **You are Evaluator (Phase 2)**
   - If a `verdict:::` exists and NO `completion:::` → **You are Executor (Phase 3)**
   - If a `completion:::` exists and NO `review:::` → **You are Reviewer (Phase 4)**

## Active Plans

### [2026.04.28] — Voice Recording in Chat & Interfaces

**Goal:** Implement real-time voice recording in the main Chat and Design Chat interfaces with automatic Whisper transcription and seamless integration into the messaging flow.

**Phase 1: Research & Component Design**
- Research `MediaRecorder` API for cross-browser audio capture (Chrome, Safari, Firefox).
- Design a reusable `VoiceRecorder` hook or component that handles state: idle, recording, processing, error.
- Define UX for recording: tap-to-start, visual waveform/timer, tap-to-stop/send.
- verify: component design matches Istara's design system (Tailwind + Lucide).

**Phase 2: Core Logic Implementation**
- Implement `useVoiceRecorder` hook in `frontend/src/hooks/useVoiceRecorder.ts`.
- Add audio blob to WAV/OGG conversion helper if needed for backend compatibility.
- Wire the hook to `chat.transcribeVoice()` API client.
- verify: hook correctly captures audio and receives transcription from backend.

**Phase 3: UI Integration (Chat & Interfaces)**
- Replace the "Coming Soon" toast in `ChatView.tsx` with the real recorder.
- Add Mic button and recording UI to `DesignChatTab.tsx`.
- Implement "Transcribing..." loading states to the message inputs.
- verify: user can record and send messages via voice in both views.

**Phase 4: Compass Documentation & Validation**
- Update `Tech.md` with the new real-time voice capability.
- Update agent personas (`istara-main`, `istara-ui-audit`) to explain they can now receive voice input directly.
- Add simulation scenario `78-real-time-voice.mjs` to verify the UI flow.
- Regenerate living docs with `scripts/update_agent_md.py`.
- verify: all docs are in sync and simulation passes.

plan:::
1. Create `frontend/src/hooks/useVoiceRecorder.ts` -> verify: captured blob length > 0.
2. Integrate in `ChatView.tsx` -> verify: transcription appears in input/sends.
3. Integrate in `DesignChatTab.tsx` -> verify: works in Interfaces view.
4. Update `Tech.md` and personas -> verify: docs regenerated.
:::

verdict:::
The plan is sound. Implementing a reusable hook `useVoiceRecorder` is the most modular approach for synchronizing Chat and Interfaces views. Using the existing `chat.transcribeVoice()` API ensures consistency with the verified Whisper pipeline. Phase 4 updates to personas and simulation tests fulfill Compass obligations. Proceeding as Executor.
:::
   - If a `review:::` exists → **Check if archive is already done.** If `old_plans.md` was updated and `current_plans.md` is empty, STOP — the lifecycle is complete. If not, the Reviewer from Phase 4 should also perform Phase 5 (archiving) in the same session.
3. Perform ONLY that role.
4. STOP. The next agent will read `current_plans.md` and continue.

**Exception — Archiving:** Phase 5 (Archiving) does NOT require a separate agent. The Reviewer from Phase 4 should archive the plan immediately after writing the review, in the same session.

---

## Compass Is Mandatory Context

- `planner.md` is part of Compass.
- Any agent told to read `planner.md` must also follow the Compass reading order from `AGENT_ENTRYPOINT.md`.
- The user should not need to separately say "also read Compass."
- If planner and Compass seem to conflict, newest explicit user instruction wins, then Compass governance, then planner phase mechanics.

## Compass Swarm Discipline

- Every agent must declare its role, branch, base branch, touched surfaces, risk level, and handoff target.
- Every role must operate only within its phase.
- Large tasks must identify ownership slices and avoid cross-agent file collisions.
- Executor and Reviewer must remain independent.
- Stale branches are salvage-only unless proven current.
- Protected Compass files must not be deleted or emptied except under explicit lifecycle rules.

## Repository Intelligence Check

Before any non-trivial phase action, the agent must inspect or record (manually for now):
- current branch and divergence from intended base
- changed/deleted/renamed files
- stale branch risk
- protected-file risk
- generated-doc drift risk
- dead-code or resurrected-code risk
- hidden coupling suspicion
- relevant architectural decisions
- tests likely affected
- Compass/persona docs likely affected

## Protected Compass Files

The following files are protected system memory:
- `planner.md`
- `current_plans.md` (may only be cleared during Phase 5 archive or explicit reset)
- `old_plans.md`
- `AGENT_ENTRYPOINT.md`
- `AGENT.md`
- `COMPLETE_SYSTEM.md`
- `CHANGE_CHECKLIST.md`
- `SYSTEM_CHANGE_MATRIX.md`
- `SYSTEM_PROMPT.md`
- `Tech.md`

## Lightweight Architectural Decision Awareness

(Note: Future work may extract this to a dedicated ADR file or tool)
- Compass files are protected system memory.
- Stale branches are salvage-only.
- JSON skill definitions are canonical.
- Generated Compass docs must match current code.
- Review-discovered defects require correction and independent re-review.
- Final agents must explain new capabilities/processes to the user.

## Handoff Contract

Every phase must append a `handoff:::` block to `current_plans.md` with:
- `role:`
- `branch:`
- `base:`
- `touched_files:`
- `risk_level:`
- `repository_intelligence_checked:`
- `validation_done:`
- `known_limitations:`
- `next_agent_should:`

## Correction and Re-Review Loop

- If Reviewer finds a real issue, they write `correction:::` and do not archive.
- Correction agent fixes only that issue and writes `completed_correction:::`.
- A different agent must write `correction_review:::` after checking the fix.
- An additional `final_review:::` is required when the correction touched high-risk/shared surfaces.
- If correction cannot be completed, the final agent must tell the user plainly and leave `current_plans.md` unarchived.

## Final User Teaching Report

Before Phase 5 archive, a `user_report:::` block is required:
- `what_changed:`
- `why_it_matters:`
- `how_to_use_it:`
- `files_or_commands_user_should_know:`
- `remaining_risks:`

This is especially important when the plan creates a new workflow, command, generated output, user-facing feature, or developer process.

---

## Phase 1: Proposal Generation (Planner Agents)
Drafting agents must write proposals directly into `current_plans.md`.

**Rules:**
1. **First Planner:** If `current_plans.md` is empty/new, copy the user's prompt to the top and draft the first plan.
2. **Secondary Planner:** If exactly one `plan:::` block exists and no `verdict:::` exists, generate one alternative counter-plan and append it below.
3. **Format:** Use `[Model Name] plan: [YYYY-MM-DD HH:MM:SS]` followed by the `plan:::` marker. Use `--- END OF PLAN ---` to close.
4. **STOP after writing.** Do not evaluate your own plan. Another agent will be the Evaluator.
5. **Role Trigger for Next Agent:** TWO OR MORE `plan:::` blocks and no `verdict:::` means the next agent should become the Evaluator.

---

## Phase 2: Evaluation and Verdict (Evaluator Agent)
Triggered by two competing proposals in `current_plans.md`. **Must be a different agent than either Planner.**

**Rules:**
1. Analyze both plans. Introduce a third perspective to synthesize the best approach and correct architectural flaws.
2. **Fact-check claims** against the codebase. Do not trust the planners' assertions blindly.
3. **The Definitive Plan:** Render a final plan that the Executor will follow.
4. **Format:** Strictly start with `verdict::: [YYYY-MM-DD HH:MM:SS]`.
5. **STOP after writing the verdict.** Do not execute. Another agent will be the Executor.
6. **Role Trigger for Next Agent:** A `verdict:::` exists and no `completion:::` means the next agent should become the Executor.

---

## Phase 3: Execution & Staging (Executor Agent)
Triggered by a `verdict:::` in `current_plans.md`. **Must be a different agent than the Evaluator.**

**Rules:**
1. **Compass Staging-First Mandate (NON-NEGOTIABLE):**
   - **Branching**: `git checkout staging && git pull origin staging && git checkout -b feat/[feature-name]`.
   - **Implementation**: Apply code changes surgically.
   - **Authorship**: Ensure `git log` shows only `henrique-simoes` (pre-push hooks will enforce this).
   - **Documentation**: Run `python scripts/update_agent_md.py` and `python scripts/check_integrity.py`.
   - **Validation**: Pass all Layer 1-5 tests.
   - **Queue**: Push to origin, update `TESTING.md`, and open a PR to `staging`.
2. **Trace Generation:** Upon completion, write a status report to `current_plans.md` starting strictly with `completion::: [YYYY-MM-DD HH:MM:SS]`.
3. **STOP after writing completion.** Do not review your own work. Another agent will be the Reviewer.
4. **Role Trigger for Next Agent:** A `completion:::` exists and no `review:::` means the next agent should become the Reviewer.

---

## Phase 4: Specialist Review (Reviewer Agent)
Triggered by a `completion:::` in `current_plans.md`. **Must be a different agent than the Executor.**

**Rules:**
1. **Audit**: Read the modified files and verify they match the `verdict:::`.
2. **Standards**: Check for "Dead Code," type-safety, and adherence to `GEMINI.md` / Compass doctrines.
3. **Verification**: Confirm that the Executor correctly followed the staging-first workflow (branching, PR, docs sync).
4. **Verdict**: Write your audit results to `current_plans.md` starting strictly with `review::: [YYYY-MM-DD HH:MM:SS]`.
5. **After writing the review, immediately proceed to Phase 5 and archive the plan only if no correction is required.** Do not wait for another agent.
6. **Role Trigger for Next Agent:** If `review:::` exists and no `correction:::` is needed, the Reviewer should archive. If `correction:::` is needed, archive is blocked until Phase 6 completes.

---

## Phase 5: Archiving and Cleanup (Reviewer Continuation)
Triggered by a `review:::` in `current_plans.md`. **Performed by the same agent that wrote the review in Phase 4.**

**Rules:**
1. Identify the most recent plan number in `old_plans.md`. Increment by `1`.
2. Write a precise title (max 30 words).
3. Insert the entry at the top of `old_plans.md` in reverse-chronological order.
4. **Cleanup**: Once archived, **DELETE ALL CONTENTS** of `current_plans.md`.
5. **STOP.** The lifecycle is complete.

**Strict Archive Format:**
plan #[Number] [YYYY-MM-DD HH:MM:SS]
title: [Description]

[Full content of current_plans.md including proposals, verdict, completion, and review]


## Phase 6: Correction
The Correction agent repairs only the issue identified by Phase 4 or a later checker.

**Rules:**
1. Correction is a limited execution phase, not a new planning phase.
2. Start from the existing branch state and preserve the same Compass and staging-first requirements used in Phase 3.
3. Fix only the verified issue that triggered `correction:::` unless a directly related change is required to make the fix work.
4. Re-run the required validation and documentation sync for the touched surface.
5. Update `current_plans.md` with `completed_correction::: [YYYY-MM-DD HH:MM:SS]` and a concise report of what was fixed.
6. If the correction reveals another real defect, repeat Phase 6 until the plan is actually compliant.
7. Do not archive until the correction state is clean and the file is ready for Phase 5.
8. If `correction:::` exists, archiving is blocked until `completed_correction:::` is present and validated.

**Completion rule:** The correction loop continues until no unresolved correction markers remain and the plan state is valid enough for archival.
