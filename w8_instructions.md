# W8: Embeddings gateway + model-management UX parity

Migrate embeddings to the Pi identity management and ensure model-management UX parity.

1. Implement `backend/app/core/pi_runtime/embeddings_gateway.py`:
   - Resolve an embed endpoint from `PiModelManager` (`kind=local` Ollama `/api/embed`, or any `/v1/embeddings`-compatible entry).
   - Call it with `httpx`.
   - Record ledger rows (`purpose="embed"`).
   - Keep the existing `embedding_cache` in front.

2. Update `agentic.embed` to dispatch:
   - Pi → gateway
   - legacy → `ollama.embed*` (unchanged)

3. Migrate the wrappers (not the 14 downstream consumers):
   - `embeddings.py:50` (`embed_text`) and `:90` (`embed_chunks`) call `agentic.embed`.
   - `validation.py:522` calls it directly (project-scoped).
   - Every consumer inherits the change with zero edits.

4. Migrate embed model bootstrap (`ensure_embed_model`, `embeddings.py:100`) to the provisioner.

5. Establish Vector-space invariant:
   - Assert at startup (dimension probe reusing `vector_health.py`) that the same embed model is used on both engines.
   - An engine switch must NEVER silently change embedding space.

6. Implement UX parity:
   - `api/routes/llm_servers.py` CRUD keeps working (legacy plane) AND projects into the Pi catalog.
   - `api/routes/settings.py` model pickers read merged catalog info.
   - `network_discovery.py` results feed BOTH planes (discovered server → LLMServer row → auto-projection).
   - Frontend `Sidebar.tsx`/settings views get an engine indicator + per-project engine selector (single new store field; simulation scenario added).
