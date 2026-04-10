# Istara — Model-Agnostic System Prompt

You are working inside the Istara repository. Your job is to make safe, architecture-aware changes while keeping the LLM-facing documentation current enough that the next agent can reason from the codebase without guesswork.

## Compass

`Compass` is Istara's name for its complete agentic development system: prompts, entry docs, generated architecture maps, change matrices, checklists, technical narrative, persona knowledge, and the test/simulation expectations that preserve product behavior over time.

When someone says "follow Compass," they mean: use this full documentation-and-testing system to make changes in a way that remains scalable, efficient, and architecture-safe.

## Primary Sources

Read these in this order when the change is non-trivial:

1. `AGENT_ENTRYPOINT.md` for the routing map of all agent-facing docs
2. `AGENT.md` for the compressed operating map
3. `COMPLETE_SYSTEM.md` for the generated architecture and coverage inventory
4. `SYSTEM_CHANGE_MATRIX.md` for cross-surface impact mapping
5. `CHANGE_CHECKLIST.md` for implementation obligations
6. `SYSTEM_INTEGRITY_GUIDE.md` when you need deeper legacy reference detail

## Core Rules

1. Treat code, tests, and docs as one system. If one changes, check whether the other two should change too.
2. Treat `tests/e2e_test.py` and `tests/simulation/scenarios/` as behavioral specifications for UI flows, menus, and end-to-end capabilities.
3. Treat Compass as part of the product's operating system. If the change alters how future agents should understand, verify, navigate, or safely modify Istara, update Compass in the same change.
4. Do not trust memory for architecture. Re-read the current files and generated docs before making structural changes.
5. Use `SYSTEM_CHANGE_MATRIX.md` to expand every local change into its dependent backend, frontend, UX, test, release, and documentation surfaces.
6. When adding or changing a route, model, type, store, view, menu item, skill, persona, background workflow, or integration, update the implementation and then regenerate the living docs in the same change.
7. If the generated docs fail to capture an important architectural fact, improve `scripts/update_agent_md.py` so the fact becomes automatic.
8. Keep the docs drift-resistant. Avoid one-off manual summaries when the information can be scanned from the repository.

## Non-Negotiable Governance Rules

1. If architecture, subsystem boundaries, release/update behavior, installation flow, or operational process changes, update `Tech.md` in the same change.
2. If a feature, workflow, menu, UX path, or backend capability changes, update the testing surface for future regressions. This usually means `tests/simulation/scenarios/`, `tests/e2e_test.py`, or both.
3. If existing scenarios no longer describe the changed behavior well enough, add a new simulation scenario instead of overloading an unrelated one.
4. Success metric for product changes: if Istara's own agents cannot understand the feature, discuss it accurately, route work around it, or use it safely, the change is incomplete.
5. When a capability changes in a way Istara's own agents should know, update the relevant persona files in `backend/app/agents/personas/`.
6. Documentation and persona updates belong in the same change as the implementation, not in a later cleanup.
7. Release/version/tag behavior must remain internally consistent across scripts, workflows, updater logic, docs, and desktop/server update checks.
8. GitHub Actions release behavior must match the real repo doctrine: release-worthy pushes to `main` publish installers and a GitHub Release, while tag/manual flows remain valid for explicit release control.
9. Release-worthy changes include product behavior changes in backend/frontend/desktop/relay/install/update surfaces and Compass-critical agent docs or persona knowledge that Istara's internal agents rely on.
10. Before preparing a release intentionally, run the standardized local release sequence via `scripts/prepare-release.sh`.

## Three-Layer Testing Mandate

Istara has three test layers. Every meaningful change must include tests at the appropriate layers:

### Layer 1: Unit / Integration Tests (`tests/test_*.py`)
- **What**: pytest tests for individual components — auth, security, services, infrastructure classes, API routes.
- **When**: Always add for new backend services, API routes, security mechanisms, infrastructure classes, or utility modules.
- **Pattern**: Use `httpx.ASGITransport(app=app)` for API route tests. Use in-memory SQLite with `async_sessionmaker` for model tests. Follow `tests/test_auth_security.py` and `tests/test_steering.py` patterns.
- **Run**: `pytest tests/`

### Layer 2: E2E Phased Test (`tests/e2e_test.py`)
- **What**: Single comprehensive test that runs against a live Istara instance. Organized in numbered phases (0–12+). Each phase tests a complete system area with real data, real skills, real agents.
- **When**: Always add a new phase or test entries when new API routes, endpoints, or system-wide features are added. Add to the appropriate existing phase if it fits, or create a new phase if it's a new system area.
- **Pattern**: Use the `test("name", lambda: assert_ok(...))` pattern. Each test is independent but phases build on earlier setup (auth → project → files → chat → tasks → etc.).
- **Run**: `python tests/e2e_test.py`

### Layer 3: Simulation Scenarios (`tests/simulation/scenarios/*.mjs`)
- **What**: Playwright behavioral scenarios that run in the simulation runner. Each scenario tests a complete user-facing UX path with real browser interactions, accessibility evaluation, and heuristic scoring.
- **When**: Always add a new scenario for new user-facing workflows, navigation paths, UI components with interactive behavior, or UX flows. Update existing scenarios when they touch the changed behavior.
- **Pattern**: Number the file sequentially (`70-mid-execution-steering.mjs`). Export `name`, `id`, and `async function run(ctx)` with `{ api, page, report }`. Add the file name (without `.mjs`) to the `scenarioFiles` array in `tests/simulation/run.mjs`. Use `api.get/post/delete()` for API calls and `page.goto()/page.getBy*()` for UI interactions. Report results via `report(name, checks)`.
- **Run**: `node tests/simulation/run.mjs` (full suite) or `node tests/simulation/run.mjs --scenario 70` (single scenario)

### Test Decision Matrix

| What changed | Layer 1 (pytest) | Layer 2 (e2e_test.py) | Layer 3 (simulation) |
|---|---|---|---|
| New API route or endpoint | ✅ Route tests | ✅ Add to relevant phase | — |
| New backend service or utility | ✅ Service tests | — | — |
| New security mechanism | ✅ Security tests | ✅ Add to relevant phase | — |
| New user-facing UI component | — | — | ✅ New or updated scenario |
| New user workflow / UX flow | — | ✅ Add to relevant phase | ✅ New scenario |
| New system-wide feature | ✅ Infrastructure tests | ✅ New phase | ✅ New scenario |
| Navigation / menu change | — | ✅ Frontend phase | ✅ Update navigation scenario |
| Agent behavior change | ✅ Agent tests | ✅ Agent phase | ✅ Agent architecture scenario |

### Non-Negotiable Test Rules
- **No change ships without tests.** Code without test coverage is incomplete.
- **Don't stretch unrelated scenarios.** If existing simulation coverage no longer describes the changed flow well, add a new scenario instead of forcing the change into unrelated old coverage.
- **Tests belong in the same commit as the implementation.** Not in a later cleanup commit.
- **Follow existing patterns.** Don't invent new test architectures — use the three-layer structure above.

## Required Documentation Workflow

Run these after architecture-affecting work:

```bash
python scripts/update_agent_md.py
python scripts/check_integrity.py
```

## Commit Authorship Rules

- **Never add `Co-authored-by` trailers** to commit messages. Only the human owner should appear as author.
- A pre-push hook (`.git/hooks/pre-push`) **automatically rewrites** the author, committer, and commit message before every push to ensure only `henrique-simoes <simoeshz@gmail.com>` appears on GitHub.
- This hook runs as the **last step before push** — it overrides even the agent's own commits.
- Manual verification: `git log --all --pretty=format:"%an <%ae>" | sort -u` should only show `henrique-simoes`.

## Branching & Pull Request Workflow

Istara uses a **staging-first** workflow to prevent broken code from reaching `main`:

- **`main`** — production-ready, protected branch. Only merged via PR from `staging`.
- **`staging`** — integration branch. All feature work lands here first. CI must pass before merging to `main`.
- **Feature branches** — `feat/feature-name`, `fix/bug-name`, `docs/doc-name`. Created from `staging`, merged back to `staging` via PR.

### Rules:
- **Direct push to `main` is blocked** — only allowed for version bumps and Compass doc regenerations via automated CI.
- **Feature work (3+ commits) MUST use a feature branch** → PR → `staging` → PR → `main`.
- **Trivial changes** (typos, version bumps, doc regenerations) may push directly to `staging`.
- **Branch protection on `main`** requires CI to pass and PR review before merge.
- **Squash merge** for clean history — one commit per feature on `main`.

### Typical flow:
```bash
# 1. Create feature branch from staging
git checkout staging && git pull
git checkout -b feat/new-security-feature

# 2. Work, commit, push
git add -A && git commit -m "feat: add biometric auth"
git push origin feat/new-security-feature

# 3. Open PR to staging, wait for CI, merge
gh pr create --base staging --title "feat: add biometric auth"

# 4. Once staging is green, PR to main
git checkout staging && git pull
git checkout -b release/staging-to-main
gh pr create --base main --title "Merge staging → main"
```

Tech.md is the **narrative technical source** that describes how Istara works architecturally. Unlike AGENT.md and COMPLETE_SYSTEM.md (which are auto-generated), Tech.md is hand-authored and MUST be updated when:

- New security mechanisms are added (auth, encryption, TLS, container hardening, network segmentation)
- New agent capabilities are introduced (steering, A2A, skill changes)
- Architecture or deployment changes (Docker networks, Caddy, installer behavior)
- New subsystems or services are created

The `check_integrity.py` script includes keyword-based freshness verification. If Tech.md is missing key concepts, the integrity check will flag it. **Never ship a change that triggers a TECH.md integrity warning without updating Tech.md first.**

## Change Awareness

Before editing, ask:

- Which API surface changes?
- Which frontend state or mounted views change?
- Which tests describe or protect this behavior today?
- Do the current 70+ simulation scenarios already capture this behavior, or does Compass now require a new one?
- Which entries in `SYSTEM_CHANGE_MATRIX.md` apply?
- Does `Tech.md` need to change because the architecture or process changed?
- Do Istara's own agents need persona/prompt updates to understand this feature?
- Which LLM-facing docs must reflect this so future agents do not regress it?

## Completion Standard

Work is not complete if the code changed but the generated architecture docs, procedural docs, Tech narrative, personas, or future-facing tests were left behind.
