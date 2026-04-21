# System Directive: Code Change Planning, Archiving & Review Workflow

**Objective:** This document dictates the strict protocol for generating, evaluating, executing, and reviewing code change plans. All agents must adhere to these instructions to maintain architectural integrity across `current_plans.md` and `old_plans.md`, following the **Compass staging-first workflow** to its core.

## File Definitions
* **`current_plans.md`**: The active workspace. Holds draft proposals, the final verdict, execution status, and the review report.
* **`old_plans.md`**: The historical ledger. Permanent archive of all finalized, reviewed, and approved plans.

---

## Phase 1: Proposal Generation (Planner Agents)
Drafting agents must write proposals directly into `current_plans.md`.

**Rules:**
1. **First Planner:** If `current_plans.md` is empty/new, copy the user's prompt to the top and draft your plan.
2. **Secondary Planner:** If exactly ONE `plan:::` block exists, generate an alternative counter-plan and append it below.
3. **Format:** Use `[Model Name] plan: [YYYY-MM-DD HH:MM:SS]` followed by the `plan:::` marker. Use `--- END OF PLAN ---` to close.
4. **Role Trigger (Evaluator):** If TWO OR MORE `plan:::` blocks exist and no `verdict:::` is present, skip to Phase 2.

---

## Phase 2: Evaluation and Verdict (Evaluator Agent)
Triggered by two competing proposals in `current_plans.md`.

**Rules:**
1. Analyze both plans. Introduce a third perspective to synthesize the best approach and correct architectural flaws.
2. **The Definitive Plan:** Render a final plan that the Executor will follow.
3. **Format:** Strictly start with `verdict::: [YYYY-MM-DD HH:MM:SS]`.
4. **Role Trigger (Executor):** If a `verdict:::` exists and no `completion:::` is present, skip to Phase 3.

---

## Phase 3: Execution & Staging (Executor Agent)
Triggered by a `verdict:::` in `current_plans.md`.

**Rules:**
1. **Compass Staging-First Mandate (NON-NEGOTIABLE):**
   - **Branching**: `git checkout staging && git pull origin staging && git checkout -b feat/[feature-name]`.
   - **Implementation**: Apply code changes surgicaly.
   - **Authorship**: Ensure `git log` shows only `henrique-simoes` (pre-push hooks will enforce this).
   - **Documentation**: Run `python scripts/update_agent_md.py` and `python scripts/check_integrity.py`.
   - **Validation**: Pass all Layer 1-5 tests.
   - **Queue**: Push to origin, update `TESTING.md`, and open a PR to `staging`.
2. **Trace Generation:** Upon completion, write a status report to `current_plans.md` starting strictly with `completion::: [YYYY-MM-DD HH:MM:SS]`.
3. **Role Trigger (Reviewer):** If a `completion:::` exists and no `review:::` is present, skip to Phase 4.

---

## Phase 4: Specialist Review (Reviewer Agent)
Triggered by a `completion:::` in `current_plans.md`. **Must be a different agent than the Executor.**

**Rules:**
1. **Audit**: Read the modified files and verify they match the `verdict:::`.
2. **Standards**: Check for "Dead Code," type-safety, and adherence to `GEMINI.md` / Compass doctrines.
3. **Verification**: Confirm that the Executor correctly followed the staging-first workflow (branching, PR, docs sync).
4. **Verdict**: Write your audit results to `current_plans.md` starting strictly with `review::: [YYYY-MM-DD HH:MM:SS]`.
5. Only after the review is written, proceed to Phase 5.

---

## Phase 5: Archiving and Cleanup (`old_plans.md`)
The Reviewer Agent must archive the entire lifecycle and reset the workspace.

**Rules:**
1. Identify the most recent plan number in `old_plans.md`. Increment by `1`.
2. Write a precise title (max 30 words).
3. Insert the entry at the top of `old_plans.md` in reverse-chronological order.
4. **Cleanup**: Once archived, **DELETE ALL CONTENTS** of `current_plans.md`.

**Strict Archive Format:**
plan #[Number] [YYYY-MM-DD HH:MM:SS]
title: [Description]

[Full content of current_plans.md including proposals, verdict, completion, and review]
