# Run Status

Run: `20260719T124322-0300-50c-paired-benchmarks`

Status: complete
Updated: 2026-07-19T15:58:33.270Z
Hard cap: USD $0.50
Spend used: USD $0.0800 conservative estimate
Budget remaining: USD $0.4200 conservative estimate

## Completed

- Scenario inventory over Istara harness backbone: 117 items.
- Command validations passed: 5/5 after rerunning the Pi live evaluator with absolute package imports.
- Baseline live DeepSeek core eval final cases: 3 selected, 3 passed after 2 capped retries for truncation-sensitive JSON cases.
- Pi live DeepSeek provider-path core eval cases: 3 selected, 3 passed.
- Pi replacement-scored deterministic adapter scenario: `chat.tool_loop.task_and_finding`.
- Owner clarification extension: 3/3 selected broad simulation representatives passed static no-model `node --check`.
- Owner clarification extension: real-user benchmark `plan-only` representative generated the credential-free corpus/playbook/scoring scaffold with the expected live-services-not-attempted blocker.

## Blocked Or Deferred

- `71-plan-and-execute`: real plan lifecycle/review-state adapter missing in Pi sidecar.
- `31-task-documents-tools`: document attach/detach and chat endpoint adapters missing.
- `23-memory-view`: persistent RAG/memory backend adapter missing.
- `53-channel-lifecycle`: channel lifecycle adapter missing; real credentials intentionally unused.
- `73-a2a-debate-and-reports`: A2A service/report adapter missing beyond facade schema.
- Full real-user probe/full modes: deferred because they require live app services, donated compute/live chat, or sandbox orchestration.
- Full simulation runtime flows beyond static validation: deferred because they require browser/API services and can mutate test app state.
- `security_or_external_service`: remains inventory-only because representative execution would require security-sensitive service/auth paths or external credentials.

## Notes

Replacement scoring only counts the Pi canonical adapter loop. Pi live provider results are useful package/provider evidence, not full replacement scores.

Final Compass Forge gate: `warn`, zero failures, zero new failures, zero drift, zero
security findings; warnings are inherited file-size complexity warnings.
