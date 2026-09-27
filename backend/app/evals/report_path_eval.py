"""R0/R1: from uploaded interviews to an exported report, through the product's own path.

Professional-readiness review (2026-09-26), DEC-5. Every step is a product route or the agent's own
task executor, in the order a researcher meets them:

  1. upload interview transcripts            POST /api/files/upload/{project}
  2. create a Kanban task on those documents POST /api/tasks (skill user-interviews)
  3. run it                                  AgentOrchestrator._execute_task, in-process (the
                                             agent loop stays paused so nothing else runs)
  4. review every pending code application   PATCH /api/code-applications/{id}/review
  5. approve the task                        POST /api/tasks/{id}/review/approve
  6. send it to Reports                      POST /api/tasks/{id}/reports
  7. export it (md, docx, csv)               GET /api/reports/{project}/{report}/export

Step 4 is a scripted reviewer (synthetic data): it approves each code, as a researcher accepting the
coders' work would. R1 is the share of the report's findings whose evidence trail reaches an exact
source span. Run inside the backend container:

    python -m app.evals.report_path_eval --files /app/data/eval/r0/*.md \\
        --endpoint pi-deepseek-flash --out /app/data/eval/r0.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

BASE = "http://127.0.0.1:8000"


async def _execute(task_id: str, project_id: str) -> None:
    from app.core.agent import agent
    from app.models.database import async_session
    from app.models.project import Project
    from app.models.task import Task

    async with async_session() as db:
        task = await db.get(Task, task_id)
        project = await db.get(Project, project_id)
        await agent._execute_task(db, task, project)


async def _wait_ready(doc_ids: list[str], timeout_s: float = 900) -> dict:
    """Upload processing runs in the background; wait until every document is ready."""
    from app.models.database import async_session
    from app.models.document import Document

    deadline = time.monotonic() + timeout_s
    statuses: dict = {}
    while time.monotonic() < deadline:
        async with async_session() as db:
            statuses = {d: str((await db.get(Document, d)).status) for d in doc_ids}
        if all(s.lower().endswith("ready") for s in statuses.values()):
            break
        await asyncio.sleep(5)
    return statuses


async def _trace(report_id: str) -> dict:
    from app.models.database import async_session
    from app.models.project_report import ProjectReport
    from app.services.report_export import trace_report, traceability

    async with async_session() as db:
        report = await db.get(ProjectReport, report_id)
        findings = await trace_report(db, report)
    by_kind: dict[str, int] = {}
    for finding in findings:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
    return {"r1": traceability(findings), "findings_by_kind": by_kind}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    import httpx

    import app.core.agentic  # noqa: F401  (import-order guard)
    from app.models.database import register_models

    register_models()
    steps: dict = {}
    started = time.monotonic()
    with httpx.Client(base_url=BASE, timeout=600) as client:
        client.post("/api/settings/pi-default", json={"endpoint_id": args.endpoint})
        project = client.post("/api/projects", json={"name": "R0 report path (Harbor)"}).json()
        pid = project["id"]
        uploaded = []
        for path in args.files:
            with open(path, "rb") as fh:
                response = client.post(
                    f"/api/files/upload/{pid}",
                    files={"file": (Path(path).name, fh, "text/markdown")},
                )
            uploaded.append(response.json())
        doc_ids = [u.get("doc_id") for u in uploaded if u.get("doc_id")]
        steps["upload"] = {
            "files": len(uploaded),
            "document_ids": doc_ids,
            "statuses": asyncio.run(_wait_ready(doc_ids)),
        }
        auto_tasks = [t["id"] for t in client.get("/api/tasks", params={"project_id": pid}).json()]
        task = client.post(
            "/api/tasks",
            json={
                "project_id": pid,
                "title": "Analyse the Harbor interviews",
                "description": "Find the themes across these interviews.",
                "skill_name": "user-interviews",
                "input_document_ids": doc_ids,
            },
        ).json()
        steps["task"] = {"id": task["id"], "auto_created_on_upload": len(auto_tasks)}

        asyncio.run(_execute(task["id"], pid))
        after_run = client.get(f"/api/tasks/{task['id']}", params={"project_id": pid}).json()
        runs = client.get(f"/api/research-validity/{pid}/coding-runs").json()
        steps["run"] = {
            "status": after_run.get("status"),
            "review_state": after_run.get("review_state"),
            "coding_runs": [
                {
                    k: r.get(k)
                    for k in ("status", "kappa", "alpha", "promotion_status", "rater_count")
                }
                for r in (runs if isinstance(runs, list) else runs.get("coding_runs", []))
            ],
        }

        pending = client.get(f"/api/code-applications/{pid}/pending").json()
        reviewed = 0
        for application in pending:
            response = client.patch(
                f"/api/code-applications/{application['id']}/review",
                params={"project_id": pid},
                json={
                    "review_status": "approved",
                    "rationale": "R0 scripted reviewer: code matches the quoted span.",
                },
            )
            reviewed += 1 if response.status_code == 200 else 0
        steps["review_codes"] = {"pending": len(pending), "approved": reviewed}

        approve = client.post(
            f"/api/tasks/{task['id']}/review/approve",
            params={"project_id": pid},
            json={"note": "R0: reviewed the coded evidence."},
        )
        steps["approve_task"] = {"status": approve.status_code, "detail": approve.json()}
        report = client.post(f"/api/tasks/{task['id']}/reports", params={"project_id": pid})
        steps["report"] = {"status": report.status_code}
        report_body = report.json()
        report_id = (report_body.get("report") or {}).get("id")
        exports = {}
        if report_id:
            for fmt in ("md", "docx", "csv"):
                exported = client.get(
                    f"/api/reports/{pid}/{report_id}/export", params={"format": fmt}
                )
                exports[fmt] = {"status": exported.status_code, "bytes": len(exported.content)}
                if fmt == "md" and exported.status_code == 200:
                    steps["report_markdown_head"] = exported.text[:1500]
            steps["report"].update(asyncio.run(_trace(report_id)))
        else:
            steps["report"]["detail"] = report_body
        steps["export"] = exports

    result = {
        "measure": "R0/R1 report path end to end (professional-readiness review, DEC-5)",
        "endpoint": args.endpoint,
        "project_id": pid,
        "elapsed_s": round(time.monotonic() - started, 1),
        "report_exists": bool(report_id),
        **steps,
    }
    text = json.dumps(result, indent=2, default=str)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
