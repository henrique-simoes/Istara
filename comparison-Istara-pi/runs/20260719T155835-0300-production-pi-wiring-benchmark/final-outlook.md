# Final Outlook

This round moved the Pi candidate beyond a lab-only bridge in the replacement worktree. The candidate is now opt-in behind a request header/env flag and is wired into real Istara chat SSE/tool-loop execution, runtime DeepSeek compute-node registration, production telemetry spans, A2A `tasks/send` observability after JSON-RPC gates, and a credential-free `pi_local` channel adapter through the real channel router and inbound processor.

The benchmark remains valid for comparison: deterministic baseline Istara passed 15/15 scenarios, deterministic Pi candidate passed 15/15 scenarios, and all 15 scenarios are marked `baseline-run`, `pi-candidate-run`, and `deterministic-covered`. The raw LLM capture contains 45 prompt rows and 45 output rows: 41 reconstructed faux-provider fixture calls plus 4 direct DeepSeek calls (`provider.deepseek_v4_pro`, `role.planner`, `role.architect`, `role.plan-reviewer`). The `role.code-reviewer` lane did not complete because the role-round script stopped producing stdout and was interrupted to protect the cap.

Pi is now a serious experimental production replacement candidate for the agentic loop surface, but it is not production-ready. Remaining blockers are production human Done/report approval state, production source-unit/evidence-chain writes for all artifact paths, full memory/RAG/ReasoningBank/Memento/skill-stat fanout, real external channel credentials, real Autoresearch engine mutation under governance, live steering interruption, and broader browser/API/real-user benchmark fanout under a larger live budget.

Spend: estimated added DeepSeek spend is USD 0.00650856, leaving USD 0.40252845 of the original USD 0.50 cap by the artifact estimator.
