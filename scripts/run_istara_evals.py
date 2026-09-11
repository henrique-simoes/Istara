#!/usr/bin/env python3
"""Run versioned Istara AI evaluations.

The runner is intentionally local-first and single-model:

- live calls use the one configured OpenAI-compatible profile from
  tests.llm_test_config
- the checked-in model id is google/gemma-4-e4b
- endpoint URLs and API keys are never written to artifacts
- static subsystem probes use Istara modules directly where doing so is safe
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

DEFAULT_REGISTRY = ROOT / "tests" / "evals" / "registry.json"
DEFAULT_CASES = ROOT / "tests" / "evals" / "cases" / "core_eval_cases.json"
DEFAULT_RESULTS_ROOT = ROOT / "tests" / "evals" / ".results"
DEFAULT_COMPASS_SPEC = "CF-SPEC-26"
DEFAULT_COMPASS_TASK = "CF-295"

PRIVATE_IP_RE = re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class EvalConfig:
    suite: str
    registry_path: Path
    cases_path: Path
    output_dir: Path | None
    require_live_llm: bool
    max_live_cases: int | None
    timeout_seconds: float
    fail_on_threshold: bool
    compass_spec: str
    compass_task: str
    allow_unignored_output: bool = False
    # CF-341: which agentic engine serves live cases. "legacy" keeps the original
    # compute_registry.chat path (byte-compatible); "pi" routes the same cases
    # through AgenticDispatcher.completion on an injected profile endpoint.
    engine: str = "legacy"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return ""
    return result.stdout.strip()


def git_metadata() -> dict[str, Any]:
    status = run_git(["status", "--short"])
    changed_paths = [line for line in status.splitlines() if line.strip()]
    return {
        "head": run_git(["rev-parse", "HEAD"]),
        "short_head": run_git(["rev-parse", "--short", "HEAD"]),
        "branch": run_git(["branch", "--show-current"]),
        "dirty": bool(changed_paths),
        "changed_path_count": len(changed_paths),
        "status_sha256": sha256_text(status),
    }


def clean_run_id(git_meta: dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_head = git_meta.get("short_head") or "nogit"
    dirty = "-dirty" if git_meta.get("dirty") else ""
    return f"{timestamp}-{short_head}{dirty}"


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_eval_output_dir(config: EvalConfig, git_meta: dict[str, Any]) -> Path:
    output_dir = config.output_dir or (DEFAULT_RESULTS_ROOT / clean_run_id(git_meta))
    if config.output_dir is None or config.allow_unignored_output:
        return output_dir

    resolved_output = output_dir.resolve()
    resolved_results_root = DEFAULT_RESULTS_ROOT.resolve()
    if resolved_output == resolved_results_root or _path_is_within(
        resolved_output,
        resolved_results_root,
    ):
        return output_dir

    raise ValueError(
        "Custom --output-dir must live under tests/evals/.results or pass "
        "--allow-unignored-output so eval runtime_data cannot land in tracked space."
    )


def load_live_profile_metadata() -> dict[str, Any]:
    from tests.llm_test_config import (
        PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
        PRIMARY_TEST_MODEL,
        current_primary_llm_profile,
        get_live_llm_api_key,
    )

    profile = current_primary_llm_profile()
    api_key = get_live_llm_api_key()
    endpoint_fingerprint = ""
    if profile.base_url:
        endpoint_fingerprint = sha256_text(profile.base_url)[:16]
    return {
        "profile_name": profile.name,
        "provider_type": profile.provider_type,
        "model": PRIMARY_TEST_MODEL,
        "base_url_configured": bool(profile.base_url),
        "api_key_configured": bool(api_key),
        "endpoint_fingerprint": endpoint_fingerprint,
        "primary_attempt_budget": PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
    }


def sanitize_text(value: str, *, extra_secrets: list[str] | None = None) -> str:
    sanitized = value
    for secret in extra_secrets or []:
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")
    for env_name in (
        "ISTARA_LIVE_LLM_BASE_URL",
        "ISTARA_PRIMARY_LLM_TEST_BASE_URL",
        "ISTARA_LIVE_LLM_API_KEY",
        "ISTARA_LLM_TEST_API_KEY",
        "ISTARA_PRIMARY_LLM_TEST_API_KEY",
        "LMSTUDIO_API_KEY",
    ):
        env_value = os.getenv(env_name, "")
        if env_value:
            sanitized = sanitized.replace(env_value, f"[REDACTED_{env_name}]")
    sanitized = PRIVATE_IP_RE.sub("[REDACTED_PRIVATE_IP]", sanitized)
    sanitized = re.sub(r"(?i)bearer\s+[A-Za-z0-9_.=-]+", "Bearer [REDACTED]", sanitized)
    return sanitized


def build_manifest(
    *,
    config: EvalConfig,
    registry: dict[str, Any],
    cases: dict[str, Any],
    output_dir: Path,
    loaded_env_files: int,
) -> dict[str, Any]:
    git_meta = git_metadata()
    live_meta = load_live_profile_metadata()
    return {
        "schema_version": 1,
        "run_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "compass": {
            "spec": config.compass_spec,
            "task": config.compass_task,
        },
        "git": git_meta,
        "registry": {
            "path": str(config.registry_path.relative_to(ROOT)),
            "sha256": sha256_file(config.registry_path),
            "registry_id": registry.get("registry_id"),
            "registry_version": registry.get("registry_version"),
        },
        "cases": {
            "path": str(config.cases_path.relative_to(ROOT)),
            "sha256": sha256_file(config.cases_path),
            "live_case_count": len(cases.get("live_cases", [])),
            "static_case_count": len(cases.get("static_cases", [])),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "loaded_gitignored_env_file_count": loaded_env_files,
        },
        "live_llm": live_meta,
        "command": {
            "suite": config.suite,
            "require_live_llm": config.require_live_llm,
            "max_live_cases": config.max_live_cases,
            "timeout_seconds": config.timeout_seconds,
            "fail_on_threshold": config.fail_on_threshold,
            "allow_unignored_output": config.allow_unignored_output,
        },
    }


def should_run_suite(selected: str, suite_id: str, *, live: bool) -> bool:
    if selected in {"all", "core"}:
        return True
    if selected == "static":
        return not live
    if selected == "live":
        return live
    return selected == suite_id


def extract_json_object(text: str) -> tuple[dict[str, Any] | None, str]:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = JSON_OBJECT_RE.search(stripped)
        if not match:
            return None, "no JSON object found"
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            return None, f"JSON parse error: {exc}"
    if not isinstance(parsed, dict):
        return None, "top-level JSON is not an object"
    return parsed, ""


def value_at_path(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def validate_dag_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return False, "nodes and edges must be lists"
    node_ids = set()
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            return False, "each node must have an id"
        node_ids.add(str(node["id"]))
    graph: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2:
            return False, "each edge must be a [from, to] pair"
        src, dst = str(edge[0]), str(edge[1])
        if src not in node_ids or dst not in node_ids:
            return False, "edge references unknown node"
        graph[src].append(dst)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return False
        if node_id in visited:
            return True
        visiting.add(node_id)
        for child in graph[node_id]:
            if not visit(child):
                return False
        visiting.remove(node_id)
        visited.add(node_id)
        return True

    for node_id in node_ids:
        if not visit(node_id):
            return False, "cycle detected"
    return True, "acyclic"


def evaluate_checks(
    text: str, checks: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    parsed: dict[str, Any] | None = None

    if checks.get("json_object"):
        parsed, error = extract_json_object(text)
        passed = parsed is not None
        results.append(
            {"name": "json_object", "passed": passed, "detail": error or "valid"}
        )
        metrics["json_validity"] = 1.0 if passed else 0.0

    if parsed is not None:
        required_keys = checks.get("json_keys", [])
        if required_keys:
            present = [key for key in required_keys if key in parsed]
            passed = len(present) == len(required_keys)
            results.append(
                {
                    "name": "json_keys",
                    "passed": passed,
                    "detail": f"{len(present)}/{len(required_keys)} keys present",
                }
            )
            metrics["required_key_coverage"] = len(present) / max(1, len(required_keys))

        for field, expected in checks.get("field_equals", {}).items():
            actual = value_at_path(parsed, field)
            passed = str(actual).strip() == str(expected)
            results.append(
                {
                    "name": f"field_equals:{field}",
                    "passed": passed,
                    "detail": f"expected {expected!r}, got {actual!r}",
                }
            )
            metrics[f"exact_{field}"] = 1.0 if passed else 0.0

        for field, expected_substring in checks.get("nested_contains", {}).items():
            actual = value_at_path(parsed, field)
            passed = expected_substring.lower() in str(actual).lower()
            results.append(
                {
                    "name": f"nested_contains:{field}",
                    "passed": passed,
                    "detail": f"expected substring {expected_substring!r}",
                }
            )

        if checks.get("dag"):
            passed, detail = validate_dag_payload(parsed)
            results.append({"name": "dag", "passed": passed, "detail": detail})
            metrics["dag_validity"] = 1.0 if passed else 0.0

    for expected in checks.get("contains", []):
        passed = expected.lower() in text.lower()
        results.append({"name": f"contains:{expected}", "passed": passed, "detail": ""})

    contains_any = checks.get("contains_any", [])
    if contains_any:
        lowered = text.lower()
        matched = [item for item in contains_any if item.lower() in lowered]
        results.append(
            {
                "name": "contains_any",
                "passed": bool(matched),
                "detail": ", ".join(matched),
            }
        )

    return results, metrics


def _import_all_models() -> None:
    """Import every model module so the SQLAlchemy mapper registry is complete.

    The dispatcher's usage-ledger write touches ORM relationships (e.g.
    Project -> Message); in a bare script context those mappers are only
    configured once every model module has been imported.
    """
    import importlib
    import pathlib

    models_dir = (
        pathlib.Path(__file__).resolve().parents[1] / "backend" / "app" / "models"
    )
    for path in sorted(models_dir.glob("*.py")):
        if path.stem != "__init__":
            importlib.import_module(f"app.models.{path.stem}")


async def _run_live_case_pi(
    case: dict[str, Any],
    *,
    timeout_seconds: float,
    started: float,
) -> dict[str, Any]:
    """Serve one live case through the Pi engine (CF-341).

    Same configured live profile as the legacy path (tests/llm_test_config), but
    dispatched through AgenticDispatcher.completion on an explicitly injected
    PiModelManager endpoint — the pi arm of the same serving target, so paired
    legacy/pi eval runs isolate the ENGINE, not the model.
    """
    from tests.llm_test_config import current_primary_llm_profile, get_live_llm_api_key
    from app.core.agentic.dispatcher import AgenticDispatcher
    from app.core.agentic.types import TurnParams
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint
    from app.core.pi_runtime.engine import PiExecutionService
    from app.core.pi_runtime.model_manager import PiModelManager

    profile = current_primary_llm_profile()
    api_key = get_live_llm_api_key()
    _import_all_models()  # complete the SQLAlchemy mapper registry before ledger writes
    import os as _os

    eval_model = _os.getenv("ISTARA_EVALS_MODEL", profile.model)
    endpoint = ResolvedPiEndpoint(
        endpoint_id="eval-live-profile",
        provider_kind="openai_compat",
        base_url=profile.base_url,
        model=eval_model,
        api_key=api_key,
        timeout_ms=int(timeout_seconds * 1000),
        max_retries=0,
    )
    manager = PiModelManager(endpoints=[endpoint])
    dispatcher = AgenticDispatcher(pi_service=PiExecutionService(model_manager=manager))
    outcome = await asyncio.wait_for(
        dispatcher.completion(
            purpose=f"istara_evals.{case['suite']}",
            project_id="istara-evals",
            system=None,
            messages=case.get("messages", []),
            params=TurnParams(
                endpoint_id="eval-live-profile",
                model=eval_model,
                temperature=0.0,
                max_tokens=int(case.get("max_tokens", 256)),
            ),
            engine="pi",
        ),
        timeout=timeout_seconds,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    visible_text = str(getattr(outcome, "text", "") or "")
    check_results, metrics = evaluate_checks(visible_text, case.get("checks", {}))
    if not check_results:
        check_results = [
            {"name": "response_nonempty", "passed": bool(visible_text), "detail": ""}
        ]
    passed = all(item["passed"] for item in check_results)
    metrics["latency_ms"] = duration_ms
    metrics["output_chars"] = len(visible_text)
    metrics["llm_serving_path"] = "agentic_dispatcher.completion:pi"
    usage = getattr(outcome, "usage", None) or {}
    if usage:
        metrics["usage"] = {
            k: usage.get(k)
            for k in ("input_tokens", "output_tokens", "total_tokens")
            if usage.get(k) is not None
        }
    return {
        "case_id": case["id"],
        "suite": case["suite"],
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": duration_ms,
        "checks": check_results,
        "metrics": metrics,
        "response_preview": sanitize_text(visible_text[:500]),
        "response_text": sanitize_text(visible_text),
    }


async def run_live_case(
    case: dict[str, Any],
    *,
    timeout_seconds: float,
    require_live_llm: bool,
    engine: str = "legacy",
) -> dict[str, Any]:
    from tests.llm_test_config import (
        PRIMARY_LIVE_LLM_MAX_ATTEMPTS,
        configure_live_compute_registry,
        current_primary_llm_profile,
        get_live_llm_api_key,
    )
    from app.config import settings
    from app.core.compute_registry import compute_registry
    from app.core.llm_output import visible_assistant_content

    started = time.perf_counter()
    profile = current_primary_llm_profile()
    api_key = get_live_llm_api_key()
    if engine == "pi" and profile.base_url and api_key:
        try:
            return await _run_live_case_pi(
                case, timeout_seconds=timeout_seconds, started=started
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            return {
                "case_id": case["id"],
                "suite": case["suite"],
                "status": "failed",
                "score": 0.0,
                "duration_ms": duration_ms,
                "checks": [
                    {
                        "name": "live_call_pi",
                        "passed": False,
                        "detail": sanitize_text(type(exc).__name__),
                    }
                ],
                "metrics": {
                    "latency_ms": duration_ms,
                    "llm_serving_path": "agentic_dispatcher.completion:pi",
                },
            }
    if not profile.base_url or not api_key:
        status = "failed" if require_live_llm else "blocked"
        return {
            "case_id": case["id"],
            "suite": case["suite"],
            "status": status,
            "score": 0.0,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "checks": [
                {
                    "name": "live_llm_configured",
                    "passed": False,
                    "detail": "live LLM base URL or API key is not configured",
                }
            ],
            "metrics": {},
        }

    original_nodes = dict(compute_registry._nodes)
    settings_snapshot = {
        "llm_provider": settings.llm_provider,
        "lmstudio_host": settings.lmstudio_host,
        "lmstudio_model": settings.lmstudio_model,
        "lmstudio_api_key": settings.lmstudio_api_key,
        "strict_auto_routing": settings.strict_auto_routing,
    }
    try:
        configure_live_compute_registry(clear_existing=True)
        import os as _os

        response = await asyncio.wait_for(
            compute_registry.chat(
                case.get("messages", []),
                model=_os.getenv("ISTARA_EVALS_MODEL", profile.model),
                temperature=0,
                max_tokens=int(case.get("max_tokens", 256)),
                thinking_mode=case.get("thinking_mode", "off"),
            ),
            timeout=timeout_seconds,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        message = response.get("message") if isinstance(response, dict) else {}
        visible_text = visible_assistant_content(message)
        check_results, metrics = evaluate_checks(visible_text, case.get("checks", {}))
        if not check_results:
            check_results = [
                {
                    "name": "response_nonempty",
                    "passed": bool(visible_text),
                    "detail": "",
                }
            ]
        passed = all(item["passed"] for item in check_results)
        metrics["latency_ms"] = duration_ms
        metrics["output_chars"] = len(visible_text)
        metrics["llm_serving_path"] = "compute_registry.chat"
        metrics["primary_attempt_budget"] = PRIMARY_LIVE_LLM_MAX_ATTEMPTS
        return {
            "case_id": case["id"],
            "suite": case["suite"],
            "status": "passed" if passed else "failed",
            "score": 1.0 if passed else 0.0,
            "duration_ms": duration_ms,
            "checks": check_results,
            "metrics": metrics,
            "response_preview": sanitize_text(visible_text[:500]),
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        detail = sanitize_text(type(exc).__name__)
        return {
            "case_id": case["id"],
            "suite": case["suite"],
            "status": "failed",
            "score": 0.0,
            "duration_ms": duration_ms,
            "checks": [{"name": "live_call", "passed": False, "detail": detail}],
            "metrics": {"latency_ms": duration_ms},
        }
    finally:
        for node in list(compute_registry._nodes.values()):
            client = getattr(node, "_client", None)
            if client is not None and not getattr(client, "is_closed", True):
                await client.aclose()
        compute_registry._nodes.clear()
        compute_registry._nodes.update(original_nodes)
        for attr, value in settings_snapshot.items():
            setattr(settings, attr, value)


async def eval_rag_keyword_gold(output_dir: Path) -> dict[str, Any]:
    from app.config import settings
    from app.core.embeddings import TextChunk
    from app.core.keyword_index import KeywordIndex
    from app.core import rag as rag_module

    started = time.perf_counter()
    runtime_dir = output_dir / "runtime_data" / "rag"
    original_data_dir = settings.data_dir
    original_lance_db_path = settings.lance_db_path
    settings.data_dir = str(runtime_dir)
    settings.lance_db_path = str(runtime_dir / "lance_db")
    project_id = "eval_rag_keyword_gold"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    chunks = [
        TextChunk(
            text="Checkout friction evidence: participants abandoned checkout when the payment retry banner hid the shipping estimate.",
            source="gold_checkout.md",
            page=1,
            position=0,
        ),
        TextChunk(
            text="Dashboard color preferences were mixed and unrelated to checkout payment retry behavior.",
            source="distractor_dashboard.md",
            page=1,
            position=1,
        ),
        TextChunk(
            text="Search navigation improved after adding filters, but this did not mention payment retry banners.",
            source="distractor_search.md",
            page=1,
            position=2,
        ),
    ]
    original_embed_text = rag_module.embed_text

    async def unavailable_embed(_: str) -> list[float]:
        raise RuntimeError("eval forces keyword fallback")

    try:
        await KeywordIndex(project_id).add_chunks(chunks)
        rag_module.embed_text = unavailable_embed
        context = await rag_module.retrieve_context(
            project_id,
            "Which evidence explains checkout payment retry friction?",
            top_k=3,
        )
    finally:
        rag_module.embed_text = original_embed_text
        settings.data_dir = original_data_dir
        settings.lance_db_path = original_lance_db_path

    sources = [item.source for item in context.retrieved]
    gold_hits = [
        item for item in context.retrieved if item.source == "gold_checkout.md"
    ]
    precision_at_1 = 1.0 if sources[:1] == ["gold_checkout.md"] else 0.0
    recall_at_3 = 1.0 if gold_hits else 0.0
    checks = [
        {
            "name": "has_context",
            "passed": context.has_context,
            "detail": f"{len(context.retrieved)} hits",
        },
        {
            "name": "gold_source_retrieved",
            "passed": bool(gold_hits),
            "detail": ", ".join(sources),
        },
        {
            "name": "gold_source_ranked_first",
            "passed": precision_at_1 == 1.0,
            "detail": ", ".join(sources[:3]),
        },
        {
            "name": "context_is_guard_wrapped",
            "passed": "gold_checkout.md" in context.context_text,
            "detail": "",
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "rag_keyword_gold",
        "suite": "rag",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "context_precision_at_1": precision_at_1,
            "context_recall_at_3": recall_at_3,
            "retrieved_count": len(context.retrieved),
        },
    }


async def eval_prompt_rag(output_dir: Path) -> dict[str, Any]:
    from app.config import settings
    from app.core.prompt_rag import compose_keyword_prompt

    started = time.perf_counter()
    agent_id = "eval-agent"
    runtime_personas = output_dir / "runtime_data" / "personas"
    persona_dir = runtime_personas / agent_id
    if persona_dir.exists():
        shutil.rmtree(persona_dir)
    persona_dir.mkdir(parents=True, exist_ok=True)
    original_runtime_personas = settings.runtime_personas_dir
    original_context_tokens = settings.max_context_tokens
    settings.runtime_personas_dir = str(runtime_personas)
    settings.max_context_tokens = 4096
    try:
        (persona_dir / "CORE.md").write_text(
            "# Eval Agent\n\n"
            "## Identity\n"
            "You are Eval Agent, an Istara research assistant with stable identity.\n\n"
            "## Personality\n"
            "Careful, evidence-driven, and concise.\n\n"
            "## Values\n"
            "Ground every recommendation in research evidence.\n\n"
            "## Irrelevant Billing Protocol\n"
            "Discuss invoice aging and procurement codes only when asked.\n",
            encoding="utf-8",
        )
        (persona_dir / "SKILLS.md").write_text(
            "## Usability Interview Planning\n"
            "Use interview guides, recruiting criteria, consent, and note templates for usability interviews.\n\n"
            "## Accessibility Review\n"
            "Use WCAG, keyboard navigation, screen reader checks, and contrast review for accessibility audits.\n",
            encoding="utf-8",
        )
        (persona_dir / "PROTOCOLS.md").write_text(
            "## Evidence Synthesis\n"
            "Retrieve notes, code themes, cite source documents, and separate findings from recommendations.\n",
            encoding="utf-8",
        )
        prompt = compose_keyword_prompt(
            agent_id,
            "Plan usability interviews and synthesize the evidence.",
            max_tokens=500,
            top_k=3,
        )
    finally:
        settings.runtime_personas_dir = original_runtime_personas
        settings.max_context_tokens = original_context_tokens

    checks = [
        {
            "name": "identity_anchor_survives",
            "passed": "You are Eval Agent" in prompt,
            "detail": "",
        },
        {
            "name": "relevant_section_selected",
            "passed": "Usability Interview Planning" in prompt,
            "detail": "",
        },
        {
            "name": "synthesis_section_selected",
            "passed": "Evidence Synthesis" in prompt,
            "detail": "",
        },
        {
            "name": "distractor_suppressed",
            "passed": "Irrelevant Billing Protocol" not in prompt,
            "detail": "",
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "prompt_rag_identity_and_relevance",
        "suite": "prompt_rag",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "identity_anchor_survival": 1.0 if checks[0]["passed"] else 0.0,
            "composed_chars": len(prompt),
            "token_estimate": len(prompt) // 4,
        },
    }


async def eval_llmlingua() -> dict[str, Any]:
    from app.core.prompt_compressor import compress_prompt

    started = time.perf_counter()
    protected = (
        "<research_methodology>"
        "CRITICAL_BRAUN_CLARKE_CODEBOOK_ALPHA must remain intact."
        "</research_methodology>"
    )
    filler = " ".join(
        [
            "It is important to note that the team should very carefully and basically review redundant notes."
            for _ in range(35)
        ]
    )
    prompt = (
        f"# Identity\nKeep evidence.\n\n## Method\n{protected}\n\n## Notes\n{filler}"
    )
    compressed = compress_prompt(prompt, max_chars=900)
    ratio = len(compressed) / len(prompt)
    checks = [
        {
            "name": "compressed_smaller",
            "passed": len(compressed) < len(prompt),
            "detail": f"{len(prompt)} to {len(compressed)} chars",
        },
        {
            "name": "protected_block_survives",
            "passed": protected in compressed,
            "detail": "",
        },
        {
            "name": "critical_term_survives",
            "passed": "CRITICAL_BRAUN_CLARKE_CODEBOOK_ALPHA" in compressed,
            "detail": "",
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "llmlingua_protected_context",
        "suite": "llmlingua",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "compression_ratio": round(ratio, 4),
            "compressed_chars": len(compressed),
        },
    }


async def eval_reasoning_bank() -> dict[str, Any]:
    from app.core.reasoning_bank import ReasoningMemoryService

    started = time.perf_counter()
    service = ReasoningMemoryService()
    memories = service.extract_memory_items(
        query="Fix checkout retry failure",
        trajectory={
            "step": "called payment_retry",
            "api_key": "secret-value-should-disappear",
        },
        outcome="failure",
        source_kind="tool_calling_react",
        source_id="eval-trace-1",
        tags=["checkout", "payment"],
        domain="checkout",
        judge_score=0.42,
    )
    memory = memories[0]
    serialized = json.dumps(memory, default=str)
    checks = [
        {"name": "one_memory_extracted", "passed": len(memories) == 1, "detail": ""},
        {
            "name": "failure_outcome_tagged",
            "passed": memory.get("outcome") == "failure",
            "detail": "",
        },
        {
            "name": "source_kind_tagged",
            "passed": "tool_calling_react" in memory.get("tags", []),
            "detail": "",
        },
        {
            "name": "secret_redacted",
            "passed": "secret-value-should-disappear" not in serialized
            and "[REDACTED]" in serialized,
            "detail": "",
        },
        {
            "name": "confidence_bounded",
            "passed": 0.0 <= float(memory.get("confidence", -1)) <= 1.0,
            "detail": str(memory.get("confidence")),
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "reasoning_bank_distillation_redaction",
        "suite": "memory_reasoning_bank",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "distilled_memories": len(memories),
            "secret_redaction": 1.0 if checks[3]["passed"] else 0.0,
            "confidence": memory.get("confidence"),
        },
    }


async def eval_memento_skills() -> dict[str, Any]:
    from app.skills.skill_manager import SOURCE_SKILLS_DIR, SkillDefinition

    started = time.perf_counter()
    paths = sorted(
        path
        for path in SOURCE_SKILLS_DIR.glob("*.json")
        if not path.name.startswith("_")
    )
    valid = 0
    enabled = 0
    output_schema_count = 0
    names: set[str] = set()
    errors: list[str] = []
    for path in paths:
        try:
            definition = SkillDefinition(path)
            valid += 1
            names.add(definition.name)
            enabled += 1 if definition.enabled else 0
            output_schema_count += 1 if definition.data.get("output_schema") else 0
        except Exception as exc:
            errors.append(f"{path.name}: {type(exc).__name__}")
    expected = {
        "research-synthesis",
        "thematic-analysis",
        "survey-generator",
        "transcribe-audio",
    }
    checks = [
        {
            "name": "skill_definitions_present",
            "passed": len(paths) >= 40,
            "detail": str(len(paths)),
        },
        {
            "name": "skill_definitions_valid",
            "passed": valid == len(paths),
            "detail": "; ".join(errors[:5]),
        },
        {
            "name": "output_schema_coverage",
            "passed": output_schema_count == len(paths),
            "detail": f"{output_schema_count}/{len(paths)}",
        },
        {
            "name": "expected_core_skills_present",
            "passed": expected <= names,
            "detail": ", ".join(sorted(expected - names)),
        },
        {
            "name": "enabled_skill_coverage",
            "passed": enabled >= max(1, int(len(paths) * 0.8)),
            "detail": f"{enabled}/{len(paths)}",
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "memento_skill_definition_coverage",
        "suite": "memento_skills",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "skill_count": len(paths),
            "valid_skill_count": valid,
            "enabled_skill_count": enabled,
            "output_schema_coverage": output_schema_count / max(1, len(paths)),
        },
    }


async def eval_meta_hyperagent() -> dict[str, Any]:
    from app.core.meta_hyperagent import (
        MAX_ACTIVE_VARIANTS,
        PARAMETER_BOUNDS,
        MetaHyperagent,
    )

    started = time.perf_counter()
    meta = MetaHyperagent()
    checks = [
        {
            "name": "skill_threshold_bounds_present",
            "passed": "agent.skill_similarity_threshold" in PARAMETER_BOUNDS,
            "detail": str(PARAMETER_BOUNDS.get("agent.skill_similarity_threshold")),
        },
        {
            "name": "valid_bound_accepted",
            "passed": meta._validate_bounds("agent.skill_similarity_threshold", 0.5),
            "detail": "",
        },
        {
            "name": "invalid_bound_rejected",
            "passed": not meta._validate_bounds(
                "agent.skill_similarity_threshold", 1.5
            ),
            "detail": "",
        },
        {
            "name": "active_variant_cap_hardened",
            "passed": MAX_ACTIVE_VARIANTS == 3,
            "detail": str(MAX_ACTIVE_VARIANTS),
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "meta_hyperagent_bounds",
        "suite": "meta_hyperagent",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "parameter_bound_count": len(PARAMETER_BOUNDS),
            "max_active_variants": MAX_ACTIVE_VARIANTS,
        },
    }


async def eval_thinking_output() -> dict[str, Any]:
    from app.core.llm_output import visible_assistant_content
    from app.core.llm_thinking import (
        apply_thinking_control,
        normalize_thinking_mode,
        thinking_marker_registry,
    )

    started = time.perf_counter()
    qwen = visible_assistant_content({"content": "<think>hidden</think>Final answer"})
    gemma = visible_assistant_content(
        {"content": "<|channel>thought hidden <channel|>Visible"}
    )
    controlled = apply_thinking_control([{"role": "user", "content": "Hi"}], "off")
    registry = thinking_marker_registry()
    checks = [
        {
            "name": "invalid_mode_defaults",
            "passed": normalize_thinking_mode("banana") == "server_default",
            "detail": "",
        },
        {
            "name": "off_directive_injected",
            "passed": controlled[0]["role"] == "system"
            and "thinking mode is OFF" in controlled[0]["content"],
            "detail": "",
        },
        {
            "name": "qwen_thinking_stripped",
            "passed": qwen == "Final answer",
            "detail": qwen,
        },
        {
            "name": "gemma_thought_stripped",
            "passed": gemma == "Visible",
            "detail": gemma,
        },
        {
            "name": "marker_registry_covers_families",
            "passed": {"qwen", "gemma", "openai", "anthropic"} <= set(registry),
            "detail": ", ".join(sorted(registry)),
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "thinking_marker_sanitization",
        "suite": "thinking_output",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "marker_family_count": len(registry),
            "visible_output_safety": 1.0 if passed else 0.0,
        },
    }


async def eval_voice_transcription(output_dir: Path) -> dict[str, Any]:
    from app.core.transcription import (
        _generate_transcription_tags,
        transcribe_audio,
        transcription_dependency_status,
    )

    started = time.perf_counter()
    missing_path = output_dir / "runtime_data" / "missing-audio.wav"
    result = transcribe_audio(str(missing_path))
    tags = _generate_transcription_tags(
        "Um I think the menu is confusing and the screen reader cannot find the button."
    )
    status = transcription_dependency_status()
    checks = [
        {
            "name": "dependency_status_shape",
            "passed": "ffmpeg_available" in status and "whisper_available" in status,
            "detail": "",
        },
        {
            "name": "missing_file_typed_failure",
            "passed": result.metadata.get("error_type") == "audio_file_missing",
            "detail": str(result.metadata),
        },
        {
            "name": "missing_file_needs_review",
            "passed": result.needs_review is True,
            "detail": "",
        },
        {
            "name": "spoken_tags_detected",
            "passed": {"navigation", "accessibility", "spoken-style"} <= set(tags),
            "detail": ", ".join(tags),
        },
    ]
    passed = all(item["passed"] for item in checks)
    return {
        "case_id": "voice_transcription_contract",
        "suite": "voice_transcription",
        "status": "passed" if passed else "failed",
        "score": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
        "metrics": {
            "ffmpeg_available": bool(status.get("ffmpeg_available")),
            "whisper_available": bool(status.get("whisper_available")),
            "tag_count": len(tags),
        },
    }


STATIC_EVALS = {
    "rag_keyword_gold": eval_rag_keyword_gold,
    "prompt_rag_identity_and_relevance": eval_prompt_rag,
    "llmlingua_protected_context": lambda _output_dir: eval_llmlingua(),
    "reasoning_bank_distillation_redaction": lambda _output_dir: eval_reasoning_bank(),
    "memento_skill_definition_coverage": lambda _output_dir: eval_memento_skills(),
    "meta_hyperagent_bounds": lambda _output_dir: eval_meta_hyperagent(),
    "thinking_marker_sanitization": lambda _output_dir: eval_thinking_output(),
    "voice_transcription_contract": eval_voice_transcription,
}


async def run_eval_suite(config: EvalConfig) -> dict[str, Any]:
    from tests.llm_test_config import load_gitignored_live_env

    loaded_env_files = load_gitignored_live_env()
    registry = read_json(config.registry_path)
    cases = read_json(config.cases_path)
    git_meta = git_metadata()
    output_dir = resolve_eval_output_dir(config, git_meta)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(
        config=config,
        registry=registry,
        cases=cases,
        output_dir=output_dir,
        loaded_env_files=loaded_env_files,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    results: list[dict[str, Any]] = []

    live_cases = [
        case
        for case in cases.get("live_cases", [])
        if should_run_suite(config.suite, case.get("suite", ""), live=True)
    ]
    if config.max_live_cases is not None:
        live_cases = live_cases[: max(0, config.max_live_cases)]
    for case in live_cases:
        results.append(
            await run_live_case(
                case,
                timeout_seconds=config.timeout_seconds,
                require_live_llm=config.require_live_llm,
                engine=config.engine,
            )
        )

    for case in cases.get("static_cases", []):
        if not should_run_suite(config.suite, case.get("suite", ""), live=False):
            continue
        fn = STATIC_EVALS.get(case["id"])
        if fn is None:
            results.append(
                {
                    "case_id": case["id"],
                    "suite": case["suite"],
                    "status": "blocked",
                    "score": 0.0,
                    "checks": [
                        {
                            "name": "static_eval_registered",
                            "passed": False,
                            "detail": "missing function",
                        }
                    ],
                    "metrics": {},
                }
            )
            continue
        results.append(await fn(output_dir))

    results_jsonl = "\n".join(json.dumps(item, default=str) for item in results) + "\n"
    (output_dir / "results.jsonl").write_text(results_jsonl, encoding="utf-8")
    summary = summarize_results(results, registry=registry, output_dir=output_dir)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        render_report(summary, results, manifest), encoding="utf-8"
    )
    return {
        "manifest": manifest,
        "summary": summary,
        "results": results,
        "output_dir": output_dir,
    }


def summarize_results(
    results: list[dict[str, Any]],
    *,
    registry: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    suite_thresholds = {
        suite["id"]: suite.get("thresholds", {}) for suite in registry.get("suites", [])
    }
    suites: dict[str, dict[str, Any]] = {}
    for item in results:
        suite_id = item.get("suite", "unknown")
        bucket = suites.setdefault(
            suite_id,
            {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "score_sum": 0.0,
                "metrics": {},
            },
        )
        bucket["total"] += 1
        status = item.get("status")
        if status == "passed":
            bucket["passed"] += 1
        elif status == "blocked":
            bucket["blocked"] += 1
        else:
            bucket["failed"] += 1
        bucket["score_sum"] += float(item.get("score", 0.0))
        for key, value in item.get("metrics", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metric_bucket = bucket["metrics"].setdefault(key, [])
                metric_bucket.append(float(value))

    threshold_violations: list[dict[str, Any]] = []
    for suite_id, bucket in suites.items():
        total = max(1, bucket["total"])
        bucket["pass_rate"] = bucket["passed"] / total
        bucket["average_score"] = bucket["score_sum"] / total
        bucket["metrics"] = {
            key: {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }
            for key, values in bucket["metrics"].items()
        }
        thresholds = suite_thresholds.get(suite_id, {})
        pass_rate_threshold = thresholds.get("pass_rate")
        if (
            pass_rate_threshold is not None
            and bucket["pass_rate"] < pass_rate_threshold
        ):
            threshold_violations.append(
                {
                    "suite": suite_id,
                    "metric": "pass_rate",
                    "threshold": pass_rate_threshold,
                    "actual": bucket["pass_rate"],
                }
            )

    totals = {
        "total": len(results),
        "passed": sum(1 for item in results if item.get("status") == "passed"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
        "blocked": sum(1 for item in results if item.get("status") == "blocked"),
    }
    totals["pass_rate"] = totals["passed"] / max(1, totals["total"])
    status = "pass" if totals["failed"] == 0 and not threshold_violations else "fail"
    if totals["blocked"] and totals["failed"] == 0 and not threshold_violations:
        status = "warn"
    return {
        "schema_version": 1,
        "status": status,
        "output_dir": str(output_dir),
        "totals": totals,
        "suites": suites,
        "threshold_violations": threshold_violations,
    }


def render_report(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> str:
    lines = [
        "# Istara AI Eval Report",
        "",
        f"- Status: {summary['status']}",
        f"- Run id: {manifest['run_id']}",
        f"- Git: {manifest['git'].get('short_head')} dirty={manifest['git'].get('dirty')}",
        f"- Compass: {manifest['compass'].get('spec')} / {manifest['compass'].get('task')}",
        f"- Model: {manifest['live_llm'].get('model')}",
        f"- Live profile configured: {manifest['live_llm'].get('base_url_configured')}",
        "",
        "## Totals",
        "",
        json.dumps(summary["totals"], indent=2),
        "",
        "## Suites",
        "",
    ]
    for suite_id, data in sorted(summary["suites"].items()):
        lines.append(f"### {suite_id}")
        lines.append(
            f"- pass_rate: {data['pass_rate']:.3f}; passed={data['passed']} "
            f"failed={data['failed']} blocked={data['blocked']} total={data['total']}"
        )
    lines.extend(["", "## Case Results", ""])
    for item in results:
        lines.append(
            f"- {item.get('suite')}/{item.get('case_id')}: {item.get('status')} "
            f"score={item.get('score')} duration_ms={item.get('duration_ms', 0)}"
        )
        failed_checks = [
            check for check in item.get("checks", []) if not check.get("passed")
        ]
        for check in failed_checks[:5]:
            lines.append(
                f"  - failed check {check.get('name')}: {check.get('detail', '')}"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> EvalConfig:
    parser = argparse.ArgumentParser(description="Run versioned Istara AI evals.")
    parser.add_argument(
        "--suite",
        default="all",
        help="Suite selector: all, core, static, live, or a suite id from tests/evals/registry.json.",
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--require-live-llm", action="store_true")
    parser.add_argument("--max-live-cases", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--engine",
        choices=["legacy", "pi"],
        default="legacy",
        help="agentic engine for live cases (CF-341; default legacy = original behavior)",
    )
    parser.add_argument("--fail-on-threshold", action="store_true")
    parser.add_argument(
        "--allow-unignored-output",
        action="store_true",
        help=(
            "Allow --output-dir outside tests/evals/.results. Use only for explicit "
            "scratch/debug destinations because static evals write runtime_data there."
        ),
    )
    parser.add_argument("--compass-spec", default=DEFAULT_COMPASS_SPEC)
    parser.add_argument("--compass-task", default=DEFAULT_COMPASS_TASK)
    args = parser.parse_args(argv)
    return EvalConfig(
        suite=args.suite,
        registry_path=args.registry,
        cases_path=args.cases,
        output_dir=args.output_dir,
        require_live_llm=args.require_live_llm,
        max_live_cases=args.max_live_cases,
        timeout_seconds=args.timeout,
        fail_on_threshold=args.fail_on_threshold,
        compass_spec=args.compass_spec,
        compass_task=args.compass_task,
        allow_unignored_output=args.allow_unignored_output,
        engine=args.engine,
    )


async def async_main(argv: list[str] | None = None) -> int:
    config = parse_args(argv)
    run = await run_eval_suite(config)
    summary = run["summary"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "totals": summary["totals"],
                "output_dir": str(run["output_dir"]),
                "threshold_violations": summary["threshold_violations"],
            },
            indent=2,
        )
    )
    if config.fail_on_threshold and summary["status"] == "fail":
        return 1
    if config.require_live_llm and summary["totals"].get("blocked", 0):
        return 1
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
