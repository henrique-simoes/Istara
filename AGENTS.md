<!-- compass-forge:start -->
# Compass Forge Agent Workflow

Compass Forge is the control plane for this repository.

- Project root: this repository checkout (`<repo-root>`)
- Recipe: `istararustgraphtrial`
- MCP server: `python -m compass_forge.cli --workspace <compass-forge-root> mcp --target <repo-root> --recipe istararustgraphtrial`

Before editing, run `compass-forge status` and `compass-forge agent-brief --request "<user request>"`.
For Standard, Full, or uncertain changes, create a durable spec first: `compass-forge spec create "<user request>"`, then `spec plan` and `spec tasks`.
Use `compass-forge intelligence impact --request "<user request>"` or `--path <path>` before touching important files.
If tasks exist, use `compass-forge work-order --role implementer --task CF-N`.
Run `compass-forge gate before` and `compass-forge gate after` for meaningful changes.
Attach command, gate, and review evidence before marking tasks done.
UI/menu/route/store/agent/skill/model/test behavior changes must update Istara's living feature documentation under `docs/features/`, regenerate the site/manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`, and attach that output as Compass Forge evidence.
Do not silently mutate external repos, global agent config, or generated integration files.

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

## Istara Research Spine Contract

Istara is a research system. Every product feature that ingests, creates,
processes, retrieves, summarizes, validates, visualizes, routes, promotes, or
reports user research data is an extension of the same research-validity spine:

`Sources -> Evidence Units -> Independent Multi-Model Atomic Extraction + Open Coding -> Reliability + Grounding -> Reconciliation -> Accepted Atoms/Nuggets -> Facts -> Insights -> Recommendations -> In Review -> Human-Approved Done -> Reports`.

Atomic Research is not a pre-validation summary layer. Bias reduction happens
before trust: model output can create candidate/provisional artifacts, but no
feature may treat nuggets, facts, insights, recommendations, design decisions,
tasks, or reports as reportable until the source-grounded coding, reliability,
reconciliation, and Done-task gates have accepted them. Evidence units come
from raw source spans, not synthesized nugget prose, unless exact source spans
are preserved and the artifact remains provisional until validated.

This spine is not optional and not limited to Findings, Tasks, or Reports. It
applies to skills, task creation and execution, ReAct/tool calls, chat,
documents, interviews, surveys, AURA-style research, integrations, deployments,
interfaces, autoresearch, self-evolution, RAG/GraphRAG, compute donation,
benchmarks, simulations, and any future feature that touches research data.

Before changing any feature, use Compass Forge impact output as a starting map,
then follow dependencies and feature relationships until you know whether the
change touches the research spine. If it does, the feature must enter or respect
the pipeline in `docs/architecture/research-validity-contract.md`. Do not treat
parallel data paths, raw finding creation, synthetic benchmark shortcuts, or
feature-specific objectives as acceptable substitutes for the spine unless the
path is explicitly unit-scoped, non-research, or documented as a governed
exception.

If a feature currently bypasses the spine, classify it as architecture debt and
either fix it in scope or report it explicitly. Never describe the system as
fully aligned while any research-data path bypasses evidence units, coding,
reliability, reconciliation, human review, route evidence, or Done/report gates.

## Self-Improvement Governance Contract

Self-improvement exists only to improve the Research Spine. Telemetry observes,
ReasoningBank stores process lessons, Memento Skills stores validated skill
memory, Autoresearch runs sandboxed experiments, Meta-Hyperagent proposes
project-scoped variants, and Self-Evolution applies only governed promotions.
RAG/BM25 retrieves exact evidence, GraphRAG synthesizes and traces
dependencies, Prompt-RAG adds supporting context, and LLMLingua compresses only
when protected protocol/codebook/gate/schema blocks remain intact.

None of these systems may create report evidence, silently rewrite protected
methodology, weaken authorization, mutate global process state from
project-scoped evidence, or learn strong positive skill/model signals from raw
tool success. If a self-improvement path touches research data or process
policy, it must preserve project scope, route/evidence handles, verification
state, governance status, and Research Spine gate status. The durable contract
is `docs/architecture/self-improvement-governance-contract.md`.

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
| `build-stream-conductor-consulting` | Use this instead of build-stream-conductor whenever the conductor's multi-model pipeline runs on a CLIENT repo inside a consulting engagement (phase 04 execution mode) — it is the consulting-safe overlay that keeps the whole toolchain invisible to the client. Trigger for "/conductor-consulting", "run the conductor on the client project", "multi-model delivery for a client", or when consulting-execution needs the S2–S4 pipeline automated. Consulting is the OUTER policy (state in private/, no AI/tool traces in code, commits, branches, PRs, docs, or config; outward steps owner-gated); the original build-stream-conductor is the INNER engine, loaded live and unmodified. Requires authorized execution mode in private/engagement.md; without it, stop and stay read-only. |
| `build-stream-conductor` | Use this to run a Build Stream delivery as a MULTI-MODEL pipeline with no human intervention between stages: one watcher (the conductor) polls Compass Forge and launches each stage on a specific model + settings (e.g. Claude opus-4.8 at xhigh effort, GPT-5.5 at xhigh reasoning) as detached CF actor sessions — plan by one model, reviewed and modified by another, implemented by a third, cross-reviewed until every reviewer passes, then PR-ready. Trigger when the user asks to orchestrate multiple models/agents/harnesses on one plan, to have agents hand off automatically when the previous one finishes, to run "X plans, Y reviews, Z codes" pipelines, or to collect per-model error/correction scorecards, or to run approved multi-wave/sequential-wave Build Stream implementation and convergence. Works from any harness (Claude Code, Codex CLI, Claude Desktop as cockpit); requires the compass-forge skill and the pinned native Rust Compass Forge binary (explicit `COMPASS_FORGE_BIN` + `COMPASS_FORGE_SHA256`; no Python or PATH fallback). |
| `build-stream` | Use Build Stream to run ANY meaningful change — code, product, or docs — through one autonomous, resumable delivery lifecycle: frame → plan → execute → review → remediate → ship & learn, recorded in a single durable file so any agent (any model, any harness) can resume statelessly from where the last one stopped. Trigger when asked to build, ship, or deliver a feature/fix/change end-to-end; to plan and execute with minimal human intervention; to run a rigorous review-and-remediation loop; to coordinate multiple agents on one plan; or whenever a repo has a build-stream / agent-plan lifecycle file to continue. Drives Compass Forge as its control plane and codifies the planning, execution, review, and remediation practices of the largest, most complex tech product companies. |
| `compass-forge` | Use Compass Forge — the local-first control plane for agentic engineering — to run ANY meaningful repository change through its spec → clarify → plan → tasks → work-order → gate → evidence → accept spine. Trigger whenever you start work in a repo that has a `.compass-forge/` directory or a Compass Forge recipe, when the user asks to plan, spec, gate, or record work through Compass Forge, or before any Standard/Full/security/ architecture/contract change that needs a durable execution contract, impact analysis, architecture gates, or multi-agent coordination. Also use when unsure WHICH of CF's ~140 tools fits a request (forge.suggest_tools), or when an MCP tools/list looks unexpectedly short (lean tool profile). Requires the explicitly pinned native Rust binary (`COMPASS_FORGE_BIN` + `COMPASS_FORGE_SHA256`, validated path/digest/runtime/capabilities); un-migrated commands refuse with typed `not_yet_native` — no Python or PATH fallback. Teaches the full command lifecycle, process levels, gates, evidence rules, large-repository intelligence and graph traversal protocol, recipes, the complete capability map with CLI + MCP paths, Build Stream / Conductor integration, the adaptive tool-intelligence layer, and the footguns. |
| `interface-design` | Use this to design, audit, or redesign professional interfaces and design systems, especially when moving an existing UI codebase through DESIGN.md/DTCG tokens, Figma MCP variables and components, Code Connect, shadcn/ui or astryx, responsive screens, Motion, and back into production code without a rewrite; also trigger for UI/UX design, visual identity, design tokens, component libraries, Figma design-system creation, code-to-Figma or Figma-to-code work, motion design, and requests to avoid generic AI-generated UI; also trigger for visual debug — directed visual inspection of a running app when a screen does not show what the code says, visual QA, interaction-state coverage beyond the initial page load (dialogs, tabs, filters, pagination, forms), and per-role UI checks. In a client engagement use consulting-design, which adds authorization, private/, external-tool, and invisibility guardrails. |
| `kairos-ai-director` | Use as Kairos's AI director for model routing, agentic workflows, LangGraph/LangChain decisions, RAG and memory design, context and graph retrieval, structured outputs, critique agents, UI generation boundaries, voice/audio-to-GenUI behavior, design-aware GenUI evaluation, model-provider neutrality, evals, safety, policy, AI observability, prompt/version management, and AI governance. Use before major Kairos AI implementation work even when not explicitly requested. Consider patterns from OpenAI, Anthropic, Google Gemini/DeepMind, Alibaba Qwen, Mistral, Microsoft Responsible AI, LangSmith, Langfuse, Arize, Bedrock Agents, Gemini Enterprise Agent Platform, Agentforce, Copilot Studio, Voiceflow, Vapi, Figma/Canva design-AI systems, and governed enterprise AI platforms. |
| `kairos-design-director` | Use as Kairos's Design Director for GenUI design strategy, product design, UX design, UX research, design systems, trusted component catalogs, UI contract quality, visual identity, accessibility, motion, density, content clarity, design critique, design QA, stable UI change budgets, affordance recall, DESIGN.md, Stitch, A2UI catalog design, and any frontend or GenUI feature before implementation. Use before major Kairos design or UI decisions even when not explicitly requested. Consider practices from Figma, Canva, Apple HIG, Adobe Spectrum, Google Material/Google Design, Nielsen Norman Group, W3C WCAG, Microsoft Human-AI Interaction, OpenAI Apps/Realtimes/Structured Outputs, Anthropic, Gemini, Mistral, Qwen, and frontier AI interface platforms. |
| `kairos-director-council` | Use for major Kairos decisions that need product, product marketing, design, engineering, and AI alignment. Trigger for requests to summon or convene the council; architecture plans; MVP scope; PRD, PRFAQ, roadmap, review, decision gate, implementation plan, GTM, research plan, risk/governance, or postmortem artifacts; feature-to-code gates; launch strategy; product packaging; enterprise readiness; GenUI design quality; model/agent/RAG/eval decisions; channel integrations; governance changes; or any decision where Kairos could drift from generic enterprise adaptive UI decision infrastructure into a vertical app or unfocused GenUI demo. Requires Compass Forge for repository work and coordinates the kairos-product-director, kairos-product-marketing-director, kairos-design-director, kairos-engineering-director, and kairos-ai-director lenses. |
| `kairos-engineering-director` | Use as Kairos's engineering director for architecture, implementation planning, production readiness, platform boundaries, API/SDK design, renderer and design-system implementation quality, integration ergonomics, reliability, security, observability, migrations, testing strategy, technical debt, scalability, developer experience, and code-review decisions. Use before major Kairos implementation work even when not explicitly requested. Consider engineering patterns from AWS Well-Architected, Segment-style ingestion platforms, Statsig/LaunchDarkly decisioning systems, Langfuse/LangSmith observability, Arize, Bedrock Agents, Gemini Enterprise Agent Platform, Microsoft Copilot Studio, Voiceflow, Vapi, Palantir, Databricks, Snowflake, Figma, Canva, Adobe Spectrum, Writer, Typeface, and similar enterprise intelligence platforms. |
| `kairos-product-director` | Use as Kairos's director-of-product operating system. Use whenever an agent is working on Kairos product strategy, productization, MVP scope, PRFAQ or Working Backwards artifacts, ICP, buyer/user pain, feature specs, roadmap, market fit, pricing or packaging, customer discovery, enterprise readiness, product metrics, launch readiness, or deciding whether a Kairos idea should become code. Also use before implementation planning or code changes for Kairos product features, even when the user does not explicitly ask, to test product rationale, customer value, evidence, governance, MVP fit, and enterprise buyer objections. Consider the product patterns of Segment, Amplitude, Statsig, LaunchDarkly, Optimizely, Braze, Adobe Experience Platform, Langfuse, LangSmith, Arize, Salesforce Agentforce, Amazon Bedrock Agents, Google Gemini Enterprise Agent Platform, Microsoft Copilot Studio, Voiceflow, Vapi, Palantir, Databricks, Snowflake, Figma, Canva, Adobe Spectrum, Writer, Typeface, and similar enterprise intelligence platforms. |
| `kairos-product-marketing-director` | Use as Kairos's product marketing director for positioning, category design, messaging, ICP narrative, website copy, PRFAQ external story, launch plans, competitive framing, sales enablement, packaging narrative, enterprise trust narrative, pricing-page language, demo storyline, and market proof. Consider how enterprise AI, analytics, experimentation, personalization, LLMOps, voice-agent, operational-intelligence, design-system, AI-interface, and governed-generation companies market themselves, including Segment, Amplitude, Statsig, LaunchDarkly, Optimizely, Braze, Adobe Experience Platform, Langfuse, LangSmith, Arize, Agentforce, Voiceflow, Vapi, Palantir, Databricks, Snowflake, Figma, Canva, Adobe Spectrum, Writer, Typeface, and similar enterprise intelligence platforms. |
| `server` | Use this to securely provision, harden, or operate a headless Linux Docker development and deployment host, especially for SSH-based agent access, Docker Engine and Compose workloads, private-LAN firewalling, Git repositories, systemd services, updates, logs, and reboot-safe verification. |
| `skills-librarian` | Master skill for this Agent Skills library. Use to connect a project to the library: install or refresh a small managed pointer block in the project's AGENTS.md — creating AGENTS.md if none exists — so ANY agent working in that project learns how to discover, load, use, and correctly edit every skill in this folder. Also the reference of record for the standards used to author and edit skills here. Trigger when asked to "install / register / onboard / hook up the skills library", "set up AGENTS.md so agents can find these skills", "make this project aware of my skills", or when you need the rules for using or writing a skill in this folder. |
| `transcribe-gpt` | Use this to transcribe any audio or video file (mp4, mov, mkv, mp3, wav, m4a, ogg, …) into a single speaker-diarized Markdown transcript with OpenAI's gpt-4o-transcribe-diarize model. The skill always asks the user for the API key, the file to transcribe, and the output destination (default ~/Desktop), then handles everything else itself: ffmpeg audio extraction, splitting under the 25 MB upload cap, model settings (diarized_json, chunking_strategy=auto), known-speaker references for consistent labels across chunks, retries, resumable per-chunk cache, reference-style Markdown output, and a total elapsed-time report. Trigger on requests to transcribe / diarize / speech-to-text a recording with OpenAI, "gpt-4o-transcribe-diarize", "speaker diarization transcript", or /transcribe-gpt. |
| `vps` | Use this to safely inspect, deploy, update, or retire repositories on the managed VPS with Dokploy and Docker, especially when strict workload isolation, minimal public ports, firewall verification, keychain-backed SSH access, and tamper-evident action auditing are required. |
<!-- END SKILLS-LIBRARY (managed by skills-librarian) -->
