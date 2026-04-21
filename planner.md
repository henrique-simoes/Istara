# System Directive: Code Change Planning, Archiving & Review Workflow

**Objective:** This document dictates the strict protocol for generating, evaluating, executing, and reviewing code change plans. All agents must adhere to these instructions to maintain architectural integrity across `current_plans.md` and `old_plans.md`, following the **Compass staging-first workflow** to its core.

## File Definitions
* **`current_plans.md`**: The active workspace. Holds draft proposals, the final verdict, execution status, and the review report.
* **`old_plans.md`**: The historical ledger. Permanent archive of all finalized, reviewed, and approved plans.

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
   - If a `review:::` exists → **Check if archive is already done.** If `old_plans.md` was updated and `current_plans.md` is empty, STOP — the lifecycle is complete. If not, the Reviewer from Phase 4 should also perform Phase 5 (archiving) in the same session.
3. Perform ONLY that role.
4. STOP. The next agent will read `current_plans.md` and continue.

**Exception — Archiving:** Phase 5 (Archiving) does NOT require a separate agent. The Reviewer from Phase 4 should archive the plan immediately after writing the review, in the same session.

---

## Phase 1: Proposal Generation (Planner Agents)
Drafting agents must write proposals directly into `current_plans.md`.

**Rules:**
1. **First Planner:** If `current_plans.md` is empty/new, copy the user's prompt to the top and draft your plan.
2. **Secondary Planner:** If exactly ONE `plan:::` block exists, generate an alternative counter-plan and append it below.
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
   - **Implementation**: Apply code changes surgicaly.
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
5. **After writing the review, immediately proceed to Phase 5 and archive the plan.** Do not wait for another agent.
6. **Role Trigger for Next Agent:** A `review:::` exists means the Reviewer should also archive. If `current_plans.md` is empty after archiving, the lifecycle is complete.

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
