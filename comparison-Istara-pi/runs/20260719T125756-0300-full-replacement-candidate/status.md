# Run Status

Run: `20260719T125756-0300-full-replacement-candidate`
Status: complete with conductor limitation recorded
Updated: `2026-07-19T13:31:31-03:00`

## Outcome

Implemented a materially broader isolated Pi replacement candidate in `/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`.

The Pi candidate now runs eight representative Istara harness-derived scenario families through Pi-owned `Agent` loops and canonical Istara envelopes:

- chat/tool loop
- plan-and-execute/task lifecycle
- documents/tools
- structured outputs/core evals
- memory/RAG
- skills, capped at three skills
- A2A delegation/reporting
- channel lifecycle simulated turn

Pi ai live provider routing was also rechecked against DeepSeek `deepseek-v4-pro` with one small smoke.

## Raw LLM Evidence

Raw prompt/input and model-output evidence is stored separately from scoring and analysis:

- `raw-llm-calls/prompts.jsonl.gz`: 22 records.
- `raw-llm-calls/outputs.jsonl.gz`: 22 records.
- `raw-llm-calls/manifest.json`: schema, counts, redaction/capping policy, and reconstruction notes.

Coverage:

- Pi candidate deterministic faux-provider calls: 21 reconstructed records from the scenario catalog, including messages, tool schemas, settings, full content blocks, tool-call requests, and redaction metadata.
- Pi candidate DeepSeek smoke: 1 reconstructed record from the fixed smoke prompt, prior raw capture, and `live-provider-smoke.json`; no new live call was made.
- Baseline Istara deterministic contract runner: 0 LLM calls.
- Missing raw capture: none identified for this run. Earlier native pytest slices did not perform live LLM calls.

Inspection:

```bash
gzip -cd comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/raw-llm-calls/prompts.jsonl.gz
gzip -cd comparison-Istara-pi/runs/20260719T125756-0300-full-replacement-candidate/raw-llm-calls/outputs.jsonl.gz
```

## Build Stream Conductor Compliance

After the owner clarified that `/skill build-stream-conductor` was specifically required, I loaded the Build Stream Conductor, Build Stream, and Compass Forge skill contracts and ran a compliance pass.

Literal Build Stream Conductor pipeline: blocked / not used for this completed implementation round. The project has no `.compass-forge/conductor/cast.json`, `conductor.py status --brief` fails on the missing cast, and `scorecard.py` returns no model attribution rows. Because the clarification arrived after the implementation/test run, I did not fabricate conductor-owned CF tasks, stage attribution, or reviewer verdicts.

Closest compliant structure now recorded:

- `build-stream-lifecycle.md`: Build Stream status block, decision log, and append-only ledger with role/model attribution.
- `build-stream-conductor-compliance.md`: conductor probe outputs, routing registry, scorecard, and next literal-conductor path.
- Manual role-separated lanes: Architect A, Architect B, Architect C/reviewer, remediator, and compliance reviewer.

## Test Results

- Baseline native contract/eval tests: 12 passed.
- Baseline native orchestration benchmark: 5 passed.
- Candidate adapter tests: 4 passed.
- Paired deterministic baseline/candidate scenarios: baseline 8/8, candidate 8/8.
- DeepSeek smoke: passed, 47 tokens, USD 0.00003654 provider-reported cost.

Post-compliance rerun:

- `npm run validate` -> 4 passed.
- `npm run collect:artifacts -- --out .../20260719T125756-0300-full-replacement-candidate` -> baseline 8/8, candidate 8/8.
- `pytest tests/test_agentic_eval_contract.py tests/test_istara_eval_runner.py tests/benchmarks/test_orchestration.py -q` -> 17 passed.
- Gzip and JSON artifact integrity checks passed.

Raw-capture rerun:

- `npm run validate` -> 4 passed.
- `npm run collect:artifacts -- --out .../20260719T125756-0300-full-replacement-candidate` -> regenerated raw LLM evidence and scores with 22 prompt/output records.

## Spend Ledger

Opening prior comparison run ledger: USD 0.0800 used, USD 0.4200 remaining under the owner cap.
This run initiated one live DeepSeek call: USD 0.00003654 provider-reported cost.
Conservative cumulative comparison ledger: USD 0.0801 used, USD 0.4199 remaining.

## Not Full Replacement Yet

Production Istara routes, databases, persistent RAG/LanceDB, real A2A services, real channel credentials/lifecycle, full skill registry/memento, and live broad scenario scoring are not wired. The candidate is a robust sidecar harness for the next adapter round, not a production replacement claim.

The run is also not a literal Build Stream Conductor run. Another round is needed if the owner needs conductor-owned S2-S4 evidence rather than the partial compliance addendum above.
