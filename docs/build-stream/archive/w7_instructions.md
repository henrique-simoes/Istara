# W7: Validation / consensus / dual-coder

Migrate 8 call sites across `core/validation.py`, `core/validation_executor.py`, and `services/research_validity_service.py` to the Pi pipeline.

| Site | Today | Migration |
|---|---|---|
| `core/validation.py:152` `dual_run` | 2 distinct servers, direct `server.chat` | `ensemble(n=2, distinct=True)` → `validation.dual_run` |
| `core/validation.py:314` `full_ensemble` | 3+ servers | `ensemble(n=min_responses+1, distinct=True)` |
| `core/validation.py:373` `self_moa` | temp sweep on one model | `ensemble(n=len(temps), distinct=False, temperatures=[...])` |
| `core/validation.py:213` `adversarial_review` | 1 call | `completion` → `validation.adversarial` |
| `core/validation.py:431,470` `debate_rounds` | initial + rounds | `completion` ×(1+rounds) → `validation.debate` |
| `core/validation_executor.py:64` | judge call; **latent bug: reads `result.get("content")` but registry returns `message.content`** | `structured` → `validation.judge`; FIX the bug in the same commit (it means legacy adversarial scoring has been silently degraded — flag in benchmark notes) |
| `services/research_validity_service.py:556` dual-coder | pinned `coder.node.chat`, RF strict=False | `structured` over `resolve_distinct(n=max_coders)` → `validity.coder`; the "≥3 distinct model coders" reliability gate (`research-spine-probes.mjs:8-31`) maps to distinct Pi endpoint identities |
| `core/validation.py:522` `_get_embeddings` | `llm_router.embed_batch` (consensus similarity) | stays legacy until W8, then `agentic.embed` |

Fail-closed rule for `distinct=True`: fewer distinct endpoints than `n` ⇒ typed error surfaced to the validation caller, which falls back to its existing "validation unavailable" handling — never fabricate diversity from one endpoint.
