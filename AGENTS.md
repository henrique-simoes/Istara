<!-- compass-forge:start -->
# Compass Forge Agent Workflow

Compass Forge is the control plane for this repository. **For the complete workflow
(spec → plan → tasks → gates → evidence → accept), command reference, MCP surface, and
footguns, load the `compass-forge` skill from the Skills library referenced at the bottom
of this file** — do not improvise the process from memory.

Project-specific facts (the skill can't know these):

- Project root: `/Users/user/Documents/Istara-main`
- Recipe: `istararustgraphtrial`
- MCP server: `python -m compass_forge.cli --workspace /Users/user/Documents/compass-forge mcp --target /Users/user/Documents/Istara-main --recipe istararustgraphtrial`
- UI/menu/route/store/agent/skill/model/test behavior changes must update the living
  feature documentation under `docs/features/`, regenerate the site/manifests with
  `python scripts/feature_docs.py --seed-missing --generate-site --check`, and attach that
  output as Compass Forge command evidence.
- Do not silently mutate external repos, global agent config, or generated integration files.

### Required Compass Forge repo-intelligence usage

Understand dependencies, relationships, and structure through Compass Forge's graph —
never by grep-and-guess alone. This is mandatory, not optional:

1. **Orient first, every session:** `compass-forge status` → `compass-forge next`. If
   staleness is flagged, run `compass-forge refresh` and `compass-forge index refresh`
   BEFORE trusting any graph answer — stale graphs lie.
2. **Before editing any non-trivial file, run BOTH:**
   - `compass-forge intelligence impact --path <path> --request "<the request>"` —
     must/should-inspect ranking, affected tests/contracts/routes, ownership/hotspot risk.
   - `compass-forge intelligence why <path>` — why the file exists: importers, graph
     links, routes, models, decisions, docs, recent git. If you cannot explain a file's
     role after `why`, you are not ready to edit it.
3. **Map relationships structurally:** use `compass-forge intelligence related
   --path <p>` (or `--symbol <s>`) for grounded dependency lists,
   `compass-forge intelligence code-graph` for the full file/symbol/edge graph,
   `compass-forge intelligence report` for repo-level structure,
   `compass-forge intelligence ownership`, `intelligence dead-code`,
   `intelligence git-history <path>`, and `intelligence trends` as the question demands.
4. **Context packs before raw file dumps:** `compass-forge context "<request>"
   --pack-type standard` (BM25 + graph, byte-budgeted; prefer `signature`/`summary`
   resolutions; escalate to `--pack-type full`/`review` only when needed). Do not read
   dozens of files raw when a pack answers the question.
5. **Pick verification from the graph:** `compass-forge intelligence test-impact
   --path <p>` and `compass-forge suggest-tests "<request>"` choose the tests that
   actually cover a change; run them and attach as command evidence.
6. **Unsure which CF tool fits:** `compass-forge classify "<request>"` for process
   level; `forge.suggest_tools {request}` (MCP) for the ranked tool. An empty
   `suggest_tools` result means off-topic — do not pad and retry.
7. **Cost ladder — cheapest tool that answers the question:** `status`/`next` →
   `intelligence impact`/`why`/`related` → `context` packs → `agent-brief` (once per
   session, `--compact` when possible) → `code-graph`/`report` (targeted queries only).
8. **Durable choices:** record architecture/process decisions with
   `compass-forge decision record --title "…" --body "…"` on Full-scope work so the
   next agent inherits the reasoning.
<!-- compass-forge:end -->

## Security Benchmark Gate

Auth, authorization, session, WebAuthn, connection string, pooled compute, MCP, webhook, LLM-provider, autoresearch, self-evolution, and agentic-memory changes must run the tracked security benchmark:

```bash
python scripts/security_benchmark.py --fail-on-threshold
```

Update `security/control_matrix.json`, `security/SECURITY_BENCHMARK.md`, and `tests/test_security_benchmark.py` when a security control, evidence path, standard version, or trigger pattern changes. Attach the scorecard output as Compass Forge command evidence before finishing security-sensitive tasks.

## Protected Local Artifact Folders

`LLMs/` and `Model_Finetuning/` are local, gitignored model/training artifact folders. Never delete, prune, move, or clean them during agent work.

## Live LLM and Model Loading Safety

Do not start live backend/frontend servers, send chat-completion probes, or trigger model loading without explicit user permission. Passive LLM status/discovery checks must stay passive. Active model loading belongs only on deliberate request paths and must be bounded to one configured target so agent work never loads multiple heavy models at once.

Use gitignored environment files, process environment, or macOS Keychain for live LLM endpoints and tokens. Never commit or paste private LLM server URLs, tokens, connection strings, or endpoint fingerprints that could identify a private server.

<!-- BEGIN SKILLS-LIBRARY (managed by skills-librarian) -->
## Skills library

This project has access to a shared, vendor- and model-neutral **Agent Skills** library
(the open [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
format — a folder per skill, each with a `SKILL.md`). It lives at:

    /Users/user/Documents/Skills

**Before starting a task, check whether a skill there applies**, then use it:

1. **Discover** — list the subfolders of the library and read the `description:` in each
   `SKILL.md`. Match your task against those descriptions.
2. **Load** — read the full `SKILL.md` whose description fits.
3. **Execute** — follow its instructions, gates, and output style for the whole task.
4. **Deepen on demand** — open a skill's `references/`, `scripts/`, or `assets/` files only
   when its `SKILL.md` points you there.

A skill is **instructions, not code** — reading its `SKILL.md` and acting on it *is*
invoking it. No special runtime is needed. For the full contract, per-harness wiring, and
the standards for adding or editing skills, read `/Users/user/Documents/Skills/AGENTS.md`. To add, edit, or
re-install this library, load the `/Users/user/Documents/Skills/skills-librarian` skill.

If you ever register a skill into a harness's own skills dir (e.g. `~/.codex/skills/`,
`~/.claude/skills/`), **symlink the library folder — never copy it** — and repair any
existing copies with `/Users/user/Documents/Skills/skills-librarian/scripts/sync-harness-skills.sh`.

**Available skills** (auto-generated on install — re-run the `skills-librarian` install to
refresh):

| Skill | Use it for |
|-------|-----------|
| `build-stream` | Use Build Stream to run ANY meaningful change — code, product, or docs — through one autonomous, resumable delivery lifecycle: frame → pl… |
| `build-stream-conductor` | Use this to run a Build Stream delivery as a MULTI-MODEL pipeline with no human intervention between stages: one watcher (the conductor)… |
| `build-stream-conductor-consulting` | Use this instead of build-stream-conductor whenever the conductor's multi-model pipeline runs on a CLIENT repo inside a consulting engage… |
| `compass-forge` | Use Compass Forge — the local-first control plane for agentic engineering — to run ANY meaningful repository change through its spec → cl… |
| `interface-design` | Use this to design, audit, or redesign professional interfaces and design systems, especially when moving an existing UI codebase through… |
| `kairos-ai-director` | Use as Kairos's AI director for model routing, agentic workflows, LangGraph/LangChain decisions, RAG and memory design, context and graph… |
| `kairos-design-director` | Use as Kairos's Design Director for GenUI design strategy, product design, UX design, UX research, design systems, trusted component cata… |
| `kairos-director-council` | Use for major Kairos decisions that need product, product marketing, design, engineering, and AI alignment. |
| `kairos-engineering-director` | Use as Kairos's engineering director for architecture, implementation planning, production readiness, platform boundaries, API/SDK design… |
| `kairos-product-director` | Use as Kairos's director-of-product operating system. |
| `kairos-product-marketing-director` | Use as Kairos's product marketing director for positioning, category design, messaging, ICP narrative, website copy, PRFAQ external story… |
| `skills-librarian` | Master skill for this Agent Skills library. |
| `consulting-assessment` | Use this to professionally assess a client's codebase, architecture, tests, security, CI/CD, documentation, product design/UX, design sys… |
| `consulting-client-comms` | Use this to draft any client-facing communication in a consulting engagement — first contact with a new lead, replies to existing clients… |
| `consulting-design` | Use this for interface, UX, visual-identity, design-system, Figma MCP, Code Connect, shadcn/astryx, or motion work inside a consulting en… |
| `consulting-documentation` | Use this in a consulting engagement's execution phase to create and keep current the client codebase's documentation — always written to… |
| `consulting-engagement` | Use this as the entry point whenever the user points at a client/project folder (a codebase, document set, designs, or any content) for c… |
| `consulting-execution` | Use this in a consulting engagement's authorized execution phase (phase 04) to actually change the client's code — implementing a fix or… |
| `consulting-memory` | Use this to ingest new client content (emails, documents, decks, meeting notes, messages) into a consulting project's private/memory/ sys… |
| `consulting-presentations` | Use this to turn a diagnosis, findings register, or engagement update into consulting-grade deliverable SPECS — slide-deck instruction fi… |
| `consulting-redteam` | Use this to run an authorized, defensive security assessment of a CLIENT'S OWN system using the T3MP3ST offensive-security harness inside… |
| `consulting-sandbox` | Use this to run a client's project in an isolated Docker container on the owner's machine — no internet access, local network only — when… |
| `wave-orchestrator` | Self-learning orchestration skill to deploy, monitor, and manage waves of tasks (e.g., in a Build Stream or Master Plan). Spawns the wave_orchestrator_v3 subagent which handles robust monitoring, rate limit fallback routing, and prevents premature pkill errors during long tasks. |
<!-- END SKILLS-LIBRARY (managed by skills-librarian) -->
