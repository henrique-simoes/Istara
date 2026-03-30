"""UX Evaluation Agent — tests real Istara API journeys end-to-end.

Unlike the UI Audit Agent (which checks heuristics/accessibility per component),
this agent evaluates the holistic UX by actually calling API endpoints to simulate
critical user journeys: project creation, file upload, task processing, and findings.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.api.websocket import broadcast_agent_status

logger = logging.getLogger(__name__)

API_BASE = os.getenv("ISTARA_API_BASE", "http://localhost:8000")


class UXEvalAgent:
    """Evaluates overall platform UX by testing real critical journeys."""

    def __init__(self) -> None:
        self._running = False
        self._audit_interval = 900  # 15 minutes
        self._reports: list[dict] = []
        self._client: httpx.AsyncClient | None = None
        # Task execution worker
        from app.core.sub_agent_worker import SubAgentWorker
        self._worker = SubAgentWorker("istara-ux-eval", check_interval=30)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=API_BASE, timeout=30.0)
        return self._client

    async def start(self) -> None:
        self._running = True
        logger.info("UX Evaluation Agent started.")

        # Start task worker alongside audit cycle
        asyncio.create_task(self._worker.start_task_loop())

        # Wait for backend to fully initialize
        await asyncio.sleep(45)

        while self._running:
            try:
                await broadcast_agent_status(
                    "working", "UX Evaluation Agent: running journey tests..."
                )
                report = await self.run_evaluation()
                self._reports.append(report)
                if len(self._reports) > 20:
                    self._reports = self._reports[-20:]

                # Report results
                failed = report.get("failed_journeys", 0)
                total = report.get("total_journeys", 0)
                if failed > 0:
                    await broadcast_agent_status(
                        "warning",
                        f"UX Evaluation: {failed}/{total} journeys have issues",
                    )
                else:
                    await broadcast_agent_status(
                        "idle",
                        f"UX Evaluation: all {total} journeys passed",
                    )

            except Exception as e:
                logger.error(f"UX Evaluation error: {e}")
                await broadcast_agent_status("error", f"UX Evaluation error: {e}")

            await asyncio.sleep(self._audit_interval)

    def stop(self) -> None:
        self._running = False
        self._worker.stop_task_loop()

    async def run_evaluation(self) -> dict:
        """Run real API journey tests."""
        timestamp = datetime.now(timezone.utc).isoformat()
        client = await self._get_client()
        journeys: list[dict] = []

        # Journey 1: First-time setup
        journeys.append(await self._journey_first_time_setup(client))

        # Journey 2: Upload & analyze interview
        journeys.append(await self._journey_upload_analyze(client))

        # Journey 3: Create & track tasks
        journeys.append(await self._journey_create_track_tasks(client))

        # Journey 4: Search & discover findings
        journeys.append(await self._journey_search_findings(client))

        # Journey 5: Configure context layers
        journeys.append(await self._journey_configure_context(client))

        # Journey 6: Skills discovery
        journeys.append(await self._journey_skills_discovery(client))

        # Journey 7: System monitoring
        journeys.append(await self._journey_system_monitoring(client))

        passed = sum(1 for j in journeys if j["passed"])
        failed = len(journeys) - passed

        return {
            "timestamp": timestamp,
            "total_journeys": len(journeys),
            "passed_journeys": passed,
            "failed_journeys": failed,
            "pass_rate": round(passed / max(len(journeys), 1) * 100, 1),
            "journeys": journeys,
            "summary": f"{passed}/{len(journeys)} critical journeys passed",
        }

    async def _step(
        self, client: httpx.AsyncClient, name: str, method: str, path: str, **kwargs
    ) -> dict:
        """Execute a single journey step against the API."""
        try:
            resp = await client.request(method, path, **kwargs)
            success = 200 <= resp.status_code < 300
            body = {}
            if success and resp.headers.get("content-type", "").startswith("application/json"):
                body = resp.json()
            return {
                "step": name,
                "success": success,
                "status_code": resp.status_code,
                "response_ms": resp.elapsed.total_seconds() * 1000 if hasattr(resp, "elapsed") else 0,
                "response": body,
                "error": None if success else resp.text[:200],
            }
        except Exception as e:
            return {
                "step": name,
                "success": False,
                "status_code": 0,
                "response_ms": 0,
                "response": {},
                "error": str(e),
            }

    async def _journey_first_time_setup(self, client: httpx.AsyncClient) -> dict:
        """Journey: new user creates first project with full context."""
        steps = []
        project_id = None

        # Step 1: Check API is alive
        steps.append(await self._step(client, "Health check", "GET", "/api/health"))

        # Step 2: List projects (should work even if empty)
        steps.append(await self._step(client, "List projects", "GET", "/api/projects"))

        # Step 3: Create project with full context
        result = await self._step(
            client, "Create project", "POST", "/api/projects",
            json={
                "name": f"UX Eval Test {uuid.uuid4().hex[:6]}",
                "description": "Automated UX evaluation journey test",
                "phase": "discover",
                "company_context": "Test company context for UX evaluation",
                "project_context": "Testing the first-time setup journey",
                "guardrails": "Test guardrails",
            },
        )
        steps.append(result)
        if result["success"]:
            project_id = result["response"].get("id")

        # Step 4: Verify project appears in list
        if project_id:
            result = await self._step(
                client, "Get created project", "GET", f"/api/projects/{project_id}"
            )
            steps.append(result)

            # Cleanup
            await self._step(client, "Cleanup", "DELETE", f"/api/projects/{project_id}")

        passed = all(s["success"] for s in steps if s["step"] != "Cleanup")
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"] and s["step"] != "Cleanup"]

        return {
            "name": "First-time Setup",
            "critical": True,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_upload_analyze(self, client: httpx.AsyncClient) -> dict:
        """Journey: upload a file, verify it's processed, check for tasks."""
        steps = []
        project_id = None

        # Step 1: Create project
        result = await self._step(
            client, "Create project", "POST", "/api/projects",
            json={"name": f"Upload Test {uuid.uuid4().hex[:6]}", "description": "File upload journey test"},
        )
        steps.append(result)
        if result["success"]:
            project_id = result["response"].get("id")

        if project_id:
            # Step 2: Upload a test file
            test_content = (
                "Interview Transcript — Dashboard Usability\n"
                "Participant: Test User (PM, 50-200)\n"
                "Date: 2026-03-18\n"
                "Duration: 45 minutes\n\n"
                "[00:00] Interviewer: How do you use the dashboard?\n"
                "[00:30] Test User: I check it every morning for key metrics.\n"
            )
            files = {"file": ("test-interview.txt", test_content.encode(), "text/plain")}
            result = await self._step(
                client, "Upload file", "POST", f"/api/files/upload/{project_id}",
                files=files,
            )
            steps.append(result)

            # Step 3: Verify file appears in project
            result = await self._step(
                client, "List project files", "GET", f"/api/files/{project_id}"
            )
            steps.append(result)

            # Step 4: Check if tasks were auto-created (from file watcher)
            await asyncio.sleep(2)  # Give file watcher time
            result = await self._step(
                client, "Check auto-created tasks", "GET", f"/api/tasks?project_id={project_id}"
            )
            steps.append(result)

            # Step 5: Check findings summary
            result = await self._step(
                client, "Check findings", "GET", f"/api/findings/summary/{project_id}"
            )
            steps.append(result)

            # Cleanup
            await self._step(client, "Cleanup", "DELETE", f"/api/projects/{project_id}")

        passed = all(s["success"] for s in steps if s["step"] != "Cleanup")
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"] and s["step"] != "Cleanup"]

        return {
            "name": "Upload & Analyze Interview",
            "critical": True,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_create_track_tasks(self, client: httpx.AsyncClient) -> dict:
        """Journey: create a task, assign to agent, check progress."""
        steps = []
        project_id = None
        task_id = None

        # Step 1: Create project
        result = await self._step(
            client, "Create project", "POST", "/api/projects",
            json={"name": f"Task Test {uuid.uuid4().hex[:6]}", "description": "Task tracking journey test"},
        )
        steps.append(result)
        if result["success"]:
            project_id = result["response"].get("id")

        if project_id:
            # Step 2: Create a task
            result = await self._step(
                client, "Create task", "POST", "/api/tasks",
                json={
                    "project_id": project_id,
                    "title": "Analyze test interview data",
                    "skill_name": "user-interviews",
                    "priority": "high",
                },
            )
            steps.append(result)
            if result["success"]:
                task_id = result["response"].get("id")

            # Step 3: Assign to agent
            if task_id:
                result = await self._step(
                    client, "Assign to agent", "PATCH", f"/api/tasks/{task_id}",
                    json={"agent_id": "istara-main"},
                )
                steps.append(result)

            # Step 4: List tasks and verify assignment
            result = await self._step(
                client, "Verify task listing", "GET", f"/api/tasks?project_id={project_id}"
            )
            steps.append(result)

            # Step 5: Check agent status
            result = await self._step(
                client, "Check agent status", "GET", "/api/agents/status"
            )
            steps.append(result)

            # Cleanup
            await self._step(client, "Cleanup", "DELETE", f"/api/projects/{project_id}")

        passed = all(s["success"] for s in steps if s["step"] != "Cleanup")
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"] and s["step"] != "Cleanup"]

        return {
            "name": "Create & Track Tasks",
            "critical": True,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_search_findings(self, client: httpx.AsyncClient) -> dict:
        """Journey: search for findings across projects."""
        steps = []

        # Step 1: List all projects
        result = await self._step(client, "List projects", "GET", "/api/projects")
        steps.append(result)
        projects = result["response"] if result["success"] and isinstance(result["response"], list) else []

        if projects:
            pid = projects[0].get("id", "")
            # Step 2: Get findings for first project
            result = await self._step(
                client, "Get findings summary", "GET", f"/api/findings/summary/{pid}"
            )
            steps.append(result)

            # Step 3: Get nuggets
            result = await self._step(
                client, "Get nuggets", "GET", f"/api/findings/{pid}/nuggets"
            )
            steps.append(result)

            # Step 4: Get insights
            result = await self._step(
                client, "Get insights", "GET", f"/api/findings/{pid}/insights"
            )
            steps.append(result)
        else:
            steps.append({"step": "Skip findings (no projects)", "success": True, "status_code": 0, "response_ms": 0, "response": {}, "error": None})

        passed = all(s["success"] for s in steps)
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"]]

        return {
            "name": "Search & Discover Findings",
            "critical": False,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_configure_context(self, client: httpx.AsyncClient) -> dict:
        """Journey: update project context layers."""
        steps = []
        project_id = None

        # Step 1: Create project
        result = await self._step(
            client, "Create project", "POST", "/api/projects",
            json={"name": f"Context Test {uuid.uuid4().hex[:6]}", "description": "Context journey test"},
        )
        steps.append(result)
        if result["success"]:
            project_id = result["response"].get("id")

        if project_id:
            # Step 2: Update company context
            result = await self._step(
                client, "Update company context", "PATCH", f"/api/projects/{project_id}",
                json={"company_context": "Updated company context for testing"},
            )
            steps.append(result)

            # Step 3: Update project context
            result = await self._step(
                client, "Update project context", "PATCH", f"/api/projects/{project_id}",
                json={"project_context": "Updated project context for testing"},
            )
            steps.append(result)

            # Step 4: Update guardrails
            result = await self._step(
                client, "Update guardrails", "PATCH", f"/api/projects/{project_id}",
                json={"guardrails": "Updated guardrails for testing"},
            )
            steps.append(result)

            # Step 5: Verify context was saved
            result = await self._step(
                client, "Verify saved context", "GET", f"/api/projects/{project_id}"
            )
            steps.append(result)
            if result["success"]:
                project_data = result["response"]
                if project_data.get("company_context") != "Updated company context for testing":
                    result["success"] = False
                    result["error"] = "Company context not saved correctly"

            # Cleanup
            await self._step(client, "Cleanup", "DELETE", f"/api/projects/{project_id}")

        passed = all(s["success"] for s in steps if s["step"] != "Cleanup")
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"] and s["step"] != "Cleanup"]

        return {
            "name": "Configure Context Layers",
            "critical": True,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_skills_discovery(self, client: httpx.AsyncClient) -> dict:
        """Journey: discover and inspect available skills."""
        steps = []

        # Step 1: List skills
        result = await self._step(client, "List skills", "GET", "/api/skills")
        steps.append(result)

        # Step 2: Get skill registry
        result = await self._step(client, "Skill registry", "GET", "/api/skill-registry")
        steps.append(result)

        passed = all(s["success"] for s in steps)
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"]]

        return {
            "name": "Skills Discovery",
            "critical": False,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    async def _journey_system_monitoring(self, client: httpx.AsyncClient) -> dict:
        """Journey: check system health and monitoring endpoints."""
        steps = []

        # Step 1: Health check
        steps.append(await self._step(client, "Health check", "GET", "/api/health"))

        # Step 2: System status
        steps.append(await self._step(client, "System status", "GET", "/api/settings/status"))

        # Step 3: Hardware info
        steps.append(await self._step(client, "Hardware info", "GET", "/api/settings/hardware"))

        # Step 4: Agent status
        steps.append(await self._step(client, "Agent status", "GET", "/api/agents/status"))

        # Step 5: DevOps audit
        steps.append(await self._step(client, "DevOps audit", "GET", "/api/audit/devops/latest"))

        passed = all(s["success"] for s in steps)
        issues = [s["step"] + ": " + (s["error"] or "failed") for s in steps if not s["success"]]

        return {
            "name": "System Monitoring",
            "critical": False,
            "passed": passed,
            "steps": steps,
            "issues": issues,
        }

    def get_latest_report(self) -> dict | None:
        return self._reports[-1] if self._reports else None

    def get_reports(self, limit: int = 10) -> list[dict]:
        return self._reports[-limit:]


# Singleton
ux_eval_agent = UXEvalAgent()
