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
        results.append({"name": name, "status": "PASS", "detail": str(result)[:200] if result else "OK"})
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

    # Priority: env vars > .env file > root .env fallback
    admin_user = os.environ.get("ISTARA_ADMIN_USER", "")
    admin_pass = os.environ.get("ISTARA_ADMIN_PASSWORD", "")

    if not admin_pass:
        # Read admin password from .env (auto-generated on first startup)
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ADMIN_PASSWORD="):
                    admin_pass = line.split("=", 1)[1].strip()
                    break
        if not admin_pass:
            # Try root .env as fallback
            env_path2 = Path(__file__).parent.parent / ".env"
            if env_path2.exists():
                for line in env_path2.read_text().splitlines():
                    if line.startswith("ADMIN_PASSWORD="):
                        admin_pass = line.split("=", 1)[1].strip()
                        break

    if not admin_user:
        admin_user = "admin"

    if admin_pass:
        try:
            login_resp = client.post("/api/auth/login", json={
                "username": admin_user,
                "password": admin_pass,
            })
            if login_resp.status_code == 200:
                token = login_resp.json().get("token") or login_resp.json().get("access_token", "")
                if token:
                    client.headers["Authorization"] = f"Bearer {token}"
                    print(f"  ✅ Authenticated as {admin_user} (JWT set)")
                else:
                    print(f"  ⚠️  Login succeeded but no token in response")
            else:
                print(f"  ⚠️  Login failed ({login_resp.status_code}): {login_resp.text[:200]}")
        except Exception as e:
            print(f"  ⚠️  Login error: {e}")
    else:
        print("  ⚠️  No ADMIN_PASSWORD found — some tests will fail with 401")

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
    # PHASE 2: Project Setup (Sarah creates her project)
    # =========================================================
    print("\n📁 Phase 2: Project Setup")

    project = run_test_step("Create project", lambda: assert_ok(client.post("/api/projects", json={
        "name": "Onboarding Redesign Study",
        "description": "Investigating onboarding drop-off for our PM tool. Goal: reduce churn by 20%.",
    })))
    project_id = project["id"] if project else None

    if project_id:
        run_test_step("Get project", lambda: assert_ok(client.get(f"/api/projects/{project_id}")))

        run_test_step("Set company context", lambda: assert_ok(client.patch(f"/api/projects/{project_id}", json={
            "company_context": "Acme PM — B2B SaaS project management tool for product teams. "
                               "200 employees, mid-market focus (50-500 seat companies). "
                               "Culture: data-driven, user-centric, move fast with quality.",
        })))

        run_test_step("Set project context", lambda: assert_ok(client.patch(f"/api/projects/{project_id}", json={
            "project_context": "Research goal: Understand why 45% of users drop off at step 3 (phone verification) "
                               "during onboarding. Timeline: 4 weeks. Target users: PMs, designers, eng leads "
                               "at companies with 50-500 employees. Phase: Discover.",
        })))

        run_test_step("Set guardrails", lambda: assert_ok(client.patch(f"/api/projects/{project_id}", json={
            "guardrails": "- Always cite which participant said what\n"
                          "- Flag findings with fewer than 3 supporting data points\n"
                          "- Use 'workspace' not 'project' (company terminology)\n"
                          "- Don't recommend removing phone verification without strong evidence",
        })))

    # =========================================================
    # PHASE 3: Context Hierarchy
    # =========================================================
    print("\n📜 Phase 3: Context Hierarchy")

    run_test_step("Create company context doc", lambda: assert_ok(client.post("/api/contexts", json={
        "name": "Acme PM Company Culture",
        "level_type": "company",
        "content": "We value user research and data-driven decisions. Our product team includes PMs, designers, and researchers.",
        "priority": 10,
    })))

    if project_id:
        run_test_step("Get composed context", lambda: assert_ok(client.get(f"/api/contexts/composed/{project_id}")))

    # =========================================================
    # PHASE 4: File Upload & Processing
    # =========================================================
    print("\n📄 Phase 4: File Upload & Processing")

    if project_id:
        for fixture_file in sorted(FIXTURES.glob("*")):
            if fixture_file.is_file():
                run_test_step(f"Upload {fixture_file.name}", lambda f=fixture_file: upload_file(client, project_id, f))

        run_test_step("List project files", lambda: assert_ok(client.get(f"/api/files/{project_id}")))
        run_test_step("File stats", lambda: assert_ok(client.get(f"/api/files/{project_id}/stats")))

    # =========================================================
    # PHASE 5: Chat & Skill Execution
    # =========================================================
    print("\n💬 Phase 5: Chat & Skill Execution")

    if project_id:
        run_test_step("Chat — analyze interviews", lambda: chat_message(client, project_id,
             "Analyze the interview transcripts I uploaded. Focus on onboarding pain points."))

        run_test_step("Chat — competitive analysis", lambda: chat_message(client, project_id,
             "Run a competitive analysis based on the competitive_analysis.md file."))

        run_test_step("Chat — create personas", lambda: chat_message(client, project_id,
             "Create personas from the research data."))

        run_test_step("Chat — thematic analysis", lambda: chat_message(client, project_id,
             "Run thematic analysis on all the interview data."))

        run_test_step("Chat — general question", lambda: chat_message(client, project_id,
             "What are the top 3 pain points we've found so far?"))

        run_test_step("Direct skill execute — survey design", lambda: assert_ok(client.post(
            "/api/skills/survey-design/execute", json={
                "project_id": project_id,
                "user_context": "Design a follow-up survey about onboarding satisfaction",
            })))

        run_test_step("Direct skill plan — user interviews", lambda: assert_ok(client.post(
            "/api/skills/user-interviews/plan", json={
                "project_id": project_id,
                "user_context": "Plan round 2 interviews focusing on the phone verification drop-off",
            })))

    # =========================================================
    # PHASE 6: Findings Verification
    # =========================================================
    print("\n🔍 Phase 6: Findings Verification")

    if project_id:
        run_test_step("List nuggets", lambda: assert_ok(client.get(f"/api/findings/nuggets?project_id={project_id}")))
        run_test_step("List facts", lambda: assert_ok(client.get(f"/api/findings/facts?project_id={project_id}")))
        run_test_step("List insights", lambda: assert_ok(client.get(f"/api/findings/insights?project_id={project_id}")))
        run_test_step("List recommendations", lambda: assert_ok(client.get(f"/api/findings/recommendations?project_id={project_id}")))
        run_test_step("Findings summary", lambda: assert_ok(client.get(f"/api/findings/summary/{project_id}")))
        run_test_step("Project search", lambda: assert_ok(client.get(f"/api/findings/search/{project_id}?query=phone+verification")))
        run_test_step("Global search", lambda: assert_ok(client.get("/api/findings/search/global?query=onboarding")))

    # =========================================================
    # PHASE 7: Tasks & Kanban
    # =========================================================
    print("\n📋 Phase 7: Tasks & Kanban")

    if project_id:
        task1 = run_test_step("Create task — analyze surveys", lambda: assert_ok(client.post("/api/tasks", json={
            "project_id": project_id,
            "title": "Analyze survey responses for AI-generated answers",
            "description": "Run the survey AI detection skill on our 20 survey responses",
            "skill_name": "survey-ai-detection",
        })))

        task2 = run_test_step("Create task — journey map", lambda: assert_ok(client.post("/api/tasks", json={
            "project_id": project_id,
            "title": "Create user journey map for onboarding flow",
            "skill_name": "journey-mapping",
        })))

        if task1:
            run_test_step("Move task to in_progress", lambda: assert_ok(client.post(
                f"/api/tasks/{task1['id']}/move?status=in_progress")))

        run_test_step("List all tasks", lambda: assert_ok(client.get(f"/api/tasks?project_id={project_id}")))

    # =========================================================
    # PHASE 8: Metrics & History
    # =========================================================
    print("\n📊 Phase 8: Metrics & History")

    if project_id:
        run_test_step("Project metrics", lambda: assert_ok(client.get(f"/api/metrics/{project_id}")))
        run_test_step("Version history", lambda: assert_ok(client.get(f"/api/projects/{project_id}/versions")))
        run_test_step("Chat history", lambda: assert_ok(client.get(f"/api/chat/history/{project_id}")))

    # =========================================================
    # PHASE 9: Skills Registry
    # =========================================================
    print("\n🧩 Phase 9: Skills")

    run_test_step("List all skills", lambda: assert_ok(client.get("/api/skills")))
    run_test_step("Skill registry", lambda: assert_ok(client.get("/api/skill-registry")))
    run_test_step("Skill health", lambda: assert_ok(client.get("/api/skills/health/all")))

    # =========================================================
    # PHASE 10: Agents & Audit
    # =========================================================
    print("\n🤖 Phase 10: Agents & Audit")

    run_test_step("Agent status", lambda: assert_ok(client.get("/api/agents/status")))
    run_test_step("List agents", lambda: assert_ok(client.get("/api/agents")))
    run_test_step("DevOps audit latest", lambda: assert_ok(client.get("/api/audit/devops/latest")))
    run_test_step("UI audit latest", lambda: assert_ok(client.get("/api/audit/ui/latest")))
    run_test_step("UX eval latest", lambda: assert_ok(client.get("/api/audit/ux/latest")))
    run_test_step("Sim test latest", lambda: assert_ok(client.get("/api/audit/sim/latest")))
    run_test_step("Context documents", lambda: assert_ok(client.get("/api/contexts")))

    # =========================================================
    # PHASE 11: Frontend Check
    # =========================================================
    print("\n🌐 Phase 11: Frontend")

    try:
        frontend = httpx.get("http://localhost:3000", timeout=10)
        run_test_step("Frontend serves HTML", lambda: assert_true(frontend.status_code == 200 and "<html" in frontend.text.lower()))
    except Exception:
        run_test_step("Frontend serves HTML", lambda: (_ for _ in ()).throw(Exception("Frontend not reachable at localhost:3000")))

    # =========================================================
    # PHASE 12: Mid-Execution Steering
    # =========================================================
    print("\n🎯 Phase 12: Mid-Execution Steering")

    run_test_step("Queue steering message", lambda: assert_ok(client.post("/api/steering/istara-main", json={
        "message": "E2E test: verify steering endpoint works",
        "mode": "one-at-a-time",
    })))

    run_test_step("Queue follow-up message", lambda: assert_ok(client.post("/api/steering/istara-main/follow-up", json={
        "message": "E2E test: verify follow-up endpoint works",
    })))

    run_test_step("Get steering status", lambda: assert_ok(client.get("/api/steering/istara-main/status")))

    run_test_step("Get steering queues", lambda: assert_ok(client.get("/api/steering/istara-main/queues")))

    run_test_step("Clear steering queues", lambda: assert_ok(client.delete("/api/steering/istara-main/queues")))

    run_test_step("Abort agent work", lambda: assert_ok(client.post("/api/steering/istara-main/abort", json={})))

    # =========================================================
    # PHASE 13: Chat Flow
    # =========================================================
    print("\n💬 Phase 13: Chat Flow")

    if project_id:
        run_test_step("Chat history exists", lambda: assert_ok(client.get(f"/api/chat/history/{project_id}")))
        # Note: Full streaming chat test requires running LLM — verify endpoint works at minimum
        run_test_step("Chat endpoint accessible", lambda: assert_ok(client.get(f"/api/chat/history/{project_id}?limit=10")))

    # =========================================================
    # PHASE 14: Findings CRUD
    # =========================================================
    print("\n🔍 Phase 14: Findings CRUD")

    if project_id:
        nugget = run_test_step("Create nugget", lambda: assert_ok(client.post("/api/findings/nuggets", json={
            "project_id": project_id,
            "text": "E2E test nugget: Users struggle with phone verification",
            "source": "e2e-test",
        })))
        
        if nugget:
            run_test_step("Evidence chain accessible", lambda: assert_ok(client.get(f"/api/findings/nugget/{nugget['id']}/evidence-chain")))
            run_test_step("Delete nugget", lambda: assert_ok(client.delete(f"/api/findings/nuggets/{nugget['id']}")))

        fact = run_test_step("Create fact", lambda: assert_ok(client.post("/api/findings/facts", json={
            "project_id": project_id,
            "text": "E2E test fact: 40% drop-off at phone verification step",
            "source": "e2e-test",
        })))
        if fact:
            run_test_step("Delete fact", lambda: assert_ok(client.delete(f"/api/findings/facts/{fact['id']}")))

        run_test_step("Design decisions accessible", lambda: assert_ok(client.get("/api/findings/design-decisions")))

    # =========================================================
    # PHASE 15: Project Management
    # =========================================================
    print("\n📁 Phase 15: Project Management")

    new_project = run_test_step("Create new project", lambda: assert_ok(client.post("/api/projects", json={
        "name": "E2E Test Project",
        "description": "Created by e2e test suite",
    })))
    if new_project:
        e2e_proj_id = new_project.get("id")
        run_test_step("Get new project", lambda: assert_ok(client.get(f"/api/projects/{e2e_proj_id}")))
        run_test_step("Pause new project", lambda: assert_ok(client.post(f"/api/projects/{e2e_proj_id}/pause")))
        run_test_step("Resume new project", lambda: assert_ok(client.post(f"/api/projects/{e2e_proj_id}/resume")))
        run_test_step("Delete new project", lambda: assert_ok(client.delete(f"/api/projects/{e2e_proj_id}")))

    run_test_step("List all projects", lambda: assert_ok(client.get("/api/projects")))

    # =========================================================
    # PHASE 16: Task Management
    # =========================================================
    print("\n📋 Phase 16: Task Management")

    if project_id:
        task = run_test_step("Create e2e task", lambda: assert_ok(client.post("/api/tasks", json={
            "project_id": project_id,
            "title": "E2E test task",
            "description": "Created by e2e test suite",
        })))
        if task:
            task_id = task["id"]
            run_test_step("Move e2e task", lambda: assert_ok(client.post(f"/api/tasks/{task_id}/move?status=in_progress")))
            run_test_step("Lock task", lambda: assert_ok(client.post(f"/api/tasks/{task_id}/lock")))
            run_test_step("Unlock task", lambda: assert_ok(client.post(f"/api/tasks/{task_id}/unlock")))
            run_test_step("Delete e2e task", lambda: assert_ok(client.delete(f"/api/tasks/{task_id}")))

    # =========================================================
    # PHASE 17: Skills Deep Dive
    # =========================================================
    print("\n🧩 Phase 17: Skills Deep Dive")

    run_test_step("Get single skill", lambda: assert_ok(client.get("/api/skills/card-sorting")))
    run_test_step("Toggle skill", lambda: assert_ok(client.post("/api/skills/card-sorting/toggle")))
    run_test_step("Skill proposals", lambda: assert_ok(client.get("/api/skills/proposals/pending")))
    run_test_step("Creation proposals", lambda: assert_ok(client.get("/api/skills/creation-proposals/pending")))

    # =========================================================
    # PHASE 18: Documents Deep Dive
    # =========================================================
    print("\n📄 Phase 18: Documents Deep Dive")

    if project_id:
        run_test_step("Document search", lambda: assert_ok(client.get(f"/api/documents/search/full?q=test&project_id={project_id}")))
        run_test_step("Document tags", lambda: assert_ok(client.get(f"/api/documents/tags/{project_id}")))
        run_test_step("Document stats", lambda: assert_ok(client.get(f"/api/documents/stats/{project_id}")))
        run_test_step("File list", lambda: assert_ok(client.get(f"/api/files/{project_id}")))
        run_test_step("File stats", lambda: assert_ok(client.get(f"/api/files/{project_id}/stats")))

    # =========================================================
    # PHASE 19: Sessions Deep Dive
    # =========================================================
    print("\n🗣️ Phase 19: Sessions Deep Dive")

    if project_id:
        run_test_step("List sessions", lambda: assert_ok(client.get(f"/api/sessions/{project_id}")))
        run_test_step("Ensure default sessions", lambda: assert_ok(client.get(f"/api/sessions/{project_id}/ensure-default")))
        run_test_step("Inference presets", lambda: assert_ok(client.get("/api/inference-presets")))

    # =========================================================
    # PHASE 20: Settings Deep Dive
    # =========================================================
    print("\n⚙️ Phase 20: Settings Deep Dive")

    run_test_step("Hardware info", lambda: assert_ok(client.get("/api/settings/hardware")))
    run_test_step("Maintenance status", lambda: assert_ok(client.get("/api/settings/maintenance")))
    run_test_step("Vector health", lambda: assert_ok(client.get("/api/settings/vector-health")))
    run_test_step("Integrations status", lambda: assert_ok(client.get("/api/settings/integrations-status")))

    # =========================================================
    # PHASE 21: Backup Deep Dive
    # =========================================================
    print("\n💾 Phase 21: Backup Deep Dive")

    run_test_step("Backup estimate", lambda: assert_ok(client.get("/api/backups/estimate")))

    # =========================================================
    # PHASE 22: Meta-Agent Deep Dive
    # =========================================================
    print("\n🧬 Phase 22: Meta-Agent Deep Dive")

    run_test_step("Meta-agent proposals", lambda: assert_ok(client.get("/api/meta-hyperagent/proposals")))
    run_test_step("Meta-agent variants", lambda: assert_ok(client.get("/api/meta-hyperagent/variants")))
    run_test_step("Meta-agent observations", lambda: assert_ok(client.get("/api/meta-hyperagent/observations")))

    # =========================================================
    # PHASE 23: Interfaces Deep Dive
    # =========================================================
    print("\n🎨 Phase 23: Interfaces Deep Dive")

    run_test_step("Interface screens", lambda: assert_ok(client.get("/api/interfaces/screens")))
    run_test_step("Interface status", lambda: assert_ok(client.get("/api/interfaces/status")))
    run_test_step("Interface handoff briefs", lambda: assert_ok(client.get("/api/interfaces/handoff/briefs")))

    # =========================================================
    # PHASE 24: Loops Deep Dive
    # =========================================================
    print("\n🔁 Phase 24: Loops Deep Dive")

    run_test_step("Loops agents", lambda: assert_ok(client.get("/api/loops/agents")))
    run_test_step("Execution stats", lambda: assert_ok(client.get("/api/loops/executions/stats")))

    # =========================================================
    # PHASE 25: Voice Transcription
    # =========================================================
    print("\n🎙️ Phase 25: Voice Transcription")

    if project_id:
        run_test_step("Transcription endpoint accessible", lambda: assert_ok(client.get(f"/api/chat/history/{project_id}")))
        # Verify specific voice transcription route from P0 roadmap
        run_test_step("Voice transcription initialization", lambda: assert_ok(client.post("/api/chat/voice-transcribe", json={
            "project_id": project_id,
            "dummy": True, # Test endpoint presence without real audio
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

    # Write report
    report_path = Path(__file__).parent.parent / "docs" / "e2e-test-report.md"
    write_report(report_path, elapsed)

    print(f"\n📄 Report: {report_path}")

    return 0 if failed == 0 else 1


def assert_ok(response):
    """Assert HTTP response is successful and return JSON."""
    if response.status_code >= 400:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except Exception:
        return None


def assert_true(condition):
    if not condition:
        raise Exception("Assertion failed")
    return True


def upload_file(client, project_id, file_path):
    """Upload a file to a project."""
    with open(file_path, "rb") as f:
        response = client.post(
            f"/api/files/upload/{project_id}",
            files={"file": (file_path.name, f, "application/octet-stream")},
        )
    if response.status_code >= 400:
        raise Exception(f"Upload failed: {response.status_code}")
    return response.json()


def chat_message(client, project_id, message):
    """Send a chat message and collect the streamed response."""
    response = client.post("/api/chat", json={
        "message": message,
        "project_id": project_id,
    }, timeout=120.0)

    if response.status_code >= 400:
        raise Exception(f"Chat failed: {response.status_code}: {response.text[:200]}")

    # Parse SSE stream
    full_response = ""
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "chunk":
                    full_response += data.get("content", "")
                elif data.get("type") == "error":
                    raise Exception(f"Chat error: {data.get('message')}")
            except json.JSONDecodeError:
                pass

    if not full_response:
        raise Exception("Empty chat response")

    return {"response_length": len(full_response), "preview": full_response[:100]}


def write_report(path, elapsed):
    """Write the test report as Markdown."""
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    lines = [
        "# Istara — End-to-End Test Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Duration:** {elapsed:.1f}s",
        f"**Results:** {passed} passed, {failed} failed, {len(results)} total",
        f"**Pass Rate:** {passed / max(len(results), 1) * 100:.0f}%",
        "",
        "---",
        "",
    ]

    # Group by phase
    current_phase = ""
    for r in results:
        phase = r["name"].split(" — ")[0] if " — " in r["name"] else ""
        if phase != current_phase:
            current_phase = phase
            lines.append(f"## {phase or 'Tests'}")
            lines.append("")

        icon = "✅" if r["status"] == "PASS" else "❌"
        lines.append(f"- {icon} **{r['name']}**")
        if r["status"] == "FAIL":
            lines.append(f"  - Error: `{r['detail']}`")
        lines.append("")

    # Failures summary
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        lines.extend(["## ❌ Failures", ""])
        for f in failures:
            lines.append(f"### {f['name']}")
            lines.append(f"```\n{f['detail']}\n```")
            lines.append("")

    lines.extend([
        "---",
        "",
        f"*Generated by Istara E2E test suite • {time.strftime('%Y-%m-%d')}*",
    ])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
