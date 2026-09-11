# Pi Compatibility Authority

Status: authoritative reference · Last verified: 2026-09-08 · Pin: `@earendil-works/pi-ai` / `@earendil-works/pi-agent-core` **0.85.1**

Pi/pi-ai is the single authority for provider and model capability semantics. Istara
**inherits, restricts, or projects** it — it never restates it. This document is the
operating manual for that contract: what the authority surfaces are, how the projection
is generated and policed, and the exact routine for adopting a new upstream release.
The governing delivery record is `docs/build-stream/2026-09-08-pi-capability-inheritance.md`
(master plan §5.6 "the routine-bump contract", AC-5/AC-10/AC-11).

---

## 1. The authority law

Capability knowledge resolves through ordered tiers; a lower tier may only restrict or
fill what a higher tier leaves unstated:

| Tier | Source | Owns | Where enforced |
|---|---|---|---|
| 4 | pi-ai builtin registry (`getBuiltinModel`, exact id) | transport `api`, `compat`, `thinkingLevelMap`, list pricing, context/max tokens | worker `provider.mjs` resolver; generated projection |
| 3 | Governed custom-provider overlays (`backend/app/core/pi_runtime/data/custom_providers/*.json`) | records for providers absent from the registry (e.g. `dashscope`), hand-owned pricing | merged verbatim by the emitter; collision/schema/order rejected |
| 2 | Operator endpoint configuration | contract rates, tri-state capability vetoes (`supports_reasoning: false` beats the record; nothing enables beyond it) | `endpoint_policy.py` merge law + admission preflight |
| 5–6 | Legacy identity/detection fallback | only registry misses (unknown proxy URL, legacy bindings) — moved verbatim into `legacyIdentityCapabilities()` | `provider.mjs` |

Rules that make the tiers safe:

- **One exact lookup.** `getBuiltinModel(pi_provider, model)` — no fuzzy matching. A miss
  delegates to the legacy path and is visible in the capability receipt.
- **Byte-identical additive wire.** Registry misses (fallback paths) emit request bodies
  pinned byte-for-byte to pre-change fixtures (`pi-runtime/test/fixtures/wire/pre-change/`).
  A bump must not perturb them (AC-1).
- **The projection is generated, never hand-edited.**
  `backend/app/core/pi_runtime/data/pi_models_catalog.json` is a provenance-stamped
  projection (`__provenance.pi_ai_version`, `model_field_set_hash`, `emitter_sha256`)
  of the installed pi-ai registry plus governed overlays.
- **Receipts, not secrets.** Capability receipts and turn spans carry content-free
  allowlisted fields only; never URLs, headers, credentials, or endpoint fingerprints.

## 2. The projection and its gates

Regenerate and verify (idempotent; `--check` masks `emitted_at`):

```bash
python scripts/generate_pi_catalog.py          # regenerate; prints the drift summary
python scripts/generate_pi_catalog.py --check  # byte-identity gate; must be a no-op
```

Standing conformance suites (all offline):

| Gate | Suite | Forbids |
|---|---|---|
| Projection ≡ resolver | `tests/pi_compat/test_catalog_conformance.py` | the two read paths disagreeing for any registry model |
| Regeneration drift | `tests/pi_compat/test_catalog_conformance.py` | a bump without regeneration (provenance ≠ pin) |
| Overlay preservation | `tests/pi_compat/test_catalog_conformance.py` | the emitter rewriting or dropping governed records |
| Serializer completeness | `tests/pi_compat/test_capability_carry_through.py` | a shipped catalog key the loader silently drops |
| Effort vocabulary | `tests/pi_compat/test_capability_carry_through.py` | a menu ladder diverging from pi-ai's derivation |
| Budget preflight (AC-6) | `tests/pi_compat/test_capability_carry_through.py` | admitting a zero-priced registry model without tier-2 rates |
| Pin lockstep | `tests/pi_migration/test_version_provenance.py` | the two surfaces (pi-runtime, labs/pi-replacement) drifting apart in `package.json`, lockfile, or installed `node_modules` |
| Wire payloads | `pi-runtime/test/capability-inheritance.test.mjs` | request-body changes on fallback or inherited paths without deliberate fixture updates |

## 3. The routine bump runbook (AC-11)

Adopting a new upstream release is five commands plus a reviewed diff. The diff **is**
the compatibility report — nothing requires repository archaeology.

```bash
# 0. Diff-proof the candidate BEFORE moving the pin (network required).
python scripts/pi_bump_diff_proof.py proof <candidate> \
  --report docs/build-stream/pi-bump-<candidate>-diff-proof.json \
  --expect-model zai/glm-5.3-flash --expect-model zai/glm-5.3

# 1. Lockstep pin both surfaces, exact versions (no ^/~).
cd pi-runtime            && npm install @earendil-works/pi-ai@<X> @earendil-works/pi-agent-core@<X>
cd ../labs/pi-replacement && npm install @earendil-works/pi-ai@<X> @earendil-works/pi-agent-core@<X>
# then set both package.json pins to exact "<X>" (npm writes ^ ranges) and re-run
# `npm install` in each surface so the lockfiles agree with the manifests.

# 2. Regenerate; the printed drift summary + git diff ARE the compatibility report.
python scripts/generate_pi_catalog.py
git diff --stat backend/app/core/pi_runtime/data/pi_models_catalog.json

# 3. Classify EVERY changed surface and registry removal (§8 taxonomy below) and
#    re-run the gate; it passes only when nothing is unclassified or blocked.
# 4. Update EXPECTED_PINS (tests/pi_migration/test_version_provenance.py), the
#    labs adapter manifest, and any test that pinned a now-changed upstream fact —
#    each with an in-file justification citing the classification.
# 5. Run the suites (§4 ladder), record evidence, ship.
```

### The diff-proof gate

`scripts/pi_bump_diff_proof.py` installs the candidate into a scratch directory and,
without touching the working tree:

- diffs every **consumed** dist surface (the API transports the resolver imports, plus
  every registry model-data module) against the installed pin;
- walks both registries and reports provider/model inventory deltas (additions and
  **removals** — deletions cannot pass unnoticed, G7);
- asserts `--expect-model` entries exist in the candidate registry;
- fails the gate while any changed surface or removal is `unclassified` or `blocked`.

`verify-report <report>` re-checks a written report offline (CI form of the same gate);
`verify` is the post-bump acceptance (pin == lockfile == installed == catalog
provenance on both surfaces).

### Classification taxonomy (§8)

Every surfaced diff — catalog field, wire payload, `model_field_set_hash`, registry
removal — is classified before release:

| Class | Meaning | Action |
|---|---|---|
| `intended-upstream` | pi-ai deliberately changed a provider fact | update the fixture/test, cite the upstream change in the ledger |
| `istara-fix` | the diff corrects a present-tense Istara defect | flip the fixture, cite the evidence ID |
| `blocked` | the change breaks a provider or contract | do **not** ship; split into its own task |
| `unclassified` | not yet triaged | **gate failure** |

Worked example — the 0.84.3 → 0.85.1 bump (2026-09-08): all 36 changed surfaces and 73
registry removals classified `intended-upstream`; no fixture updates were needed because
every changed API surface was response-side (reasoning-detail replay assembly, SSE EOF
flush, prompt-cache/max-tokens compat gates, Anthropic beta-endpoint migration) and the
request-wire fixtures passed unchanged; `zai/glm-5.3` was repriced from $0 (the AC-6
proof moved to `zai/glm-5.3-highspeed`); evidence:
`docs/build-stream/pi-compat-20260908-0851-diff-proof.json`.

### Rollback

No database or schema migration exists on this path, so rollback is mechanical:

```bash
git checkout <previous-sha> -- pi-runtime/package.json pi-runtime/package-lock.json \
    labs/pi-replacement/package.json labs/pi-replacement/package-lock.json \
    backend/app/core/pi_runtime/data/pi_models_catalog.json
cd pi-runtime && npm ci && cd ../labs/pi-replacement && npm ci && cd ..
python scripts/generate_pi_catalog.py --check   # verifies the restored projection
```

Terminal states are explicit: *deterministic complete, live pending* · *not_runnable*
(missing permission/credential — record the exact blocker and resume command) ·
*rolled back* · *accepted*. Live acceptance against a configured endpoint is a separate,
owner-authorized step (AGENTS.md *Live LLM and Model Loading Safety*); the pin bump
itself never requires it.
