# Decision-Model Judge: References Log

Spec: CF-SPEC-1. Companion to `decision-model-judge-research.md` and the lifecycle file
`docs/build-stream/2026-10-17-decision-model-judge.md`.

Logging rule: every source used for this work is listed with **what was actually read** and when.
`docs` = official documentation pages read in full. `abstract` = only the arXiv/landing abstract was
read; claims beyond it are not made. `search` = only bibliographic details confirmed through search
results. `known` = a standard reference cited from prior knowledge, not re-read in this session;
verify against the primary source before quoting it in a publication. Secondary blogs were consulted
only to locate primary sources and are listed separately; no claim rests on them.

## Primary sources

| # | Reference | URL / DOI | Read | Date | Used for |
|---|---|---|---|---|---|
| R1 | Simões, L. H.; Ramires, T. G. (2026). *Avaliando orquestração multiagente e multimodelo local e de fronteira: trajetórias, recuperação, calibração e decisão humana.* Trabalho de Conclusão de Curso, especialização em Data Science e Analytics. | local PDF supplied by the owner | full text (30 pp.) | 2026-10-17 | the four-layer stack, T-Eq. 5–15, invariants |
| R2 | TypeSafe. *API reference* (`POST /v1/systemone`), *State*, *Primitives*, *Patterns*, *Double-checking citations* cookbook. | https://docs.typesafe.ai/api · /concepts/state · /patterns · /cookbooks/citation_check | docs | 2026-10-17 | wire contract, request rules, errors, batching, citation-check pattern |
| R3 | TypeSafe. *Models* and *Legal*. | https://docs.typesafe.ai/models · /legal | docs | 2026-10-17 | `jev-1.13.0`/`jev-1.14.0`, aliases, 64k/32k context, pricing, pin-the-version advice, no training on customer data, ZDR enterprise-only |
| R4 | TypeSafe. *Confidence*. | https://docs.typesafe.ai/confidence | docs | 2026-10-17 | confidence formulas; routing tiers; no calibration claim |
| R5 | TypeSafe. *Jev 1.13 jaggedness* (reviewed 2026-10-02) and *AI primer* (RLCD). | https://docs.typesafe.ai/model-jaggedness/jev-1.13 · /introduction/machine-learning-primer | docs | 2026-10-17 | first-option bias, literal reading, no arithmetic, context rot, adversarial state; RLCD aim |
| R6 | Rao, D.; Callison-Burch, C. (2026). *Decision Models vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places.* arXiv:2609.29769v3. | https://doi.org/10.48550/arXiv.2609.29769 | abstract | 2026-10-17 | correlated errors (>85% repeat), cascade gain ≤ 2.7 pts, cost 16–357×, latency 5–350× |
| R7 | Wang, Z.; Gao, Y. (2026). *JEV as a Judge for Agent Trace Security: An Empirical Comparison with Generative LLM Judges.* arXiv:2609.34862. | https://doi.org/10.48550/arXiv.2609.34862 | abstract | 2026-10-17 | 5,219 trajectories; F1 77.8 vs 74.1; coverage 95.5%; median 0.99 s |
| R8 | Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review* 78(1):1–3. | — | known (thesis ref) | — | Brier score, proper scoring rule |
| R9 | Murphy, A. H. (1973). A new vector partition of the probability score. *J. Applied Meteorology* 12(4):595–600. | — | known (thesis ref) | — | REL − RES + UNC |
| R10 | Guo, C.; Pleiss, G.; Sun, Y.; Weinberger, K. Q. (2017). On Calibration of Modern Neural Networks. ICML. | https://arxiv.org/abs/1706.04599 | known | — | temperature scaling |
| R11 | Chow, C. K. (1970). On optimum recognition error and reject tradeoff. *IEEE Trans. Information Theory* 16(1):41–46. | — | known (thesis ref) | — | reject option |
| R12 | Naeini, M. P.; Cooper, G.; Hauskrecht, M. (2015). Obtaining Well Calibrated Probabilities Using Bayesian Binning. AAAI. | — | known | — | ECE with equal-width bins |
| R13 | Geifman, Y.; El-Yaniv, R. (2017). Selective Classification for Deep Neural Networks. NeurIPS. | https://arxiv.org/abs/1705.08500 | known (search confirmed only that it is cited as related work in R26's slides) | — | risk–coverage curves |
| R14 | Wang, P. et al. (2023). Large Language Models are not Fair Evaluators. | https://arxiv.org/abs/2305.17926 | known | — | position bias; balanced position calibration |
| R15 | Horvitz, D. G.; Thompson, D. J. (1952). A Generalization of Sampling Without Replacement from a Finite Universe. *JASA* 47(260):663–685. | — | known | — | inverse-probability weights for audit samples |
| R16 | Angelopoulos, A. N.; Bates, S.; Candès, E. J.; Jordan, M. I.; Lei, L. Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control. arXiv:2110.01052 (Annals of Applied Statistics, 2025, per a listing). | https://arxiv.org/abs/2110.01052 | search | 2026-10-17 | risk control as multiple testing; τ with finite-sample guarantee |
| R17 | Kim, E. M.; Garg, A.; Peng, K.; Garg, N. (2025). Correlated Errors in Large Language Models. ICML 2025, PMLR 267:30038–30066. arXiv:2506.07962. | https://proceedings.mlr.press/v267/kim25e.html | search (abstract-level facts) | 2026-10-17 | 60% agreement when both err; larger/more accurate models more correlated; judge inflation for same-provider models |
| R18 | Kuncheva, L. I.; Whitaker, C. J. (2003). Measures of Diversity in Classifier Ensembles and Their Relationship with the Ensemble Accuracy. *Machine Learning* 51:181–207. | — | known | — | Yule's Q, diversity measures |
| R19 | NandhaKishor, M. (2026). *Laya: multilingual, non-autoregressive System 1 decision engine.* GitHub. | https://github.com/NandhaKishorM/laya | via R1 (not re-read) | — | per-language calibration failure (Khmer) |
| R20 | Dawid, A. P.; Skene, A. M. (1979). Maximum Likelihood Estimation of Observer Error-Rates Using the EM Algorithm. *JRSS C* 28(1):20–28. | — | known | — | evaluator confusion matrices with missing labels |
| R21 | Russo, D. J.; Van Roy, B.; Kazerouni, A.; Osband, I.; Wen, Z. (2018). A Tutorial on Thompson Sampling. *Foundations and Trends in ML* 11(1). | https://arxiv.org/abs/1707.02038 | known | — | Beta–Bernoulli bandit for method selection |
| R22 | Xiong, M. et al. (2024). Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs. ICLR. | https://arxiv.org/abs/2306.13063 | known | — | verbalized confidence is poorly calibrated |
| R23 | ggml-org/llama.cpp PR #29818: *server: add /v1/systemone API (models: laya, julia-1, lev, openjev, kev)*. Merged 2026-10-02. | https://github.com/ggml-org/llama.cpp/pull/29818 | page read | 2026-10-17 | open-weight deciders served through the same contract |
| R24 | Guo, R. et al. (2026). *Just Ask Jev: Reinforcement Learning for Calibrated Decisions as a Zero-Shot Detector of AI Alignment Failures.* arXiv:2609.29429. | https://doi.org/10.48550/arXiv.2609.29429 | abstract | 2026-10-17 | RLCD; RLCDAlignBench (10 failure types incl. hallucination, prompt injection); median AUROC 0.886 zero-shot; 63× cheaper than LLM-judge scorers |
| R25 | *Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation Panels.* arXiv:2605.29800. | https://arxiv.org/abs/2605.29800 | title only (search result) | 2026-10-17 | named as related work only |
| R26 | Mozannar, H.; Sontag, D. (2020). Consistent Estimators for Learning to Defer to an Expert. ICML. arXiv:2006.01862. | https://arxiv.org/abs/2006.01862 | search | 2026-10-17 | learning to defer (future work: learned rejector) |
| R27 | OpenAI Decisions API, public beta (2026-10-06): `POST /v1/decisions`. | official guide not reached; facts from secondary coverage | secondary only | 2026-10-17 | adapter candidate; **no design claim relies on it until the official docs are read** |
| R28 | Karpathy, A. *autoresearch*. | https://github.com/karpathy/autoresearch | via governance contract | — | hill-climbing loop origin |
| R29 | ReasoningBank, arXiv:2509.25140; Memento-Skills, arXiv:2603.18743; Hyperagents/DGM-H, arXiv:2603.19461. | see `docs/architecture/self-improvement-governance-contract.md` | via governance contract | — | learning-loop placement |
| R30 | Xiao, Z.; Yuan, X.; Liao, Q. V.; Abdelghani, R.; Oudeyer, P.-Y. (2023). Supporting Qualitative Analysis with Large Language Models: Combining Codebook with GPT-3 for Deductive Coding. IUI '23 companion. arXiv:2304.10548. | https://arxiv.org/abs/2304.10548 | search | 2026-10-17 | LLM deductive coding precedent |
| R31 | Chew, R.; Bollenbacher, J.; Wenger, M.; Speer, J.; Kim, A. (2023). LLM-Assisted Content Analysis: Using Large Language Models to Support Deductive Coding. arXiv:2306.14924. | https://arxiv.org/abs/2306.14924 | search (abstract-level); author list from prior knowledge | 2026-10-17 | LACA; agreement comparable to humans; detecting codes where the model guesses |
| R32 | *When Qualitative Research Meets Large Language Model: Exploring the Potential of QualiGPT as a Tool for Qualitative Coding.* arXiv:2407.14925. | https://arxiv.org/abs/2407.14925 | title + one search-snippet claim | 2026-10-17 | named only |
| R33 | Laurer, M.; van Atteveldt, W.; Casas, A.; Welbers, K. (2023). Less Annotating, More Classifying: Addressing the Data Scarcity Issue of Supervised Machine Learning with Deep Transfer Learning and BERT-NLI. *Political Analysis*. DOI 10.1017/pan.2023.20. | https://doi.org/10.1017/pan.2023.20 | search (citation via model card) | 2026-10-17 | NLI encoders as closed-set codebook classifiers |
| R34 | Hu, Y. et al. (2024). Leveraging Codebook Knowledge with NLI and ChatGPT for Zero-Shot Political Relation Classification. ACL 2024. arXiv:2308.07876. | https://arxiv.org/abs/2308.07876 | search | 2026-10-17 | codebook-derived hypotheses |
| R35 | *Codebook LLMs: Adapting Political Science Codebooks for LLM Use and Adapting LLMs to Follow Codebooks.* arXiv:2407.10747. | https://arxiv.org/abs/2407.10747 | search snippet | 2026-10-17 | codebook restructuring gives modest gains; constraint compliance is hard |
| R36 | gbesse. *jev-codebook* (MIT; independent of TypeSafe). | https://github.com/gbesse/jev-codebook | README read | 2026-10-17 | noul-per-code / choice mechanics; per-code thresholds; no benchmark claimed |
| R37 | Stephenson, D. B.; Coelho, C. A. S.; Doblas-Reyes, F. J.; Balmaseda, M. (2008). Two extra components in the Brier score decomposition. *Weather and Forecasting* 23(4):752–757. | — | known; **title and venue to verify before publication** | — | within-bin variance and covariance terms that make the binned Brier decomposition exact |

## Secondary sources (located primary sources only; no claims rest on them)

TypeSafe-adjacent and landscape pages seen in search results on 2026-10-17: OpenRouter JEV guide
(openrouter.ai/docs/guides/community/jev), AIMLAPI JEV page, Cloudflare `typesafe/jev` model page,
Pydantic AI TypeSafe provider, Flavio Copes "How to build typed decisions with Jev", Hugging Face
community blogs on JEV, Runware "Jev, Laya, and the emerging role of decision models", Pinggy
"Best Open Source Jev Alternatives", Forbes 2026-10-12 "Decisions, decisions…", explainx.ai
llama.cpp decision models, and secondary coverage of the OpenAI Decisions API (letsdatascience.com,
apidog.com, aiweekly.co). Several conflict on endpoints, versions and pricing; the official docs
(R2–R5) win.

## Note for the thesis revision

The thesis bibliography lists R6 as "JEV vs. LLMs as rubric judges: cheaper, faster, and wrong in the
same places". The current arXiv version (v3) is titled **"Decision Models vs. LLMs as Rubric Judges:
Cheaper, Faster, and Wrong in the Same Places"**. It also compares Perplexity's Decider, not only JEV.
Cite the version you read.
