# Istara — Gemini Agent Directives

You operate within a constrained context window. Follow ALL numbered rules below. The user will reference them as `Rules: #1 #4 #9` in prompts.

---

## A. Code Discipline (always active)

1. **STEP 0 — DEAD CODE FIRST**: Before ANY structural refactor on a file >300 LOC, remove dead props, unused exports/imports, debug logs. Commit cleanup separately before the real work.

2. **PHASED EXECUTION**: Never touch >5 files in one phase. Complete phase → run verification → wait for explicit approval before next phase.

3. **SENIOR DEV OVERRIDE**: Do NOT "try the simplest approach." If architecture is flawed, state is duplicated, or patterns are inconsistent — propose and fix structural issues. Ask: "What would a perfectionist senior dev reject in code review?" Fix all of it.

4. **FORCED VERIFICATION**: FORBIDDEN from reporting a task complete until:
   - `run_shell_command` executes `npx tsc --noEmit` and it passes (zero errors).
   - `run_shell_command` executes `npx eslint . --quiet` and it passes (if configured).
   - All resulting errors are fixed.
   If no type-checker exists, state that explicitly.

## B. Context Integrity (always active)

5. **SUB-AGENT DELEGATION**: Tasks touching >5 independent files → delegate to the `generalist` sub-agent for batch processing. Not optional — sequential processing of large tasks causes context decay in the main session.

6. **CONTEXT DECAY AWARENESS**: After 10+ messages, re-read any file using `read_file` before editing. Never trust memory. Compaction silently destroys context.

7. **FILE READ BUDGET**: Cap reads at 2,000 lines. Files >500 LOC → use `start_line` and `end_line` to read in chunks. Never assume a single read captured the full file.

8. **TOOL RESULT BLINDNESS**: Results exceeding tool limits are truncated. If results look suspiciously sparse, re-run `grep_search` or `glob` with a narrower scope or different patterns. State when truncation is suspected.

## C. Edit Safety (always active)

9. **EDIT INTEGRITY**: Use `read_file` to get fresh context BEFORE every edit. Use `replace` for surgical changes. Re-read AFTER to verify the change was applied correctly. Max 3 edits per file before a verification read. **RESILIENCE**: If a session was interrupted or crashed, re-read all recently touched files to detect truncated writes or corrupted duplicate lines before proceeding.

10. **NO SEMANTIC SEARCH**: `grep_search` is powerful but not an AST. When renaming/changing any symbol, search separately for: direct calls, type-level refs, string literals, dynamic imports, re-exports/barrel files, test files/mocks. Never assume one search found everything.

## D. Release Flow (when shipping changes)

11. **SYSTEM INTEGRITY CHECK**: Before ANY structural change, consult `SYSTEM_INTEGRITY_GUIDE.md` Change Impact Matrix. Follow `CHANGE_CHECKLIST.md`. After changes, update the guide if new models/routes/skills/types were added. Critical couplings:
    - New model → `database.py init_db()` + `to_dict()` + `types.ts`
    - New route → `main.py` + `api.ts` + security middleware exempt paths
    - New skill → `definitions/` + `SCOPE_MAP` in `report_manager.py`
    - New WS event → `websocket.py` + frontend listener
    - New finding type → `agent.py _store_findings()` + `FindingsView.tsx`
    - Agent persona change → update ALL 5 agents SKILLS.md

12. **FEATURE INTEGRATION**: Update `scripts/update_agent_md.py` output + all 5 agent personas. Success metric: "If agents cannot understand, discuss, and act on this feature, it's a fail." Update `Tech.md` for architecture changes.

13. **STANDARDS & COMPLIANCE**: All changes adhere to WCAG. Validate against existing design system. Maintain keyboard shortcut compatibility.

14. **TESTING SUITE UPDATE** (design only, no execution): Update simulation agents + CI/CD pipeline. Cover: memory/DB systems, agent protocols, all UI menus. Tests must iterate automatically on failure.

15. **REPO CLEANUP & RELEASE**: Clean version for push — exclude personal configs, local test data, project-specific memory/skills. Include: new agents, core skills, system-wide updates.
    - **VERSIONING**: Run `git tag -l "vYYYY.MM.DD.*" | sort -V` before any version bump to identify the next sequence `N`. Never assume the sequence.
    - **CLEANUP**: Review untracked files with `git status`. Utility scripts (e.g., `yes.sh`, `*.tmp`) MUST NOT be committed unless they are permanent core tools.
    - `run_shell_command` for `./scripts/set-version.sh --bump` (CalVer across 7 files + VERSION).
    - Commit: `release: YYYY.MM.DD.N`
    - Tag: `git tag vYYYY.MM.DD.N && git push origin vYYYY.MM.DD.N`
    - Push: `git push origin main`

16. **DOCUMENTATION SYNC**: Update README, wiki, Tech.md. Remove outdated logic. Add explanations for new changes. Run `python scripts/update_agent_md.py` to regenerate AGENT.md.

17. **COMPLETION SIGNAL**: Once all tasks complete, all agents cease, git push finalized, and environment is verified clean → output: `FINISHED!!!`

## E. Project Constants

- **Name**: Istara | **Repo**: github.com/henrique-simoes/Istara
- **Persona dirs**: istara-main, istara-devops, istara-ui-audit, istara-ux-eval, istara-sim
- **Startup**: `./istara.sh` | **CSS**: istara-{50-900} green palette
- **localStorage**: istara_token, istara_active_view, istara_onboarding_*
- **CalVer**: `YYYY.MM.DD[.N]` | Tauri semver: `YEAR%100.MONTH*31+DAY.BUILD`
- **LLM provider**: LM Studio (default)
- **Version truth**: VERSION file → backend reads at startup → frontend via `/api/updates/version`
