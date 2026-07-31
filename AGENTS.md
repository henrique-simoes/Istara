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
