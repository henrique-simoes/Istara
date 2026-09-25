# Evidence: research-spine findings and retrieval measurements (2026-09-25)

Lifecycle: `2026-09-25-spine-findings-and-retrieval-measurements.md`. Each finding has four
parts, written while it runs: what it is for → the flow driven → the output inspected
(quoted) → why that proves it. "Fails on main" means the test ran against `origin/main`'s
backend (`9272d41e`), from a `git archive` in the `istara-test:1` image with `--network none`
on the Mac Studio. "Passes" means the same command ran on this branch.

## F13: truncation cuts through the untrusted-content wrapper

**What it is for.** Retrieved documents and stored memories are untrusted. The guard wraps each
one in `<untrusted_content>` so the model treats it as data (OWASP LLM01 prompt injection;
spotlighting/delimiting, Hines et al. 2024, arXiv:2403.14720). That works only if every
wrapper is closed and nothing retrieved sits outside one.

**Flow driven (pytest, container).**
`tests/test_spine_prompt_boundaries.py` drives `AgentLifecycleMixin._handle_collaboration`
end to end with a 2,700-character chunk, and captures what the dispatcher receives. It drives
`ReasoningMemoryService.context_for_query` at budgets of 300, 700, 1,100 and 1,500
characters, and wraps a document that contains its own `</untrusted_content>` and a fake
opening tag. It also runs the deterministic skill fallback plan over wrapped context.

**Output inspected.** On `origin/main`:
```
test_spine_prompt_boundaries.py:29: AssertionError: (1, 0, 'he invoice screen. Participant P7 described ... Participant')
test_spine_prompt_boundaries.py:29: AssertionError: (1, 0, 'mory:m0">
test_spine_prompt_boundaries.py:156: assert (2 == 1)
```
That is one opening tag with no closing tag for the A2A block and for the ReasoningBank block,
and two closing tags where the document closed its own wrapper. On this branch all pass. The
A2A documents now sit before the collaborator's question, which stays the turn being answered
(`user_text == "What did P7 say about invoices?"`).

**Why that proves it.** The assertions count opening and closing tags and check that no
retrieved text remains outside a wrapper, at every budget tried. The fix removes the cause:
`truncate_preserving_wrappers` closes a cut wrapper or drops a partial one, ReasoningBank
assembles whole lines against its budget and never slices the joined block, and
`neutralize_boundary_markup` entity-escapes wrapper and protected tags inside untrusted text.
Stored text is untouched, so evidence-unit quotes stay exact substrings.

Product drive: the live-lane chat and A2A runs are recorded under Phase 8 below.

## F14: document content can trigger protected-tag pinning; the RAG budget is not enforced

**What it is for.** Protected blocks (`<qualitative_coding_protocol>`, `<codebook>`,
`<promotion_gate>` …) are methodology the services inject. The contract keeps them whole and
in order through compression. Document text must never borrow that privilege, and the RAG
budget (`min(5% of the window, 4,000)` tokens) decides how much evidence the model sees.

**Flow driven (pytest, container).** `build_compressed_rag_context`, the chat and Interfaces
path, runs with a relevant chunk and a hostile document chunk that wraps 900 filler words in
`<instructions>…</instructions>`. It also runs `compress_rag_chunks_indexed` with five
default-sized chunks (1,200 characters) against the default budget (409 tokens) at every
surplus level.

**Output inspected.** On `origin/main` the hostile chunk was pinned first
(`AssertionError: retrieval order kept; no pinning`), and the default case overran the budget
at every surplus level:
```
assert 2160 <= (409 * 4)   # high
assert 2160 <= (409 * 4)   # moderate
assert 2274 <= (409 * 4)   # low
assert 2189 <= (409 * 4)   # constrained
```
On this branch the relevant chunk leads, the block including labels and wrappers is at most
1,636 characters, no `compression.protected_block` telemetry fires for document text, and
service-injected protected blocks still survive in order
(`test_rag_chunk_compression_preserves_all_protected_blocks_in_order` passes).

**Why that proves it.** The budget overrun is a second defect under F14. The helper that
"enforced" the budget, `_trim_preserving_protected_blocks`, returns text without protected
blocks unchanged, so any ordinary chunk longer than the remaining budget passed through
whole. `_fit_to_budget` now trims ordinary text at a word boundary and still lets real
protected blocks overflow, as the contract requires. Retrieved text is neutralised before
compression, so a document can no longer produce a protected block.

Suites run on this branch: `test_spine_prompt_boundaries.py`, `test_data_transformations.py`,
`test_rag_resilience.py`, `test_retrieval_correctness_fixes.py`, `test_reasoning_bank.py`,
`test_content_guard.py`, `pi_production/test_w4_a2a_handlers.py`, `test_prompt_rag.py`,
`test_chat.py`, `test_agent_personas.py`: **110 passed**.
