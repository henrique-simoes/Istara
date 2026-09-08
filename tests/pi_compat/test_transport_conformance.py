"""Transport conformance: the endpoint policy's derived ``provider_kind`` must
agree with a real worker bind for every pi-ai registry ``api`` value
(review F-1 on wave ``authority-and-boundary``).

Root cause of the miss: ``dump-resolved-capabilities.mjs`` fed ``record.api``
back in as the transport, so ``record.api !== modelApi`` was structurally
unreachable in the equivalence sweep — while production derives the transport
from ``endpoint_policy.provider_kind_for_catalog_api``. This module drives the
POLICY-DERIVED kind (not the record api) for at least one catalog model per
affected api value, on both sides of the boundary:

- Python side (no node needed): the derived kind per api value.
- Worker side (node lane, typed ``not_runnable`` without it): the derived kind
  binds (``pi_builtin``) or rejects with the typed ``provider_transport_mismatch``.
- Parity: the JS ``providerKindForRegistryApi`` table and the Python
  ``provider_kind_for_catalog_api`` table agree on every KnownApi value.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "backend" / "app" / "core" / "pi_runtime" / "data" / "pi_models_catalog.json"
PROVIDER_MJS = REPO_ROOT / "pi-runtime" / "src" / "provider.mjs"

# One catalog model per affected registry api value (F-1). The openai and xai
# rows are the fixed regression (they bind); the rest document the deliberate
# loud rejection (native auth/URL shapes PiApiEndpoint does not model).
CASES = [
    # (registry api, catalog provider, catalog model, expected kind, binds?)
    ("openai-responses", "openai", "gpt-4o", "openai_responses", True),
    ("openai-responses", "xai", "grok-4.3", "openai_responses", True),
    ("bedrock-converse-stream", "amazon-bedrock", "amazon.nova-lite-v1:0", "openai_compat", False),
    ("azure-openai-responses", "azure-openai-responses", "gpt-4", "openai_compat", False),
    ("mistral-conversations", "mistral", "codestral-latest", "openai_compat", False),
    ("google-generative-ai", "google", "gemini-2.5-flash", "openai_compat", False),
    ("google-vertex", "google-vertex", "gemini-2.5-flash", "openai_compat", False),
    # Unaffected controls: the three original transports keep deriving as before.
    ("openai-completions", "deepseek", "deepseek-v4-pro", "openai_compat", True),
    ("anthropic-messages", "anthropic", "claude-opus-4-7", "anthropic_compat", True),
    ("openai-codex-responses", "openai-codex", "gpt-5.6-luna", "openai_codex", True),
]

# Every transport pi-ai 0.84.3 can emit (KnownApi minus pi-messages, which has
# no builtin models in this pin). Both mapping tables must agree on all of these.
KNOWN_APIS = [
    "openai-completions",
    "openai-responses",
    "azure-openai-responses",
    "openai-codex-responses",
    "anthropic-messages",
    "bedrock-converse-stream",
    "google-generative-ai",
    "google-vertex",
    "mistral-conversations",
    "pi-messages",
]


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _node_ready() -> bool:
    return (
        shutil.which("node") is not None
        and (REPO_ROOT / "pi-runtime" / "node_modules" / "@earendil-works" / "pi-ai").exists()
    )


def test_policy_derives_bindable_kind_per_registry_api():
    """The kind the endpoint policy derives — the exact production input the
    worker gate sees — per affected api value (F-1 requirement b)."""
    from app.core.pi_runtime.endpoint_policy import provider_kind_for_catalog_api

    catalog = _catalog()
    for api, provider, model_id, expected_kind, _binds in CASES:
        models = {m["id"]: m for m in catalog[provider]}
        assert models[model_id]["api"] == api, (
            f"case drift: catalog {provider}/{model_id} is now {models[model_id]['api']}, "
            f"expected {api} — refresh CASES"
        )
        assert provider_kind_for_catalog_api(api) == expected_kind, (
            f"policy derives the wrong kind for registry api {api}"
        )


def test_apply_catalog_fields_end_to_end_per_affected_api():
    """Full ``_apply_catalog_fields`` derivation for the affected models —
    the payload the worker will actually bind."""
    from fastapi import HTTPException

    from app.core.pi_runtime.endpoint_policy import _apply_catalog_fields

    catalog = _catalog()
    for api, provider, model_id, expected_kind, binds in CASES:
        payload = {"pi_provider": provider, "pi_model": model_id}
        if not binds and provider == "azure-openai-responses":
            # Azure records carry no baseUrl; the catalog cannot supply the
            # resource-scoped URL, so only the pure kind mapping is asserted.
            from app.core.pi_runtime.endpoint_policy import provider_kind_for_catalog_api

            models = {m["id"]: m for m in catalog[provider]}
            assert provider_kind_for_catalog_api(models[model_id]["api"]) == expected_kind
            continue
        try:
            _apply_catalog_fields(payload)
        except HTTPException as exc:  # pragma: no cover - catalog drift guard
            pytest.fail(f"_apply_catalog_fields rejected {provider}/{model_id}: {exc.detail}")
        assert payload["provider_kind"] == expected_kind, (
            f"{provider}/{model_id} (api={api}): derived {payload['provider_kind']}, "
            f"expected {expected_kind}"
        )
        assert payload["model"] == model_id
        if binds:
            assert str(payload.get("base_url") or "").startswith("https://"), (
                f"{provider}/{model_id}: bindable kind requires a catalog base_url"
            )


def test_kind_mapping_parity_node_python():
    """The JS and Python mapping tables agree on every KnownApi value.

    Either table drifting re-opens the F-1 hole (sweep and production deriving
    different transports), so the gate fails on ANY disagreement.
    """
    if not _node_ready():
        pytest.skip("not_runnable: node or the installed pi-ai package is unavailable")
    from app.core.pi_runtime.endpoint_policy import provider_kind_for_catalog_api

    probe = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                f"import {{ providerKindForRegistryApi }} from '{PROVIDER_MJS.as_uri()}';"
                f"console.log(JSON.stringify([{', '.join(repr(a) for a in KNOWN_APIS)}].map(providerKindForRegistryApi)))"
            ),
        ],
        cwd=str(REPO_ROOT / "pi-runtime"),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert probe.returncode == 0, f"node mapping probe failed: {probe.stderr}"
    js_kinds = json.loads(probe.stdout)
    for api, js_kind in zip(KNOWN_APIS, js_kinds):
        assert js_kind == provider_kind_for_catalog_api(api), (
            f"mapping drift for registry api {api}: node={js_kind} "
            f"python={provider_kind_for_catalog_api(api)}"
        )


def test_policy_derived_kind_binds_or_rejects_typed_on_worker():
    """End-to-end across the boundary: policy-derived kind -> worker
    ``resolveCapabilities``. Bindable models resolve ``pi_builtin`` (the F-1
    regression: openai/gpt-4o threw here); native-transport models reject with
    the typed pre-network code (loud, not misshapen)."""
    if not _node_ready():
        pytest.skip("not_runnable: node or the installed pi-ai package is unavailable")

    catalog = _catalog()
    script_lines = ["import { resolveCapabilities } from './src/provider.mjs';", "const results = [];"]
    for _api, provider, model_id, kind, binds in CASES:
        if provider == "azure-openai-responses":
            continue  # no catalog base_url — nothing bindable to construct
        models = {m["id"]: m for m in catalog[provider]}
        base_url = models[model_id].get("baseUrl") or ""
        script_lines.append(
            "results.push(await (async () => {"
            f"  const endpoint = {{ pi_provider: {provider!r}, model: {model_id!r}, base_url: {base_url!r} }};"
            f"  const transport = ({{ openai_compat: 'openai-completions', openai_responses: 'openai-responses',"
            "    anthropic_compat: 'anthropic-messages', openai_codex: 'openai-codex-responses' })"
            f"    [{kind!r}];"
            "  try {"
            "    const outcome = await resolveCapabilities(endpoint, transport);"
            "    return { binds: true, source: outcome.receipt.capability_source };"
            "  } catch (error) { return { binds: false, error: String(error?.message || error) }; }"
            "})());"
        )
    script_lines.append("console.log(JSON.stringify(results));")
    probe = subprocess.run(
        ["node", "--input-type=module", "-e", "\n".join(script_lines)],
        cwd=str(REPO_ROOT / "pi-runtime"),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert probe.returncode == 0, f"worker bind probe failed: {probe.stderr}"
    results = json.loads(probe.stdout)
    index = 0
    for api, provider, model_id, _kind, binds in CASES:
        if provider == "azure-openai-responses":
            continue
        result = results[index]
        index += 1
        if binds:
            assert result["binds"], (
                f"{provider}/{model_id} (api={api}) must bind on the policy-derived kind: "
                f"{result.get('error')} (F-1 recurrence)"
            )
            assert result["source"] == "pi_builtin"
        else:
            assert not result["binds"], f"{provider}/{model_id} unexpectedly bound — gate lost?"
            assert result["error"].startswith("provider_transport_mismatch:"), (
                f"{provider}/{model_id} must reject TYPED pre-network, got: {result['error']}"
            )
