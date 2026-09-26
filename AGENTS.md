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

## Protected QA Containers and Databases (Never Delete)

The Mac Studio QA host keeps containers that hold research results from testing and multi-model runs used for consultation. They carry the `never-delete-official-` name prefix and must never be deleted:

- `never-delete-official-istara-qa-readiness5-20260910-qa-backend` — QA backend run data (DB in tmpfs `/tmp/istara-qa.db`, feature tree in `/app/data`).
- `never-delete-official-w3-live-backend`, `never-delete-official-w3-live-backend-fix` — W3 candidate live runs (`istara-w3.db` + run artifacts in `/app/data`).
- `never-delete-official-w4-live-pi`, `never-delete-official-w4-live-legacy` — W4 long-horizon multi-model telemetry (host dataset at `~/w4-scratch-20260910/data`).

Rules:

1. Never run `docker rm`, `docker container prune`, or `docker system prune` against these containers, and never delete their databases or images.
2. Their data surfaces are **tmpfs (in RAM)**: before stopping any protected container, snapshot `/app/data` and `/tmp/*.db*` to `~/never-delete-official-data/<container>/<UTC-timestamp>/` on the host. Snapshots are permanent records — never delete, move, or prune them.
3. Code updates happen by renewing the codebase with new commits only: rebuild images from repo HEAD into a new QA run (`QA_RUN_ID=<branch>-<date>`, unique project per `docker-compose.qa.yml` contract). All existing databases and data snapshots for all features must be kept across redeploys — a redeploy never erases prior run data.
4. The W4 multi-model telemetry dataset at `~/w4-scratch-20260910/data` (`istara-w4-pi.db`, `istara-w4-legacy.db`, run JSONs/logs) is protected research data: never delete, move, or prune it.

## Live LLM and Model Loading Safety

Do not start live backend/frontend servers, send chat-completion probes, or trigger model loading without explicit user permission. Passive LLM status/discovery checks must stay passive. Active model loading belongs only on deliberate request paths and must be bounded to one configured target so agent work never loads multiple heavy models at once.

Use gitignored environment files, process environment, or macOS Keychain for live LLM endpoints and tokens. Never commit or paste private LLM server URLs, tokens, connection strings, or endpoint fingerprints that could identify a private server.

## Full UI Testing Suite Contract

Every novel feature, sub-feature, addition, or behavior change must ship with coverage in the container-first user-journey suite (`tests/simulation/` scenarios + `tests/real_user_benchmark/` where long-form/team/donation flows apply). A feature is not done until the suite drives it the way a real user would, through a container, with dated verdicts.

When adding or changing product behavior, the author must:

1. **Add or extend a Playwright scenario** in `tests/simulation/scenarios/` (registered in `lib/scenario-registry.mjs`) that performs the feature's real browser acts — navigate, click, fill, upload, send — not API calls with a screenshot attached. API-behind-browser steps must be labeled as such in the scenario.
2. **Cover the matrix**: roles (admin/researcher/viewer/stranger where auth-adjacent), light/dark, 375px reflow, keyboard Tab + visible focus, and loading/error/empty states. Mutations use synthetic data only — never golden data, no destructive ops.
3. **Record the verdict** in the scenario's summary plus the coverage map (`tests/simulation/lib/scenario-registry.mjs` and any `coverage-matrix.json`): pass/fail with date, screenshots/HAR paths, and the QA lane used (`docker-compose.qa.yml` `ui` profile, loopback publish only).
4. **Extend the long-form layers when the feature touches them**: team/role flows → `tests/real_user_benchmark/lib/persona.mjs`; donated-compute/model paths → donor/model-management probes; Research Spine paths → spine probes (gates stay non-bypassable, evidence stays provisional until Done-task acceptance).
5. **Keep it green without live dependencies**: new scenarios must pass in the credential-free lane or declare their live requirements (donors, models, third-party keys) and fail closed with `not_runnable` — never silently skip, never fabricate.
6. **Attach suite evidence** as Compass Forge command evidence (scenario command + verdict summary) before finishing the feature's tasks, and update `TESTING.md`/`testing/TEST_HISTORY.md` when the suite topology or release-relevant behavior changes.

Stale scenarios are architecture debt: if a feature change breaks a scenario's selectors, copy, or flow, updating that scenario is part of the feature — not a follow-up.

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

<!-- compass-forge:start -->
# Compass Forge Agent Workflow

Project root: `<REPO_ROOT>` (repo-relative; the literal checkout path must never be committed — see `scripts/public_repo_quality_audit.py` rule `machine_checkout_path`)
Recipe: `istara-main`
Runtime: Rust-only (`compass-forge mcp`).

1. Call `forge.status`, then `forge.agent_brief` for the user's request.
2. For meaningful changes create, clarify, plan, and task a durable spec.
3. Use impact, graph, model, zones, context packs, and a role-specific work order before editing.
4. Run gates before and after; attach command, gate, and review evidence.
5. Preserve independent blind review: freeze the reviewer sheet before revealing implementation evidence, then reconcile.
6. Never invoke a legacy runtime or silently mutate global configuration.

<!-- compass-forge:end -->
