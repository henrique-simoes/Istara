# Testing Queue

Changes that are awaiting review before merging to `main`, plus the most recent integration state.

> **Branch hygiene note (2026-04-28):** Multiple legacy branches (`feat/voice-transcription`, `review/p*`, `fix-ci-validation`, etc.) are 46–124 commits behind `main` and must not be merged. See `planner.md` "Deprecated Branches" for the canonical list.

## Awaiting Review

| PR | Change | Added | Notes |
|---|---|---|---|
| - | - | - | - |

## Verified & Ready for `main`

| PR | Change | Reviewed | Notes |
|---|---|---|---|
| - | - | - | - |

## Recently Integrated into `main`

| Change | Integrated | Notes |
|---|---|---|
| `feat/high-quality-uxr-finetuning-datasets` | 2026-04-28 | Merged real-time voice recording in Chat and Design Tools. |
| `feat/dataset-generator-upgrade` | 2026-04-24 | Merged dataset generator and fine-tuning source support after resolving review findings. |
| `feat/security-remediation-2fa-passkey` | 2026-04-24 | Merged passkey ownership and security hardening. |
| `feat/skill-methodology-audit-clean` | 2026-04-24 | Merged JSON-first skill registry cleanup and stale legacy skill file removal. |
| `feat/compute-pool-audit-and-upgrades` | 2026-04-24 | Merged connection string lifecycle hardening. |
| `feat/integrations-audit` | 2026-04-24 | Integrated retry semantics hardening into `main`; stale branch should not be merged wholesale. |
| `feat/compass-swarm-repository-intelligence` | 2026-04-24 | Merged Compass planner, repository intelligence, correction loop, and user handoff process updates. |

---

### How to Use This File

1. **Push the review branch** → Add an entry under "Awaiting Review"
2. **Test locally** → Check out the review branch or integration branch, run `./istara.sh start`, verify the change works
3. **Mark verified** → Move the entry to "Verified & Ready for `main`"
4. **Merge to main** → merge only reviewed, current code; clear the verified entries and update "Recently Integrated into `main`"

### How to Test Staging Locally

```bash
git checkout staging && git pull origin staging
./istara.sh start   # or docker compose up for containerized testing
```

### What to Test

- **API changes**: `curl` the endpoints, check responses
- **UI changes**: Open http://localhost:3000, navigate the affected views
- **Auth changes**: Login, logout, token refresh, 2FA flow
- **E2E tests**: `ISTARA_ADMIN_USER=<user> ISTARA_ADMIN_PASSWORD=<pass> python tests/e2e_test.py`
- **Unit tests**: `pytest tests/`
- **Simulation scenarios**: `ADMIN_USERNAME=<user> ADMIN_PASSWORD=<pass> node tests/simulation/run.mjs --skip-skills`

---

## Layer 4: Orchestration Benchmarks

### Running the Benchmark Suite

```bash
# Run all benchmarks (recommended)
python tests/benchmarks/run_benchmarks.py

# With JSON output for CI/CD integration
python tests/benchmarks/run_benchmarks.py --json results.json

# Via pytest (for IDE integration)
pytest tests/benchmarks/test_orchestration.py -v

# Run specific benchmark only
pytest tests/benchmarks/test_orchestration.py::test_long_horizon_dag_decomposition -v
```

### Benchmark Requirements

Benchmarks use **mocked LLM responses** — no live database or LLM server required. They run with in-memory SQLite and do not require Istara to be running.

- **Python**: 3.11+ (uses `asyncio`, `pytest-asyncio`)
- **Dependencies**: pytest, pytest-asyncio (already in project dev dependencies)
- **Time**: ~5 seconds total for all 4 benchmarks + suite runner

### Benchmark Details

| # | Benchmark | File | Tests | What It Validates |
|---|-----------|------|-------|------------------|
| 1 | Long-Horizon DAG Decomposition | `test_orchestration.py::test_long_horizon_dag_decomposition` | 1 | No circular dependencies in 10-step research plans, valid topological ordering, context retention across multi-step execution |
| 2 | Tool-Calling Accuracy & Resilience | `test_orchestration.py::test_tool_calling_accuracy_resilience` | 5 | Schema compliance (strict JSON with `additionalProperties: false`), regex fallback for non-tool-call models, hallucination filtering, MAX_ITERATION enforcement |
| 3 | A2A Mathematical Consensus | `test_orchestration.py::test_a2a_mathematical_consensus` | 5 | Fleiss' Kappa ≥0.6 on clear cases, <0.6 on ambiguous cases (triggers IN_REVIEW routing), cosine similarity on embedding vectors, consensus threshold logic |
| 4 | Async Steering Responsiveness | `test_orchestration.py::test_async_steering_responsiveness` | 1 | Atomic queue lock under concurrent steering injection (10 simultaneous), steering reflected in output without state corruption, follow-up message queuing |

### Consensus Engine Usage

All mathematical benchmarks use Istara's **production** consensus engine from `backend/app/core/consensus.py`:

```python
from app.core.consensus import fleiss_kappa, cosine_similarity, compute_consensus
```

**Fleiss' Kappa Input Format**: N×k ratings matrix where N = number of items (rows), k = categories (columns). Each cell = count of raters who assigned that category to that item. All rows must sum to the same `n` (number of raters per item).

Example:
```python
# 3 items, 4 categories, 2 raters per item
ratings_matrix = [
    [2, 0, 0, 0],   # Item 1: both raters chose category 0 → perfect agreement
    [0, 1, 0, 1],   # Item 2: split between categories 1 and 3
    [0, 0, 2, 0],   # Item 3: both chose category 2 → perfect agreement
]
kappa = fleiss_kappa(ratings_matrix)  # Returns ~0.85 (strong agreement)
```

### CI/CD Integration

Benchmarks are mandatory for changes to `AgentOrchestrator`, `A2A`, or `steering_manager`. Add to CI workflow:

```yaml
- name: Run Orchestration Benchmarks
  run: pytest tests/benchmarks/test_orchestration.py -v --tb=short
```

The suite runner (`test_full_orchestration_suite`) asserts all benchmarks pass. In CI, a single failure fails the entire suite.

### Model-Specific Testing Notes

Benchmarks can be run against various local models by configuring `LLM_PROVIDER` and the corresponding host/model settings before running:

| Model | Provider | Settings |
|-------|----------|---------|
| Llama 3 (8B) | LM Studio | `LMSTUDIO_MODEL=llama-3-8b`, `LMSTUDIO_HOST=http://localhost:1234` |
| Qwen 2.5 (7B/14B) | Ollama | `OLLAMA_MODEL=qwen2.5:latest`, `LLM_PROVIDER=ollama` |
| Gemma 3 (4B/12B) | LM Studio/Ollama | Configure model name in respective settings |

The benchmarks are **model-agnostic** — they test orchestration logic, not model quality. Results should be consistent regardless of which local model is configured.

---

## Dataset Generator Validation

The Istara SFT dataset generator is validated as a local, credential-free generation path by default.

```bash
python -m py_compile Model_Finetuning/dataset-json-generator.py
python Model_Finetuning/dataset-json-generator.py --out-dir /tmp/istara_dataset_check --samples-per-skill 2
python scripts/check_integrity.py
```

Expected result:
- all live skill definitions under `backend/app/skills/definitions/*.json` are discovered
- generated `istara_sft_messages.jsonl`, `istara_sft_alpaca.jsonl`, and `istara_sft_full.jsonl` parse as JSONL
- `dataset_info.json` reports no omitted live skills
- upload is skipped unless `--upload` is explicitly passed
