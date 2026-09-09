# Build Stream — Memory Re-index Investigation

<!-- STATUS BLOCK -->
```yaml
item: memory-reindex-investigation
branch: testing
phase: "Phase 3 — Fix, migrate, prove (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: opencode, at: 2026-09-07T18:33:47Z, ledger: L-003 }
next_action: "Owner verifies Memory on QA; no merge without explicit approval."
```
<!-- /STATUS BLOCK -->

## S0 Frame (DEC-1)
- Symptom (owner): every visit to the Memory menu shows no chunks until a
  manual re-index; question is whether stored information is lost between
  visits or the UI simply fails to display what is stored.
- Memory touches: MemoryView (4 tabs), memoryApi, memory routes, RAG ingest/
  retrieval, LanceDB + keyword/BM25 stores, ReasoningBank, ContextDAG,
  health endpoint, QA tmpfs/volume mounts, backend restarts.
- DEC-1: diagnose before any fix; no destructive ops (no resets, no volume
  deletion, no re-ingest on user data); read-only probes first.

## Append-Only Ledger
- **L-001** (2026-09-07): Opened. Fanning out 3 read-only explorations.
- **L-002** (2026-09-07): Diagnosis CLOSED — real data loss, not UI error.
  Frontend refetches every mount (no cache) and shows genuine-empty honestly;
  Health reads stats while Knowledge reads chunk list (can diverge, by design).
  Backend re-index recomputes from persistent DB documents. The loss: durable
  override persists only SQLite; `LANCE_DB_PATH` fell through to
  `backend/.env` (`./data/lance_db` → tmpfs) and keyword lived at
  `data_dir/keyword_index` (tmpfs) — every backend recreate wiped both
  (9,292-chunk vanishings). Extra finds: keyword never migrated to shared
  storage; `data_migration.py:96` hardcoded `./data` vs `settings.data_dir`
  split-brain; project-delete cleanup would orphan override-lane keyword DBs.
- **L-003** (2026-09-07T18:33:47Z): FIXED and proven (CF-SPEC-16, CF-151
  evidenced 955 + finished; gate after 0 new). New optional
  `KEYWORD_INDEX_DIR` setting + `keyword_index_dir()` helper used by all 6
  keyword path sites (defaults identical); remote durable override sets
  `LANCE_DB_PATH` + `KEYWORD_INDEX_DIR` to simulation-shared. Tmpfs was found
  already empty at migration time (prior wipe), so one API sync repopulated
  9,675 chunks/129 docs from persistent DB rows. Acceptance: full
  `--force-recreate` → stats 9,292/9,292/79 sources with ZERO re-index, and UI
  screenshot shows the source list on first visit. Verified: 74 backend tests
  (2 new helper tests red→green), `diff --check` clean, feature docs ok.
  Notes: the two other project keyword DBs in wiped tmpfs were orphans (only
  1 project remains in DB — nothing to restore); `docker cp` cannot read
  tmpfs (resolve through exec, and stop-then-cp still misses mounts — learned
  the hard way, no data harmed since tmpfs was already empty); remote
  override file content recorded here for recoverability (host-only file):
  DATABASE_URL→simulation-shared db, LANCE_DB_PATH→shared/lance_db,
  KEYWORD_INDEX_DIR→shared/keyword_index. CF-SPEC-16 left unaccepted
  (auto-generated process tasks open).
