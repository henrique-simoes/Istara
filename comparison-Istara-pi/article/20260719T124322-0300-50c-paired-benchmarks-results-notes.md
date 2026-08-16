# 50c Paired Benchmark Batch Notes

Run artifact: `comparison-Istara-pi/runs/20260719T124322-0300-50c-paired-benchmarks/`

This batch used the Istara harness inventory as the denominator and stayed under the approved USD $0.50 cap. It executed no-model Istara orchestration benchmarks, no-model static evals, Pi replacement lab validation, Pi canonical adapter smoke, and three capped DeepSeek core eval cases through both an Istara-compatible OpenAI path and Pi's DeepSeek provider path.

Empirical replacement claims remain limited: the only counted Pi replacement score in this batch is the deterministic Pi-owned agent loop through `CanonicalToolFacade` for task/finding tools. The live Pi DeepSeek cases are provider-path evidence and are not counted as full replacement evidence until the same contracts run through the Pi-wired adapter loop.

Conservative spend estimate: USD $0.0800 / $0.50.

Update: Pi provider-path live core evals passed after fixing the run-local import path; baseline live JSON cases passed after capped retries. These provider-path results remain excluded from replacement scoring.

Owner clarification update: the batch was extended with no-cost category representatives for the broader interpretation of scenario coverage. Three oversized `other_feature_simulation` representatives (`09-navigation-search`, `43-process-hardening`, `75-participant-simulation`) passed static `node --check`, and the real-user research spine ran `plan-only` to generate the corpus/playbook/scoring scaffold. These additions did not change spend and do not add Pi replacement-score evidence.
