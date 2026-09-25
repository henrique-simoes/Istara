# Blind pack: Phase 7b, RAG compression under budget pressure only (2026-09-25)

This is the only file you, the Phase 7b reviewer, are handed first. Do not open
`2026-09-25-spine-findings-and-retrieval-measurements.md` (the lifecycle file),
`2026-09-25-spine-findings-evidence.md`, or the implementer's commit message until your
measurement sheet below is filled and frozen. Those files carry the implementer's numbers, and
reading them first turns measuring into confirming.

## Mandate

Your task is not to confirm the change. It is to break it. Assume it is wrong until your own
measurement says otherwise. A review that confirms everything and raises no independent
finding is itself suspect: if you find nothing, state what you tried to break and could not.
Prefer to be a different model from the implementer's.

## Own environment, mandatory

Build your own workspace on the Mac Studio (the owner's brief allows execution only there):
your own directory under `~/cf-remote/eval/`, your own container names, your own output
directory. Do not reuse `istara-m3fix*`, `m3fix-*.sh` or `measure-m3fix/`. The reason: if the
implementer's apparatus carries a bias, reusing it measures the same blind spot twice.

## What changed (scope, not results)

- `backend/app/core/prompt_compressor.py`: `compress_rag_chunks_indexed` and a new helper.
- `backend/app/evals/retrieval_eval.py`: `budget_recall` reports lost spans and a loss step.
- New tests: `tests/test_spine_rag_budget_passthrough.py`; two tests appended to
  `tests/test_spine_retrieval_eval.py`.
- Docs: one block in `Tech.md` (context management pipeline), one bullet in
  `docs/architecture/research-validity-contract.md`.
- Base for "before" comparisons: commit `afe5c307` on the local branch
  `fix/spine-findings-measurements-20260925` (not pushed at the time of writing; `git show
  afe5c307:<path>` gives each base file).

## Operational prerequisites (not results)

- pytest: the `istara-test:1` image, `--network none`, working directory `/work/backend`,
  tests addressed as `../tests/<file>`.
- M3 needs the real embedder: `nomic-embed-text` served by the labelled Ollama container
  `istara-cs76-embed` on the Docker network `istara-cs76-live`. Set
  `LLM_PROVIDER=ollama`, `OLLAMA_HOST=http://istara-cs76-embed:11434`,
  `OLLAMA_EMBED_MODEL=nomic-embed-text`, and a scratch `DATA_DIR`/`DATABASE_URL`/`LANCE_DB_PATH`
  under `/tmp`; initialise the schema with `app.models.database.init_db` first. Run
  `python -m app.evals.retrieval_eval budget --out <file>` from `/work/backend`.
- The Studio is shared. When its load average is high, the CPU embedder can exceed the embed
  client's 30-second timeout (`httpx.ReadTimeout`); wait for the load to drop and re-run.
  Load one embedding model only; do not start chat models or the QA stack.

## Proof questions

1. On the base commit, run the new test file and the two appended tests. How many fail, and
   what does each failure assert?
2. On the change, how many of those pass? How many of the pre-existing compressor, RAG-context,
   ranking and retrieval-eval tests pass (`test_spine_prompt_boundaries.py`,
   `test_spine_ranking_semantics.py`, `test_data_transformations.py`,
   `test_retrieval_correctness_fixes.py`, `test_rag_resilience.py`,
   `test_spine_retrieval_eval.py`)?
3. Run M3 (`budget`) on the base commit with the instrumented `retrieval_eval.py` from the
   change. For each window: spans retrieved, spans in the prompt, spans verbatim, and every
   lost span's question, path, offsets, hit rank and step. Is one cause behind the losses at
   16k tokens and above? What is it?
4. Run M3 on the change. Same table. Which losses disappear, which remain, and why?
5. Does any chunk now reach the prompt in a different order, or without its label or
   untrusted-content wrapper, or push the RAG block over its budget, at any window?
6. Under budget pressure (the chunks do not fit), is the behaviour byte-identical to the base
   commit? Construct at least one case yourself.
7. Do protected blocks (`get_protected_blocks`) still come first, whole, and in their original
   order, with and without budget pressure?
8. Can the new pass-through path be reached with content that should not pass (document text
   posing as a protected block, blank chunks, an empty query)? What happens?
9. Does `_loss_step` attribute each step correctly? Is any branch unreachable or mislabelled?
10. Is the claim in the changed docs true of the code?

## Measurement sheet (fill, then freeze before opening anything else)

| Q | Command(s) run | Your result | Finding? |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |

What I could not verify, and why:

Did I build my own environment, or reuse theirs?

Frozen at (ISO time), by (model id):
