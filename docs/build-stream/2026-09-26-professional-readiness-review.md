# Professional-readiness review (2026-09-26)

```yaml
item: professional-readiness-review
branch: plan/professional-readiness-20260926
cf: { spec: CF-SPEC-5, tasks: [CF-45, CF-46, CF-47, CF-48, CF-49, CF-50, CF-51, CF-52, CF-53, CF-54, CF-55, CF-56, CF-57, CF-58] }
phase: "Phase 1 — surveys, channels, deployments"
stage: S2-execute
status: in-progress
blocked_on: null
last: { agent: claude-code, at: 2026-09-27T00:45:00Z, ledger: L-3 }
next_action: "Merge the Phase 1 PR into main once CI is green, merge the main -> testing sync PR, then start Phase 2 (D-12 grounding, D-7 analysis path, D-8 reliability matrix)."
```

## Plan overview

**Question.** Is Istara ready for UX researchers doing professional work? Answer it per area with
measurements and real browser journeys, fix what fails, and end with a dated verdict per area:
*ready*, *ready with caveats*, or *not ready*, each with its evidence.

**Why now.** The previous round found RAG weak (nDCG@10 0.52) and evidence-graph links mostly wrong
(12% supported) while every structural check passed. This plan assumes every other area can hide the
same kind of problem until it is measured.

**Spirit.** Istara is local-first, and every feature that touches research data extends the Research
Spine (`AGENTS.md` §1, `docs/architecture/research-validity-contract.md`). Model output stays
provisional until source-grounded coding, reliability, reconciliation and a human Done gate accept
it. Nothing in this plan creates report evidence by a shortcut.

**Appetite.** One plan, five working phases plus ship. Studio-only execution, synthetic data only,
live spend capped at $1 per run (the three live identities: Muse Spark 1.3 Contributor
`pi-muse-spark`, DeepSeek V4 Flash `pi-deepseek-flash`, the owner's local Qwen3.8-27B
`pi-local-qwen`).

**Non-goals.** New research methods; replacing the coding protocol; any path that bypasses coding,
reliability, reconciliation, the Done gate or the report gate; code signing with the owner's Apple or
Windows certificates (the owner holds those secrets); real third-party channel credentials.

### What the recon found before any measurement (read from the code, 2026-09-26)

These are hypotheses to prove with failing tests first, not conclusions.

| ID | Area | Where | Suspected defect |
|---|---|---|---|
| D-1 | Channels | `services/inbound_processor.py` (intro state) | The participant's first message, sent before any question, is stored as the answer to question 1. |
| D-2 | Channels | `services/adaptive_interview.py::_handle_wrap_up` | The closing question is sent together with "thank you" and the conversation is marked completed, so its answer is never recorded. |
| D-3 | Deployments | `DeploymentWizard.tsx` vs `adaptive_interview.py` | The wizard saves `adaptive_enabled` / `max_follow_ups`; the backend reads `adaptive` / `max_probes_per_question`. The adaptive toggle does nothing. |
| D-4 | Deployments | `inbound_processor.py`, `deployment_service.py` | `target_responses` is display-only: no quota closes a deployment. |
| D-5 | Deployments | whole flow | No informed-consent step: answers are stored before, and regardless of, consent. No screener. No reminders. |
| D-6 | Surveys | `api/routes/surveys.py::sync_responses` | Every sync re-ingests every response (the adapters return all responses), duplicating nuggets and evidence units and inflating `response_count`. |
| D-7 | Surveys, channels | ingestion paths | Answers become evidence units, but nothing starts governed coding or names a path to a report. |
| D-8 | Coding | `core/research_validity.py::normalize_coder_applications` | The reliability matrix treats each coder's exact **set** of free-text labels as one nominal category (case- and spelling-sensitive), although the protocol asks for one `primary_code` for nominal reliability. The saved three-identity run coded with **no codebook** (`codebook_version_id: null`). |
| D-9 | Reports | `api/routes/reports.py`, `ProjectReportsView.tsx` | No report export (Markdown, DOCX, PDF, CSV). Project export writes to the server's disk, which a browser user on Docker cannot reach. |
| D-10 | Installers | `.github/workflows/build-installers.yml` | `tauri build` runs with `continue-on-error`: all three platform builds fail (Windows MSI rejects CalVer minor 305 > 255; Linux lacks the updater signing key; macOS codesign import fails), the workflow is green, and each main push publishes a release with only a DMG and a `latest.json` with empty signatures. |
| D-11 | Installers | `homebrew/istara.rb`, tap repo | The cask pins 2026.03.30.6; the tap was last pushed 2026-03-30. `VERSION` says 2026.05.27.3 while the latest tag is v2026.09.26.6. |
| D-12 | Spine | `core/agent_research.py` (skill nugget storage), `research_validity_reconciliation.py::_task_finding_support_diagnostics` | No skill sets `source_document_id` on its nuggets, so every skill nugget is stored as a `candidate_atom`, no coding run starts, and the report gate (every task nugget needs an accepted coded unit) can never pass: skill output may never reach a report through the product path. |
| D-13 | Channels | `inbound_processor.py` | A participant of a paused or closed study fell through to the project agent path (fixed in Phase 1, DEC-7). |
| D-14 | Skills | `skills/discover/user_interviews.py` | Each transcript is cut to its first 4,000 characters before analysis; Harbor interviews are 21,000-29,000 characters, so 80-85% of every interview is never read. |
| D-15 | Skills | `user_interviews.py` | When one input file fails to load, every later transcript's nuggets carry the wrong file name. |
| D-16 | Skills | `skills/skill_factory.py` (generic runner behind most skills) | Input is capped at 4,000 characters for the whole task across all files, then fitted to a 4,096-token context with 1,024 output tokens: a thematic analysis of the 498,690-character Harbor study reads under 1% of it. |
| D-17 | Skills | `skill_factory.py::_deterministic_findings_from_research_data` | When a model returns no findings, the runner stores meta-statements ("Input contains N evidence lines", "Review the source data and rerun the skill") as project facts, insights and recommendations. |
| D-18 | Skills | `core/agent_research.py` (task skill input) | A task's `input_document_ids` never reached its skill (the ReAct path read the whole project folder; the DAG path passed no files), so "analyse these interviews" analysed whatever the folder held. |
| D-19 | Coding | `services/research_validity_service.py::run_independent_coding_run` | Every unit of a run (up to 200) went to each coder in one prompt as its full database record: about 114,000 input and 40,000-55,000 output tokens per coder on the Harbor study. The owner's local model timed out after 584 s, so a three-model run including it could not complete. |
| D-20 | Installers | `main.py` lifespan (vector-space invariant) | A fresh native install, which has no local model yet, refused to start: the embedding probe could not reach a model and startup aborted, so the user never reached the settings that configure one. Both engines embed through one gateway, so the refusal protected nothing. |
| D-21 | Installers | `scripts/install-istara.sh` | On Linux the curl installer offered to install Homebrew for a missing Python or Node ("required ... on macOS"), and used `sudo apt-get` for ffmpeg, which fails as root in a container. |
| D-22 | Installers | `backend/Dockerfile`, `qa/Dockerfile`, `api/routes/updates.py` | Docker images shipped no `VERSION`, so the status bar read "Istara vunknown"; a checkout read its stale `VERSION` before its release tag, so the update checker offered the release it was running. |
| D-23 | Skills | `skills/discover/contextual_inquiry.py`, `diary_studies.py` | Both skills computed pain points and opportunities, then stored nuggets only: no facts, insights or recommendations, although their definitions promise them (SK1). |

## Pre-registered readiness criteria (DEC-2, fixed before any number)

Verdict rule for every area: **ready** when every criterion passes; **ready with caveats** when every
*Blocker* criterion passes and each failing non-Blocker criterion is documented with its residual
risk; **not ready** when any Blocker criterion fails. Deterministic criteria are exact (a count, not
an estimate). Model-dependent criteria report a point estimate with a 95% bootstrap interval
(2,000 resamples, seed 7) and, where two arms are compared, a paired sign-flip randomization test
(10,000 permutations) with Holm correction across the family named in the row.

### Area 1 — menus nobody has walked (and Area 5 — UX)

| ID | Criterion | Measure | Pass | Blocker |
|---|---|---|---|---|
| U1 | Every view in `HomeClient.tsx` and every tab/sub-menu inside it is walked in a browser in this plan | views and tabs walked / total | 1.00 | yes |
| U2 | Each walked surface is checked for happy path, empty, loading, error, 375 px (nothing cut off), dark via the app toggle, keyboard focus | states checked / states applicable | 1.00 | yes |
| U3 | No open Blocker or Major UI defect (dead end, silent failure, control that does nothing, text cut off, unreadable contrast, action with no feedback) | open Blocker+Major | 0 | yes |
| U4 | Each fixed defect has a Playwright scenario step that fails on `main` and passes after | fixed defects with a scenario step / fixed defects | 1.00 | no |
| U5 | Every coverage-matrix row carries a verdict dated in this plan | rows dated 2026-09-26 or later / rows | 1.00 | no |

### Area 2 — surveys, channels, deployments

Measured with synthetic participants driven through the stub Slack, Telegram and WhatsApp adapters
(`simulate-inbound`) and a stub survey platform; real third-party credentials fail closed as
`not_runnable`.

| ID | Criterion | Measure | Pass | Blocker |
|---|---|---|---|---|
| S1 | Answer attribution: each stored answer names the question the participant was actually shown | correct / stored answers, 30 scripted conversations (10 per channel) | 1.00 | yes |
| S2 | Answer completeness: every answer given, including the closing question, is stored exactly once | stored-once / given | 1.00 | yes |
| S3 | Consent: no answer is stored before consent; a participant who declines gets no stored answer and no further questions | violations | 0 | yes |
| S4 | Quota: a deployment stops accepting new participants at its target | conversations started past target | 0 | no |
| S5 | Survey re-sync is idempotent | duplicate evidence units after 3 syncs of the same responses | 0 | yes |
| S6 | Spine entry: every stored answer has an evidence unit whose `source_text` contains the answer verbatim; answers can be coded by a governed three-model run, reconciled, and reach a report only through an approved Done task | span fidelity; path proven end to end (live) | 1.00; yes | yes |
| S7 | Researcher needs when preparing and sending: consent, screener, quota, reminders, raw-data export (CSV) — each present and working in the browser | present-and-working / 5 | 5/5 ready; ≥ 3/5 caveats | no |
| S8 | Adaptive follow-up setting in the UI changes behaviour | toggle honoured (test) | yes | no |

### Area 3 — Research Spine features

| ID | Criterion | Measure | Pass | Blocker |
|---|---|---|---|---|
| C1 | Coding agreement is measured correctly: the reliability matrix follows the protocol's nominal `primary_code` rule with label normalisation, and a construction test shows known-agreeing coders score κ = 1 and known-disagreeing coders κ ≤ 0 | unit tests | pass | yes |
| C2 | Diagnosis of near-zero agreement: three live coders on ≥ 40 Harbor evidence units, arm A = no codebook (today's default), arm B = a Harbor codebook with definitions and inclusion/exclusion criteria. Report κ and α per arm, per-coder accuracy against the planted theme (span-graded truth), and the paired difference (units as pairs) | κ_B − κ_A, accuracy per coder | Decision rule DEC-3 | no |
| C3 | With a codebook, three-model agreement reaches the product's own threshold on Harbor | Fleiss κ (arm B) | ≥ 0.60 ready; 0.40–0.60 caveats; < 0.40 not ready | no |
| C4 | Codebook versioning: a new version never rewrites an old one; runs record the version they used; coders receive definitions and inclusion/exclusion criteria | tests + prompt inspection | pass | yes |
| R0 | End to end through the product: Harbor interviews uploaded, the `user-interviews` skill run as a Kanban task, codes reviewed, task approved → a report exists | report produced with ≥ 1 finding | yes | yes |
| R1 | Every claim in a generated report traces to an exact source span (G1 walk) | traced / claims | 1.00 | yes |
| R2 | Report gate: In Review tasks, unreconciled codes and provisional findings never appear in a report | seeded-fault tests | pass | yes |
| R3 | Export formats researchers use: a report downloads from the browser as Markdown and DOCX with source citations, and the coded data as CSV | formats working in browser | 3/3 | no |
| K1 | Kanban: only a human with researcher+ role moves a task to Done; agents cannot; viewer cannot; approval is recorded | role-matrix tests + browser | pass | yes |
| A1 | Agents creating agents: a proposal carries evidence, needs human approval, and never self-activates; a created agent inherits the spine gates | tests + audit | pass | yes |
| E1 | Skills evolving (skill factory, self-evolution, meta-hyperagent, autoresearch) meet the governance contract: no strong signal from raw success, no global mutation from project evidence, no report evidence created | contract-clause audit with a test per clause | every clause has a passing guard test | yes |
| SK1 | Findings-producing skills: none silently returns zero facts for a valid single input when its schema promises facts | skills with the gap | 0 (or documented) | no |
| SK2 | A skill reads all of its input: characters of the task's source files delivered to the model across all calls / source characters (Harbor, 16 interviews) | coverage | ≥ 0.99 | yes |
| SK3 | Analysis finds what is in the data: themes (of 10 planted Harbor themes) with at least one output nugget grounded in a span overlapping a planted quote of that theme; `user-interviews` and `thematic-analysis`, each of the three live models | theme recall; paired randomization before vs after over theme × model (30 pairs), Holm over the two skills | ≥ 0.80 per model, and significantly higher than before | no |
| SK4 | No finding is written without model content from the data (no deterministic meta-findings) | fabricated findings in a test that forces an empty model answer | 0 | yes |
| G1 | Evidence-graph links: fact→nugget supported share (judged, validated judge) | re-measure after changes | improve on 0.65; ≥ 0.75 target | no |
| G2 | Context-DAG summary recall of planted facts | re-measure | improve on 0.48; ≥ 0.60 target | no |
| G3 | Graph-assisted retrieval ships only by the DEC-2 rule of the graph plan (coverage@10 significantly higher, no v2 style significantly worse, Holm) | paired test | rule | no |

### Area 4 — installers

| ID | Criterion | Measure | Pass | Blocker |
|---|---|---|---|---|
| I1 | The release workflow fails when a platform build fails (no silent green) | workflow contract test | pass | yes |
| I2 | Each published channel installs the current version: DMG, Linux AppImage/deb, Windows installer, Homebrew cask, curl one-liner, Docker compose | channels verified current / channels | all reachable ones | yes |
| I3 | Fresh install on the Studio (macOS) and in Linux containers reaches first run with clear first-run guidance | fresh-install journeys | pass | yes |
| I4 | `VERSION` equals the latest tag; the Homebrew cask updates automatically | drift | 0 | no |
| I5 | What cannot be verified is stated (Windows without a machine; signing without the owner's certificates) | honesty | stated | yes |

## Phases

| Phase | Goal | Acceptance | Verification |
|---|---|---|---|
| 1 Surveys, channels, deployments | fix D-1 to D-7; consent, screener, quota, reminders, CSV export; prove S1-S8 | S1-S8 | pytest (fail on `main` first), scenario 89, live spine run |
| 2 Spine quality | D-8 fix; C1-C4; R1-R3 (report export); K1; A1; E1; SK1; G1-G3 re-measured | Area 3 table | pytest, live runs, scenario steps |
| 3 Menus and UX | walk every view and tab (U1-U5); fix defects; scenarios; refresh stale verdicts | Areas 1 and 5 | browser walk on the QA `ui` lane, scenarios |
| 4 Installers | D-10, D-11; I1-I5 | Area 4 | workflow run, fresh installs on the Studio and in Linux containers |
| 5 Ship | docs, map, readiness report (Artifact), PRs merged, `main` = `testing`, lane torn down | all verdicts dated | governance checks, `verify_lifecycle.py` |

Each phase lands as its own PR into `main` followed by a `main → testing` sync PR (DEC-1).

**Rollback.** Every behaviour change is behind a test; consent, screener and quota are deployment
settings defaulting to the old behaviour only where a researcher has not configured them (consent
defaults on for new deployments, DEC-4). The reliability-matrix change is a methodology fix recorded
as a decision with its evidence; old runs keep their stored metrics.

**Top risks.** Live coder variance at small n (bound by ≥ 40 units and bootstrap intervals);
installer signing needs owner-held secrets (state it, do not fake it); browser walk breadth (24 views
× tabs × states) — the walk is recorded as a table, not narrated.

## Decision log

DEC-1 | 2026-09-26 | S0-frame | owner
Context: the owner's handoff prompt of 2026-09-26 ("Istara — professional-readiness review").
Decision: frame approved by the handoff: review, measure, fix and prove the five areas; work
autonomously; branch, commit, push, open and merge PRs once required CI is green; after any
direct-to-`main` merge, merge a `main → testing` sync PR in the same session; no subagents; review
coverage self-only; Studio-only execution; synthetic data; $1 per live run.
Why: owner instruction. This is the plan's only owner gate.

DEC-2 | 2026-09-26 | S1-plan | claude-code (pre-registered before any number)
Context: the handoff asks for pre-registered criteria per area.
Decision: the criteria tables above, with the verdict rule stated at their head, are fixed now.
A criterion may be tightened later but never loosened; any change is a new DEC with its reason.
Why: fixing the bar before the numbers is what makes the verdicts evidence rather than narrative.

DEC-3 | 2026-09-26 | S1-plan | claude-code (pre-registered before any number)
Context: C2 asks why three-model agreement is near zero.
Decision: attribute the cause by these rules, in order. (a) **Metric artifact** if, on the same
coder outputs, κ on normalised `primary_code` exceeds κ on exact label sets by ≥ 0.20. (b)
**Codebook** if κ_B − κ_A ≥ 0.20 with the paired test significant (p < 0.05, Holm over κ and α).
(c) **Prompt / model** if in arm B at least one coder's accuracy against the planted theme is
< 0.60 while the others are ≥ 0.70. (d) **Genuine ambiguity** if in arm B every coder's accuracy is
≥ 0.70 and κ_B is still < 0.40 (coders are right about different, defensible codes). More than one
cause may hold; each is reported with its numbers.
Why: separates the four explanations the handoff names using quantities fixed in advance.

DEC-4 | 2026-09-26 | S1-plan | claude-code
Context: D-5; professional research requires informed consent before data collection.
Decision: new deployments ask for consent by default (a researcher can edit the text, and can turn
it off only with an explicit setting that is shown on the deployment card). Until the participant
consents, nothing they send is stored as research data; a decline ends the conversation politely
and stores only a consent-declined marker with no content. Existing deployments keep their
behaviour (no retroactive consent prompt mid-conversation).
Why: consent-before-collection is the norm (ESOMAR/ICC, GDPR Art. 6/7); making it default-on is
the safe choice, and not retrofitting it avoids breaking live conversations.

DEC-5 | 2026-09-26 | S1-plan | claude-code (pre-registered before any number)
Context: recon found D-12 after DEC-2 was written.
Decision: add R0 (Blocker) to Area 3. A fix may ground a skill nugget in a source document only by
exact, contiguous substring match against the task's own input documents (no fuzzy match, no
model judgement); an ungrounded nugget stays a candidate.
Why: tightening is allowed by DEC-2; exact-substring grounding keeps the contract's rule that
evidence units come from raw source spans.

DEC-6 | 2026-09-27 | S2-execute | claude-code
Context: D-1/D-2 needed a rule for which participant messages are research data.
Decision: every message the engine sends records `pending_prompt` (kind, exact text, question
index); a reply is stored only when it answers a pending question, follow-up probe or closing
question, attributed to that exact text. A captured answer's evidence unit holds the answer only;
the question is kept as `prompt_text` and passed to coders as `asked` context.
Why: attribution by position (the old `current_question_index - 1`) mis-files any reply that is
not an answer (greeting, consent, screener, STOP); storing the researcher's question as a codable
unit would let coders code the researcher's words as participant data.

DEC-7 | 2026-09-27 | S2-execute | claude-code
Context: D-13 found in the walk: when a study is paused or closed, a participant's next message
fell through to the project's Pi agent path (off by default via `pi_replacement_enabled`, but with
no sender allowlist when on).
Decision: a sender with any conversation in a non-active study on that channel is never routed to
the agent: unfinished participants get the paused/closed notice, finished ones get silence. The
missing sender allowlist for opt-in channel agent replies is recorded as residual risk R-1, not
fixed in this plan (it is off on every shipped configuration).
Why: participants must never reach an agent that can read project research data; the allowlist is
a separate security feature with its own design.

DEC-8 | 2026-09-27 | S2-execute | claude-code (pre-registered before any number)
Context: recon of the skill engine found D-14, D-16 and D-17 after DEC-2 and DEC-5.
Decision: add SK2 (Blocker), SK3 and SK4 (Blocker) to Area 3, fixed now. SK3 runs on the 16 Harbor
interviews (the thematic qrels' planted quotes are the truth; a nugget counts for a theme when its
grounded span overlaps a planted quote of that theme by at least 40 characters), `user-interviews`
and `thematic-analysis`, each of the three live identities, before (`main`) and after; $1 cap per
model and arm, stopping a run that would exceed it and reporting it incomplete.
Why: an analysis that reads under 1% of a study cannot be professional, however well the gates
behind it work; theme recall against planted quotes is span-graded truth, like M1-M3.

DEC-9 | 2026-09-27 | S2-execute | claude-code
Context: how to make skills read all of their input without breaking small local models.
Decision: size each skill call to the endpoint that serves it: its declared context window, bounded
by a ceiling (`skill_execute_context_ceiling_tokens`, 32,768) and never below the existing
`skill_execute_context_limit_tokens`; output up to the endpoint's `max_tokens`, bounded at 8,192.
Split the full input into windows at paragraph boundaries, each labelled with its source file;
run the existing single-call path (with its repair chain) once per window; merge window nuggets;
then one synthesis pass over the merged, labelled nuggets produces facts, insights and
recommendations, which link to nuggets by meaning as before. The deterministic fallback keeps no
findings (the run reports that the model returned none).
Why: map-reduce over labelled windows is the standard way to cover long corpora with bounded
context (local-first: a 4k local model still works, with more windows); reusing the single-call
path keeps the proven repair chain; synthesising over nuggets rather than raw windows keeps facts
tied to evidence.

DEC-10 | 2026-09-27 | S2-execute | claude-code (before any SK3 number)
Context: DEC-8 grades SK3 on grounded spans, but the `main` arm has no grounding (D-12), so its
nuggets have no spans to grade.
Decision: SK3 grades both arms the same way: a theme counts when one of the run's nuggets shares at
least 40 contiguous characters (case and whitespace aside) with one of that theme's planted quotes
(`app/evals/skill_theme_eval.py`). The share of nuggets stored as exact source spans is reported
beside it for the after arm. The pass bar (>= 0.80 per model, significantly above before) is
unchanged.
Why: one metric for both arms keeps the comparison paired and fair; grounding is measured
separately rather than folded into recall.

DEC-11 | 2026-09-27 | S2-execute | claude-code
Context: D-19; the coding prompt grew with the run and carried whole database records.
Decision: a coder receives only the fields it codes with (id, stable id, index, source type,
participant, speaker, location, text, and the question asked), in batches of at most
`research_validity_coding_units_per_call` (20) units and about
`research_validity_coding_chars_per_call` (12,000) characters. Every coder codes the same batches;
each batch keeps the existing repair chain; a coder still has to code every unit of the run or it
is dropped, as before. The prompt hash covers all batches.
Why: local-first means the smallest coder, the owner's local model, must be able to take part;
identical batches keep the reliability comparison like with like.

DEC-12 | 2026-09-27 | S2-execute | claude-code
Context: D-20; a fresh install without a reachable embedding model refused to start.
Decision: at startup an unreachable embedding model is recorded as `unverified` with a warning and
startup continues; a proven divergence (both engines answering with different models or
dimensions) still refuses to start.
Why: both engines embed through the one Pi gateway (`AgenticDispatcher.embed`), so they cannot
diverge while the model is down, and every stored vector stays bound to its model fingerprint; the
refusal locked out every new native user.

## Ledger

### L-1 | 2026-09-26T21:10:00Z | S0-frame | claude-code | framer | —
Did: read the handoff; oriented on `main` = `testing` = 06545a8a; gated the CF binary (all seven
probes pass); refreshed the CF index; read the survey, channel, deployment, codebook, reliability,
report, release-workflow and Homebrew code paths; pulled the latest release and its build logs.
Result: frame written with 11 recon hypotheses (D-1 to D-11) and pre-registered criteria (DEC-2,
DEC-3). Every desktop build in run 36263309378 failed while the workflow reported success.
Verified: `gh run view 36263309378 --log` (three `Error failed to bundle project` lines);
`gh release view v2026.09.26.6` (assets: DMG, latest.json only); code reads cited in the D table.
Next: CF spec, then Phase 1 failing tests.

### L-2 | 2026-09-27T00:40:00Z | S2-execute | claude-code | executor | Phase 1
Did: CF-SPEC-5 created, clarified, planned, tasked (CF-45..58); gate before on CF-45. Failing tests
first (`tests/test_deployment_participant_flow.py`, `tests/test_deployment_research_ops.py`: 16
red, 4 green on `main`, the greeting stored as the Q1 answer and an empty probe confirmed). Fixed
D-1 to D-6 and the walk's findings: engine rewritten around `pending_prompt` (consent, screener,
closing, STOP, quota, failed-probe fallback, both adaptive key spellings); inbound attribution,
quota and held-study routing; reminder sweep in the scheduler tick; consent on by default for new
deployments (DEC-4); pseudonymous CSV exports for deployments and survey links; survey re-sync
idempotent; answer-only evidence units (DEC-6). UI: wizard step "Consent & Screening", wrap-up and
reminder settings, visible errors; dashboard live refresh, state feedback, Resume, Export CSV,
plain-word outcomes, real overview counts, role gating (viewers cannot create or export); Surveys
tab no longer pre-fills sample answers or invents "No response provided", reports sync results,
exports CSV. Persona protocols, Tech.md and three researcher feature docs rewritten to match.
Result: see Phase 1 results.
Verified: Studio `pr-pytest.sh` 107 then 80 and 47 passed on the Phase 1 suites; `tsc --noEmit`
clean; eslint 0 errors (touched files clean); frontend unit 124/124; simulation static 41/41;
scenario 89 27/27 (run 2026-09-27T00-14-34-198Z) and 3/9 on a `main` lane (run
2026-09-27T00-17-30-405Z); `python -m app.evals.study_capture_eval` before/after (below);
`check_change_obligations.py` and `check_feature_obligations.py` pass; feature docs check passes.
Next: full backend suite on the Studio, then the Phase 1 PR into `main` and the sync PR.

## Phase 1 — surveys, channels, deployments

Results (2026-09-27). S1-S5 from `python -m app.evals.study_capture_eval` on the Studio (30
synthetic participants, 10 per channel, seed 7; 30 survey responses synced three times), exact
counts; before = `origin/main` 06545a8a, after = this branch. Reports in
`~/cf-remote/eval/measure/readiness-0926/s1-s5-*.json` (Studio).

| Criterion | Before | After | Pass bar | Verdict |
|---|---|---|---|---|
| S1 attribution (stored answers filed under the prompt shown) | 0 / 116 (15 real answers misfiled, 101 non-answers stored) | **55 / 55** | 1.00 | pass |
| S2 completeness (answers given stored exactly once, closing included) | 0 / 55 | **55 / 55** | 1.00 | pass |
| S3 non-research data stored (before consent, declined, screened out, after STOP) | 101 | **0** | 0 | pass |
| S4 quota (participants past the target with answers stored) | 9 of 9 | **0 of 9** | 0 | pass |
| S5 survey re-sync (duplicate evidence units after 3 syncs of 30 responses) | 360 (response count 90) | **0** (response count 30) | 0 | pass |
| S6 spine entry (answers coded, reconciled, reported through a Done task) | no path | not yet: needs D-7/D-12 (Phase 2) | proven live | open |
| S7 consent, screener, quota, reminders, raw export in the browser | 0 / 5 | **5 / 5** (scenario 89; reminders by test, set in the wizard) | 5/5 | pass |
| S8 adaptive setting honoured | no (key mismatch) | **yes** (tests) | yes | pass |

Found on the way and fixed, each with a test or scenario step: the dashboard's "Active Now" never
listed anyone (it filtered on a state deployment conversations never have); the question badge was
off by one; Activate/Pause/Complete gave no feedback and swallowed errors; the overview cards
summed the wrong numbers and one was a hard-coded "--"; the live feed and progress never refreshed;
the action row was cut off at 375 px; viewers were offered "New Deployment"; the Questionnaire
Studio came pre-filled with caregiver answers, stored empty answers as "No response provided" and
always reported 0 nuggets; a paused study handed participants to the project agent path; a
participant's "Q:" line became a codable evidence unit.

Residual: R-1 opt-in channel agent replies (`pi_replacement_enabled`) have no sender allowlist
(off on every shipped configuration). Diary-study pacing between prompts is not scheduled.

### L-3 | 2026-09-27T00:45:00Z | S2-execute | claude-code | executor | Phase 1
Did: brought the CF gate to zero new warnings: split `process_inbound_channel_message` into named
steps; rebuilt the wizard as one component per step around a pure `deploymentDraft.ts` (unit
tested); split the Surveys tab (`QuestionnaireStudio`, `LinkedSurveysTable`, `SurveyPlatformCards`,
`useLinkedSurveys`) and the dashboard header; moved scenario 89's helpers to
`lib/study-journey.mjs`; added both export routes to the route-coverage list; one expiring,
reasoned suppression for scenario 89's symbol count (same inherited class as scenarios 10, 20-22,
29, 86). Found while splitting: studio-recorded surveys never appeared under Linked Surveys (so could
not be exported), Sync was offered for them, "Request Platform" and non-admin removal gave no
feedback, link-list and removal failures were silent, and the Typeform badge text failed contrast in
dark mode; all fixed. Updated three source-string contract tests to follow the moved code (same
project-scoping intent).
Result: gate after 0 new failures, 0 new warnings; scenario 89 still 27/27.
Verified: `compass-forge gate after --task CF-45 --summary` (new_failures 0, new_warnings 0);
Studio full backend suite `-m "not live_llm" --continue-on-collection-errors`: branch 2,587 passed,
3 failed + 1 error; `origin/main` 2,554 passed, 3 failed + 1 error, the same four (network-dependent
breached-password check, repo-audit and update tests that need a git checkout, `hypothesis` missing
from `istara-test:1`); `tsc` clean, vitest 127/127, eslint 0 errors; scenario 89 27/27 (run
2026-09-27T00-36-33-370Z); change and feature obligations, security benchmark, public-repo audit and
`git diff --check` pass.
Next: PR into `main`, CI, merge, sync PR.
