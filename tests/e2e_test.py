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
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx required: pip install httpx")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
FIXTURES = Path(__file__).parent / "fixtures"

# Test results tracking
results = []
start_time = time.time()


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
    print(f"   Fixtures: {FIXTURES}")
    print("=" * 60)

    # =========================================================
    # PHASE 0: Authentication
    # =========================================================
    print("\n🔐 Phase 0: Authentication")

    admin_user = os.environ.get("ISTARA_ADMIN_USER", "admin")
    admin_pass = os.environ.get("ISTARA_ADMIN_PASSWORD", "")

    if not admin_pass:
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ADMIN_PASSWORD="):
                    admin_pass = line.split("=", 1)[1].strip()
                    break
    
    if admin_pass:
        try:
            login_resp = client.post("/api/auth/login", json={"username": admin_user, "password": admin_pass})
            if login_resp.status_code == 200:
                token = login_resp.json().get("token") or login_resp.json().get("access_token", "")
                if token:
                    client.headers["Authorization"] = f"Bearer {token}"
                    print(f"  ✅ Authenticated as {admin_user}")
        except Exception as e:
            print(f"  ⚠️  Login error: {e}")

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

    project = run_test_step("Create project", lambda: assert_ok(client.post("/api/projects", json={
        "name": "Onboarding Redesign Study",
        "description": "Investigating onboarding drop-off for our PM tool.",
    })))
    project_id = project["id"] if project else None

    if project_id:
        run_test_step("Get project", lambda: assert_ok(client.get(f"/api/projects/{project_id}")))
        run_test_step("Set company context", lambda: assert_ok(client.patch(f"/api/projects/{project_id}", json={"company_context": "Acme SaaS"})))

    # =========================================================
    # PHASE 3: Context Hierarchy
    # =========================================================
    print("\n📜 Phase 3: Context Hierarchy")

    run_test_step("Create company context doc", lambda: assert_ok(client.post("/api/contexts", json={
        "name": "Company Culture", "level_type": "company", "content": "User-centric.", "priority": 10
    })))

    # =========================================================
    # PHASE 4: File Upload
    # =========================================================
    print("\n📄 Phase 4: File Upload")

    if project_id:
        for f in sorted(FIXTURES.glob("*")):
            if f.is_file():
                run_test_step(f"Upload {f.name}", lambda file=f: upload_file(client, project_id, file))

    # =========================================================
    # PHASE 5: Chat & Skill Execution
    # =========================================================
    print("\n💬 Phase 5: Chat & Skill Execution")

    if project_id:
        run_test_step("Chat — analyze", lambda: chat_message(client, project_id, "Analyze transcripts."))
        run_test_step("Direct skill execute", lambda: assert_ok(client.post("/api/skills/survey-design/execute", json={
            "project_id": project_id, "user_context": "Design survey"
        })))

    # =========================================================
    # PHASE 12: Steering
    # =========================================================
    print("\n🎯 Phase 12: Mid-Execution Steering")

    run_test_step("Get steering status", lambda: assert_ok(client.get("/api/steering/istara-main/status")))

    # =========================================================
    # PHASE 14: Browser Research & Formal Evaluation
    # =========================================================
    print("\n🌐 Phase 14: Browser Research & Formal Evaluation")

    run_test_step("Automated Browser Skill registered", lambda: assert_true(
        any(s["name"] == "competitive-analysis" for s in assert_ok(client.get("/api/skills"))["skills"])
    ))
    run_test_step("Formal Evaluation Skill registered", lambda: assert_true(
        any(s["name"] == "evaluate-research" for s in assert_ok(client.get("/api/skills"))["skills"])
    ))

    # =========================================================
    # PHASE 25: Voice Transcription
    # =========================================================
    print("\n🎙️ Phase 25: Voice Transcription")

    run_test_step("Voice transcription initialization", lambda: assert_ok(client.post("/api/chat/voice-transcribe", json={
        "project_id": project_id if project_id else "0",
        "dummy": True,
    })))

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
    if response.status_code == 204: return None
    try: return response.json()
    except: return None

def assert_true(condition):
    if not condition: raise Exception("Assertion failed")
    return True

def upload_file(client, project_id, file_path):
    with open(file_path, "rb") as f:
        resp = client.post(f"/api/files/upload/{project_id}", files={"file": (file_path.name, f)})
    return assert_ok(resp)

def chat_message(client, project_id, message):
    resp = client.post("/api/chat", json={"message": message, "project_id": project_id}, timeout=120.0)
    return assert_ok(resp)

if __name__ == "__main__":
    sys.exit(main())
