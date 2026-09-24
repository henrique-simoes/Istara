# Build Stream — Memory Re-index Investigation

<!-- STATUS BLOCK -->
```yaml
item: memory-reindex-investigation
branch: main   # testing was promoted to main by squash merge (PR #34, 2f106b57), so its commits are not ancestors of main
phase: "Phase 3 — Fix, migrate, prove (complete)"
stage: S5-ship
status: done
blocked_on: null
last: { agent: claude-opus-5-5, at: 2026-09-24T03:39:14Z, ledger: L-1 }
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

### L-1 | 2026-09-24T03:39:14Z | S5-ship | claude-opus-5-5 | executor | —
Did: record correction found by Ainulindalë's truth reconciler. Its work reached main through the squash merge of testing (PR #34, 2f106b57); the block named `testing`, whose commits a squash leaves off main's history.
Result: the Status Block says what is true today.
Verified: `git merge-base --is-ancestor 2f106b57 origin/main` (the squash of testing); `git diff --stat 2f106b57 9620e5d8` empty; `compass-forge spec show` for each named spec.
Next: as the block says.
