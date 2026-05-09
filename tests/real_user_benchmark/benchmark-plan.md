# Benchmark Plan

## Researcher Persona

Name: Maya Rodrigues

Role: senior UX researcher at Northstar Health, working on a patient-care coordination product used by clinic staff, patients, and family caregivers.

Behavioral model:

- Maya asks open-ended questions, then narrows into evidence checks.
- She uploads messy historical research because real teams inherit imperfect archives.
- She corrects vague summaries and asks Istara to cite sources.
- She creates work, waits for Review, reads the output, approves good work, and sends weak work back with concrete revision instructions.
- She tests third-party setup flows even when she knows credentials are unavailable.

## Project Narrative

Project: CareNav Renewal

Problem: care coordinators lose time reconciling patient tasks across portals, SMS threads, paper notes, and phone calls. Patients and caregivers miss preparation steps before appointments, while staff cannot tell which reminders worked.

Benchmark goals:

- Validate whether Istara can ground recommendations in a large messy corpus.
- Validate whether real donated compute can serve live `google/gemma-4-e4b` chat before research-quality scoring begins.
- Measure whether reports and atomic findings make sense across mixed methods.
- Probe Istara's agentic stack through realistic researcher requests: tool calls, skill calls, RAG, context management, memento/project memory, ReasoningBank, Hyperagent/governed improvement, and ensemble/MoA health.
- Exercise the human review loop instead of assuming agent tasks are done.
- Test whether integrations fail helpfully without credentials.
- Produce reusable evidence that can be compared across product builds.
- Complement, not duplicate, the deterministic coverage already tracked in `tests/simulation`, `tests/evals`, `tests/benchmarks`, and `scripts/security_benchmark.py`.

## Operating Discipline

The benchmark is not a happy-path script. When an action fails, the harness first checks whether the failure came from benchmark misunderstanding: wrong auth mode, stale first-run tour state, frontend runtime config, missing render wait, inaccessible container path, or an unsupported integration credential profile. Only after that architecture check does it log a product issue.

For UI actions, Playwright waits until Istara has rendered a usable state before navigation or chat input. For task review, the benchmark reads the task output, records a human-quality judgment, sends weak work back with specific revision instructions, then approves only after the simulated researcher decides the output is good enough.

For compute, the benchmark treats the donated relay as part of the product under test. Non-plan runs require the configured live model profile by default, verify the relay node through `/api/compute/stats`, and require non-empty chat output before later research tasks can count as successful.

## Corpus

The generator creates:

- interview transcripts
- usability test notes
- survey CSVs
- diary studies
- field notes
- analytics exports
- support tickets
- design critique notes
- competitor reviews
- research readouts and presentation files
- malformed and edge-case files
- multilingual Portuguese and Spanish examples
- URL and web-fetch prompts

The generated corpus intentionally contains overlap, contradictions, missing metadata, and repeated pain points so Istara must synthesize rather than simply list.

## Feature Coverage Matrix

| Feature | Required Evidence |
| --- | --- |
| Sandboxed server install | container/log evidence or blocker |
| Connection string | generated user invite and compute donation string where available |
| Sandboxed client install | relay/client connection attempt or blocker |
| Onboarding UI | Playwright screenshots/traces |
| Project context | project create/update payload and UI evidence |
| Linked folders | backend-visible `/benchmark-results/.../corpus` folder path plus API result |
| Uploads | manifest plus upload responses |
| Chat | 100 JSONL turns in full mode |
| Donated compute | relay/client registration, forced topology or route-log evidence, and live Gemma response |
| Tool/skill calls | natural researcher prompts that require tool or skill attempts, plus trace/observability findings |
| RAG/context | retrieved-source usefulness, citations, contradictions, and context-window stress prompts |
| Memento/ReasoningBank | memory/reasoning-bank request evidence and contamination/grounding review |
| Hyperagent/governed improvement | bounded safe-path attempt and human review of proposed improvement |
| Ensemble/MoA health | compute-health and ensemble-readiness evidence; future Qwen donor remains disabled until provisioned |
| Task review | 50 approved tasks in full mode, with revision examples |
| Loops | overview/config/schedule/custom loop attempts |
| Autoresearch | status/config/toggle/error-path evidence |
| Surveys | Google Forms, SurveyMonkey, Typeform developer/demo path or error path |
| Telegram/AURA | fake Telegram setup, deployment creation, activation, response simulation attempt |
| URL/web fetching | chat/task URL prompts and response quality notes |
| Interfaces | mock Stitch/Figma generation/import, design chat, handoff where possible |
| MCP | server/client status, policy, fake client discovery error path |
| Reports/findings | report and atomic research endpoints or chat-generated artifacts |

## Scoring Rubric

The final score is out of 100:

- install and sandbox behavior: 10
- onboarding and project setup: 8
- corpus ingestion and uploads: 10
- chat quality and naturalness: 10
- grounding and evidence handling: 10
- task execution and human review workflow: 12
- reports, findings, and atomic research: 10
- integrations and graceful degradation: 10
- Autoresearch, loops, and scheduled work: 6
- URL fetching and web context: 4
- interface generation and design handoff: 4
- stability and performance: 4
- overall researcher usefulness: 2

The scorecard includes explanations and product improvement notes, not just numbers.

Storage is part of run hygiene. Colima autostart uses a 10GB root disk and 10GB data disk by default, snapshots actual/apparent usage, and records a product/process finding when the benchmark environment exceeds the 10GB actual or 20GB apparent budgets.

Recurring product findings should be tracked over time rather than discarded. Current expected high-signal findings include lack of a credential-free AURA participant conversation simulator and missing support for realistic archive types such as `.pptx` research readouts and `.jsonl` support-ticket exports.
