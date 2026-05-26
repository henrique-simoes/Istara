# Retrieval-Augmented Generation (RAG)

Retrieval-augmented generation combines model generation with retrieved project context, documents, memory, or other evidence. In Istara, Hybrid RAG is the exact-evidence layer: it retrieves source passages, evidence units, spans, participants, methods, review status, reliability status, and codebook/coding-run provenance.

Hybrid retrieval calls emit content-free `retrieval.hybrid` telemetry with project, mode, and available evidence-unit/codebook/coding-run handles. The telemetry proves retrieval occurred and which validated handles were available; it does not store queries, quotes, prompts, or source text.

Evidence Graph / GraphRAG is the synthesis and traceability layer. It can answer cross-document questions and reveal relationships between evidence units, codes, coding runs, models, donors, disagreements, tasks, findings, and reports. It cannot bypass qualitative coding, reliability gates, human review, approved Done-task gating, or report gating.

The research-validity traceability API exposes the stored graph/report/task chain as `graph+hybrid` evidence. It is the route to use when asking whether a report depends on low-agreement codes, unresolved reconciliation, a coding run, or a codebook version; it does not replace exact Hybrid RAG backfill for quotes and spans.

Prompt-RAG may retrieve helpful contextual sections, but mandatory qualitative coding methodology, codebook, reliability policy, and promotion gates are injected deterministically by the relevant service. Project-scoped Prompt-RAG calls emit `prompt_rag.context` telemetry with agent and retrieval-mode handles, never the retrieved prompt text or user query.

Compression must preserve protected protocol and evidence blocks across prompt, question-aware, and RAG-chunk compression; when the budget is too small, protected blocks stay intact and the output is marked over budget instead of truncating research methodology. When protected blocks are present in project RAG compression, Istara emits `compression.protected_block` telemetry with retention status only.
