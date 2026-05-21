# Bibliography Audit

Spec: CF-SPEC-123 / CF-1581

The audit prefers primary arXiv, W3C, DOI, ACM, publisher, or official project sources. Secondary summaries should not drive Istara claims.

| Reference | Primary URL | Istara Feature | Current Wording Guidance |
| --- | --- | --- | --- |
| Fleiss, J. L. (1971). "Measuring nominal scale agreement among many raters." Psychological Bulletin, 76(5), 378-382. DOI 10.1037/h0031619. | https://doi.org/10.1037/h0031619 | Consensus/Kappa | Use for the formula and item-by-rater categorical agreement. Do not claim Istara's keyword-category response matrix is a formal human-coding reliability study. |
| Wang et al. (2024). "Mixture-of-Agents Enhances Large Language Model Capabilities." | https://arxiv.org/abs/2406.04692 | Multi-model validation | Use as inspiration for aggregating multiple model outputs. Do not claim Istara exactly implements layered MoA unless code does so. |
| Du et al. (2023/2024). "Improving Factuality and Reasoning in Language Models through Multiagent Debate." | https://arxiv.org/abs/2305.14325 | Debate/adversarial validation | Use for debate/refinement inspiration. Record route identity if claiming distinct model debate. |
| "Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?" / Self-MoA. | https://arxiv.org/abs/2502.00674 | Self-MoA fallback | Use to describe single-model ensembling as a constrained-compute fallback, not as equivalent to distinct-model consensus. |
| Zheng et al. (2023). "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." | https://arxiv.org/abs/2306.05685 | LLM-as-judge / eval framing | Use cautiously; LLM-as-judge is useful but biased and should not replace human research review. |
| Borzunov et al. (2022/2023). "Petals: Collaborative Inference and Fine-tuning of Large Models." | https://arxiv.org/abs/2209.01188 | Compute donation | Use as collaboration inspiration. Istara is whole-request routing, not Petals layer-wise sharding. |
| Jiang et al. (2023). "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." | https://arxiv.org/abs/2310.05736 | Prompt compression/memory | Use for compression inspiration; verify exact reduction claims against implementation benchmarks. |
| Chen et al. (2023). "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading." | https://arxiv.org/abs/2310.05029 | MemWalker-inspired context | Use for hierarchical reading/retrieval inspiration. |
| Lewis et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." | https://arxiv.org/abs/2005.11401 | RAG | Accurate for retrieval-augmented generation foundation. |
| Cormack et al. (2009). "Reciprocal rank fusion outperforms Condorcet and individual rank learning methods." | https://doi.org/10.1145/1571941.1572114 | Hybrid RAG ranking | Accurate for RRF. |
| Robertson and Zaragoza (2009). "The Probabilistic Relevance Framework: BM25 and Beyond." | https://doi.org/10.1561/1500000019 | Keyword retrieval/BM25 | Accurate for BM25 background. |
| AURA: "A Reinforcement Learning Framework for AI-Driven Adaptive Conversational Surveys." | https://arxiv.org/abs/2510.27126 | Adaptive interview/survey flow | Use as adaptive conversational survey inspiration. Live WhatsApp/Telegram claims require configured provider credentials or local simulators. |
| Zhou et al. (2026). "Memento-Skills: Let Agents Design Agents." | https://arxiv.org/abs/2603.18743 | Skill self-evolution inspiration | Use for governed skill/prompt evolution inspiration, not autonomous code mutation without approval. |
| Ouyang et al. (2025). "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory." | https://arxiv.org/abs/2509.25140 | Reasoning memory | Use for memory-driven self-improvement framing. |
| "Hyperagents" / DGM-H. | https://arxiv.org/abs/2603.19461 | Governed improvement archive | Use as metacognitive self-modification inspiration; Istara must keep human approval and rollback boundaries. |
| Berkeley Function Calling Leaderboard (BFCL). | https://huggingface.co/datasets/Felix-Ma/Berkeley-Function-Calling-Leaderboard | Tool/function-calling evals | Use for function-calling benchmark framing; cite official dataset or paper when adding eval claims. |
| W3C Web Authentication Level 3. | https://www.w3.org/TR/webauthn-3/ | WebAuthn/passkeys | Use current W3C spec; note Level 3 status when relevant. |
| Model Context Protocol specification. | https://modelcontextprotocol.io/specification | MCP integration | Use official specification; keep Istara MCP disabled by default and permission-gated. |
| Agent2Agent Protocol specification. | https://agent2agent.info/specification/ | A2A integration | Use official/current spec; avoid overclaiming interoperability beyond implemented manifest/routes. |
| Jon Yablonski. "Laws of UX." | https://lawsofux.com/book/ | Laws of UX skill/audit | Use as design heuristic reference, not scientific proof of all UX recommendations. |
| Atomic Research / Sharon and Gadbaw. | https://www.atomicresearch.io/ | Atomic Research chain | Practitioner source for nugget/fact/insight/recommendation structure. Istara should describe it as methodology inspiration plus database provenance, not a hallucination impossibility proof. |
