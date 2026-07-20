#!/usr/bin/env python3
"""Istara End-to-End Test — Simulates Sarah's complete user journey.

Runs against a live Istara instance (docker compose up or local dev).
Tests every API endpoint, creates real data, runs real skills,
and verifies the entire system works end-to-end.

Usage:
    python tests/e2e_test.py [--base-url http://localhost:8000]
"""

import argparse
import json
import os
import secrets
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
CANONICAL_CORPUS = Path(__file__).parent / "document_corpus" / "canonical"
CANONICAL_MANIFEST = CANONICAL_CORPUS / "manifest.json"

# Test results tracking
results = []
start_time = time.time()


def read_backend_env() -> dict[str, str]:
    """Read ignored backend/.env values used by local E2E harnesses."""
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def persist_backend_env_value(key: str, value: str) -> None:
    """Persist generated E2E bootstrap credentials to ignored backend/.env."""
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")


def canonical_e2e_files(limit: int = 8) -> list[Path]:
    """Return canonical corpus files for product-level E2E ingestion."""
    manifest = json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    preferred_slices = {
        "interview-heavy",
        "survey-heavy",
        "usability-heavy",
        "findings-reporting",
        "coding-reliability",
        "low-consensus-review",
    }
    selected: list[Path] = []
    for source in manifest.get("sources", []):
        slices = set(source.get("slices", []))
        if not slices.intersection(preferred_slices):
            continue
        if source.get("long_form") is not True:
            continue
        path = CANONICAL_CORPUS / (source.get("relative_path") or source.get("path", ""))
        if path.is_file():
            selected.append(path)
        if len(selected) >= limit:
            break
    if len(selected) < min(limit, 6):
        raise RuntimeError("Canonical E2E corpus selection did not find enough long-form sources.")
    return selected


def authenticate_or_bootstrap_admin(client: httpx.Client) -> None:
    """Authenticate in team mode, creating the first admin only on a fresh server."""
    backend_env = read_backend_env()
    admin_user = (
        os.environ.get("ISTARA_ADMIN_USER")
        or os.environ.get("ADMIN_USERNAME")
        or backend_env.get("ADMIN_USERNAME")
        or "admin"
    )
    admin_pass = (
        os.environ.get("ISTARA_ADMIN_PASSWORD")
        or os.environ.get("ADMIN_PASSWORD")
        or os.environ.get("ISTARA_TEST_ADMIN_PASSWORD")
        or backend_env.get("ADMIN_PASSWORD")
        or "istara123"
    )

    def try_login(username: str, password: str) -> bool:
        if not password:
            return False
        login_resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        if login_resp.status_code != 200:
            return False
        token = login_resp.json().get("token") or login_resp.json().get("access_token", "")
        if not token:
            return False
        client.headers["Authorization"] = f"Bearer {token}"
        print("  ✅ Authenticated with configured admin credentials")
        return True

    if try_login(admin_user, admin_pass):
        return

    if os.environ.get("ISTARA_E2E_ALLOW_LOCAL_TOKEN", "").lower() in {"1", "true", "yes"}:
        backend_path = Path(__file__).parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        try:
            from app.core.auth import create_token

            token = create_token("e2e-admin", admin_user, "admin", mfa_verified=True)
            client.headers["Authorization"] = f"Bearer {token}"
            print("  ✅ Authenticated with local signed E2E token")
            return
        except Exception as exc:
            print(f"  ⚠️  Local signed token fallback failed: {str(exc)[:120]}")

    status_resp = client.get("/api/auth/team-status")
    if status_resp.status_code != 200:
        print("  ⚠️  Could not read team auth status; continuing without auth")
        return
    status = status_resp.json()
    if not status.get("team_mode"):
        return

    if status.get("has_users"):
        raise RuntimeError(
            "TEAM_MODE=true and users already exist, but no working admin credentials were "
            "found. Set ISTARA_ADMIN_PASSWORD or ADMIN_PASSWORD before running E2E."
        )

    bootstrap_pass = (
        os.environ.get("ISTARA_E2E_BOOTSTRAP_PASSWORD")
        or admin_pass
        or f"e2e-{secrets.token_urlsafe(18)}"
    )
    register_resp = client.post(
        "/api/auth/register",
        json={
            "username": admin_user,
            "email": f"{admin_user}@istara.local",
            "password": bootstrap_pass,
            "display_name": "Istara E2E Admin",
        },
        headers={"User-Agent": "IstaraE2E/Bootstrap"},
    )
    if register_resp.status_code != 200:
        raise RuntimeError(
            f"Fresh team-mode admin bootstrap failed: HTTP {register_resp.status_code} "
            f"{register_resp.text[:200]}"
        )

    token = register_resp.json().get("token", "")
    if not token:
        raise RuntimeError("Fresh team-mode admin bootstrap did not return a token.")
    client.headers["Authorization"] = f"Bearer {token}"
    persist_backend_env_value("ADMIN_USERNAME", admin_user)
    persist_backend_env_value("ADMIN_PASSWORD", bootstrap_pass)
    print("  ✅ Bootstrapped first team-mode admin for E2E")


def run_test_step(name, fn):
    """Run a test and record the result."""
    try:
        result = fn()
        results.append(
            {
                "name": name,
                "status": "PASS",
                "detail": str(result)[:200] if result else "OK",
            }
        )
        print(f"  ✅ {name}")
        return result
    except Exception as e:
        results.append({"name": name, "status": "FAIL", "detail": str(e)[:300]})
        print(f"  ❌ {name}: {e}")
        return None


def main():
    global BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.base_url

    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    print("\n🐾 Istara End-to-End Test")
    print(f"   Target: {BASE_URL}")
    print(f"   Canonical corpus: {CANONICAL_CORPUS}")
    print("=" * 60)

    # =========================================================
    # PHASE 0: Authentication
    # =========================================================
    print("\n🔐 Phase 0: Authentication")

    authenticate_or_bootstrap_admin(client)

    # =========================================================
    # PHASE 1: System Health
    # =========================================================
    print("\n📡 Phase 1: System Health")

    run_test_step("Health check", lambda: assert_ok(client.get("/api/health")))
    run_test_step("System status", lambda: assert_ok(client.get("/api/settings/status")))
    run_test_step("Hardware info", lambda: assert_ok(client.get("/api/settings/hardware")))
    run_test_step("Available models", lambda: assert_ok(client.get("/api/settings/models")))
    run_test_step("Resource governor", lambda: assert_ok(client.get("/api/resources")))

    # =========================================================
    # PHASE 2: Project Setup
    # =========================================================
    print("\n📁 Phase 2: Project Setup")

    project = run_test_step(
        "Create project",
        lambda: assert_ok(
            client.post(
                "/api/projects",
                json={
                    "name": "[E2E] Research Spine Canonical Corpus",
                    "description": "Investigating onboarding drop-off for our PM tool.",
                },
            )
        ),
    )
    project_id = project["id"] if project else None

    if project_id:
        run_test_step("Get project", lambda: assert_ok(client.get(f"/api/projects/{project_id}")))
        run_test_step(
            "Set company context",
            lambda: assert_ok(
                client.patch(
                    f"/api/projects/{project_id}",
                    json={"company_context": "Acme SaaS"},
                )
            ),
        )

    # =========================================================
    # PHASE 3: Context Hierarchy
    # =========================================================
    print("\n📜 Phase 3: Context Hierarchy")

    run_test_step(
        "Create company context doc",
        lambda: assert_ok(
            client.post(
                "/api/contexts",
                json={
                    "name": "Company Culture",
                    "level_type": "company",
                    "content": "User-centric.",
                    "priority": 10,
                },
            )
        ),
    )

    # =========================================================
    # PHASE 4: File Upload
    # =========================================================
    print("\n📄 Phase 4: File Upload")

    if project_id:
        for f in canonical_e2e_files():
            if f.is_file():
                run_test_step(
                    f"Upload canonical {f.name}",
                    lambda file=f: upload_file(client, project_id, file),
                )

    # =========================================================
    # PHASE 5: Chat & Skill Execution
    # =========================================================
    print("\n💬 Phase 5: Chat & Skill Execution")

    if project_id:
        run_test_step(
            "Chat — analyze",
            lambda: chat_message(client, project_id, "Analyze transcripts."),
        )
        run_test_step(
            "Direct skill execute",
            lambda: assert_skill_success(
                client.post(
                    "/api/skills/survey-design/execute",
                    json={"project_id": project_id, "user_context": "Design survey"},
                )
            ),
        )

    # =========================================================
    # PHASE 12: Steering
    # =========================================================
    print("\n🎯 Phase 12: Mid-Execution Steering")

    run_test_step(
        "Get steering status",
        lambda: assert_ok(client.get(f"/api/steering/istara-main/status?project_id={project_id}")),
    )

    # =========================================================
    # PHASE 14: Browser Research & Formal Evaluation
    # =========================================================
    print("\n🌐 Phase 14: Browser Research & Formal Evaluation")

    run_test_step(
        "Automated Browser Skill registered",
        lambda: assert_true(
            any(
                s["name"] == "competitive-analysis"
                for s in assert_ok(client.get("/api/skills"))["skills"]
            )
        ),
    )
    run_test_step(
        "Formal Evaluation Skill registered",
        lambda: assert_true(
            any(
                s["name"] == "evaluate-research"
                for s in assert_ok(client.get("/api/skills"))["skills"]
            )
        ),
    )

    # =========================================================
    # PHASE 25: Voice Transcription
    # =========================================================
    print("\n🎙️ Phase 25: Voice Transcription")

    run_test_step(
        "Voice transcription initialization",
        lambda: assert_ok(
            client.post(
                "/api/chat/voice-transcribe",
                json={
                    "project_id": project_id,
                    "dummy": True,
                },
            )
        )
        if assert_true(project_id)
        else None,
    )

    # =========================================================
    # PHASE 26: Pi Migration Count-to-Zero Ratchet
    # =========================================================
    print("\n🧭 Phase 26: Pi Migration Count-to-Zero Ratchet")

    run_test_step("Pi migration count-to-zero ratchet", pi_migration_ratchet)

    # =========================================================
    # RESULTS
    # =========================================================
    elapsed = time.time() - start_time
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print("\n" + "=" * 60)
    print(f"🐾 Results: {passed} passed, {failed} failed, {len(results)} total")
    print(f"⏱️  Time: {elapsed:.1f}s")
    print("=" * 60)

    return 0 if failed == 0 else 1


def assert_ok(response):
    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def assert_skill_success(response):
    payload = assert_ok(response)
    if not isinstance(payload, dict):
        raise Exception("Skill execute returned no JSON payload.")
    if not payload.get("success"):
        errors = payload.get("errors") or []
        summary = payload.get("summary") or ""
        detail = "; ".join(str(error) for error in errors) or summary
        raise Exception(f"Skill execution failed: {detail[:240]}")
    return payload


def assert_true(condition):
    if not condition:
        raise Exception("Assertion failed")
    return True


def upload_file(client, project_id, file_path):
    with open(file_path, "rb") as f:
        resp = client.post(f"/api/files/upload/{project_id}", files={"file": (file_path.name, f)})
    return assert_ok(resp)


def chat_message(client, project_id, message):
    resp = client.post(
        "/api/chat",
        json={"message": message, "project_id": project_id},
        timeout=120.0,
    )
    return assert_ok(resp)


def pi_migration_ratchet():
    """Deterministic count-to-zero ratchet (master plan §4.2); needs no server."""
    tests_dir = Path(__file__).resolve().parent
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))
    from pi_migration.test_count_to_zero import EXPECTED_PRODUCT_SITES, check_count_to_zero

    check_count_to_zero()
    return f"legacy-plane inventory within allowlist; {EXPECTED_PRODUCT_SITES} product sites ratcheted"


if __name__ == "__main__":
    sys.exit(main())
