"""Istara MCP Server -- exposes research capabilities to external agents.

SECURITY WARNING: This server allows external AI agents to access local
research data.  All tools are gated by MCPAccessPolicy with granular
per-tool permissions.  OFF by default.  Enable via settings.

The server is built on top of ``fastmcp`` (if installed).  When the
library is unavailable the module still imports cleanly -- callers can
check ``MCP_AVAILABLE`` before attempting to start the server.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional import of fastmcp
# ---------------------------------------------------------------------------

try:
    from fastmcp import FastMCP  # type: ignore[import-untyped]
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.info("fastmcp not installed -- MCP server unavailable")


# ---------------------------------------------------------------------------
# Helper: run a security-gated tool
# ---------------------------------------------------------------------------


async def _gated_call(tool_name: str, arguments: dict | None, handler):
    """Execute *handler* only if the access policy permits *tool_name*.

    Logs the request to the audit trail regardless of outcome.
    """
    from app.models.database import async_session
    from app.services.mcp_security import audit_request, check_access

    args = arguments or {}
    start = time.monotonic()

    async with async_session() as db:
        allowed, reason = await check_access(db, tool_name, args)

        if not allowed:
            await audit_request(
                db,
                tool_name=tool_name,
                args=args,
                caller="mcp-external",
                granted=False,
                result_summary=reason,
            )
            return {"error": reason, "tool": tool_name}

        try:
            result = await handler(db, args)
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            await audit_request(
                db,
                tool_name=tool_name,
                args=args,
                caller="mcp-external",
                granted=True,
                result_summary=f"error: {exc}",
                duration_ms=duration,
            )
            return {"error": str(exc), "tool": tool_name}

        duration = (time.monotonic() - start) * 1000
        summary = json.dumps(result)[:200] if isinstance(result, dict) else str(result)[:200]
        await audit_request(
            db,
            tool_name=tool_name,
            args=args,
            caller="mcp-external",
            granted=True,
            result_summary=summary,
            duration_ms=duration,
        )
        return result


# ---------------------------------------------------------------------------
# MCP server definition (only created when fastmcp is installed)
# ---------------------------------------------------------------------------

if MCP_AVAILABLE:
    mcp = FastMCP("Istara", description="Local-first AI agent for UX Research")

    # ---- Low-risk tools ---------------------------------------------------

    @mcp.tool()
    async def list_skills() -> dict:
        """List all available UXR skills with descriptions."""

        async def _handler(db, args):
            from app.skills.registry import registry
            skills = registry.list_all()
            return {
                "skills": [
                    {
                        "name": s.name,
                        "display_name": s.display_name,
                        "description": s.description,
                        "phase": s.phase.value,
                    }
                    for s in skills
                ],
                "count": len(skills),
            }

        return await _gated_call("list_skills", {}, _handler)

    @mcp.tool()
    async def list_projects() -> dict:
        """List research projects (names and IDs only)."""

        async def _handler(db, args):
            from sqlalchemy import select as sa_select
            from app.models.project import Project

            result = await db.execute(
                sa_select(Project.id, Project.name).order_by(Project.created_at.desc())
            )
            rows = result.all()
            return {
                "projects": [{"id": r[0], "name": r[1]} for r in rows],
                "count": len(rows),
            }

        return await _gated_call("list_projects", {}, _handler)

    @mcp.tool()
    async def get_deployment_status() -> dict:
        """Get status of active research deployments."""

        async def _handler(db, args):
            from sqlalchemy import select as sa_select
            from app.models.research_deployment import ResearchDeployment

            result = await db.execute(
                sa_select(ResearchDeployment)
                .order_by(ResearchDeployment.created_at.desc())
                .limit(10)
            )
            deployments = result.scalars().all()
            return {
                "deployments": [d.to_dict() for d in deployments],
                "count": len(deployments),
            }

        return await _gated_call("get_deployment_status", {}, _handler)

    # ---- Sensitive tools --------------------------------------------------

    @mcp.tool()
    async def get_findings(project_id: str, finding_type: str = "all") -> dict:
        """Get research findings for a project.

        SENSITIVE: contains research data. Requires explicit permission.

        Args:
            project_id: The project to retrieve findings from.
            finding_type: "nugget", "fact", "insight", "recommendation", or "all".
        """

        async def _handler(db, args: dict[str, Any]):
            from sqlalchemy import select as sa_select
            from app.models.finding import Fact, Insight, Nugget, Recommendation
            from app.services.mcp_security import get_default_policy

            policy = await get_default_policy(db)
            limit = policy.max_findings_per_request if policy else 50

            pid = args["project_id"]
            ft = args.get("finding_type", "all")

            type_map = {
                "nugget": Nugget,
                "fact": Fact,
                "insight": Insight,
                "recommendation": Recommendation,
            }

            results: dict[str, list] = {}

            if ft == "all":
                models = type_map.items()
            elif ft in type_map:
                models = [(ft, type_map[ft])]
            else:
                return {"error": f"Invalid finding_type: {ft}"}

            for name, model in models:
                rows = await db.execute(
                    sa_select(model)
                    .where(model.project_id == pid)
                    .order_by(model.created_at.desc())
                    .limit(limit)
                )
                items = rows.scalars().all()
                results[name] = [
                    {"id": i.id, "text": i.text, "phase": getattr(i, "phase", "")}
                    for i in items
                ]

            return {
                "project_id": pid,
                "findings": results,
                "warning": "SENSITIVE: This response contains research data.",
            }

        return await _gated_call(
            "get_findings",
            {"project_id": project_id, "finding_type": finding_type},
            _handler,
        )

    @mcp.tool()
    async def search_memory(query: str, top_k: int = 5) -> dict:
        """Search the agent's long-term memory.

        SENSITIVE: exposes internal knowledge base.

        Args:
            query: Natural language search query.
            top_k: Number of results to return.
        """

        async def _handler(db, args):
            try:
                from app.core.rag import retrieve_context
                # Use the first available project or a global search
                ctx = await retrieve_context("", args["query"], top_k=args.get("top_k", 5))
                return {
                    "query": args["query"],
                    "results": [
                        {"text": r.text, "source": r.source, "score": round(r.score, 3)}
                        for r in ctx.retrieved
                    ],
                    "count": len(ctx.retrieved),
                    "warning": "SENSITIVE: Memory search results may contain private research data.",
                }
            except Exception as exc:
                return {"query": args["query"], "results": [], "error": str(exc)}

        return await _gated_call("search_memory", {"query": query, "top_k": top_k}, _handler)

    # ---- High-risk tools --------------------------------------------------

    @mcp.tool()
    async def execute_skill(skill_name: str, project_id: str, parameters: dict | None = None) -> dict:
        """Execute a UXR skill on a project.

        HIGH RISK: Modifies data and may trigger external actions.
        Rate-limited to max_skill_executions_per_hour.

        Args:
            skill_name: The skill to execute.
            project_id: Target project.
            parameters: Optional skill parameters.
        """

        async def _handler(db, args):
            from app.core.agent import agent
            from app.skills.base import SkillInput

            output = await agent.execute_skill(
                skill_name=args["skill_name"],
                project_id=args["project_id"],
                parameters=args.get("parameters") or {},
            )
            return {
                "success": output.success,
                "summary": output.summary,
                "nuggets_created": len(output.nuggets),
                "facts_created": len(output.facts),
                "insights_created": len(output.insights),
                "warning": "HIGH RISK: Skill execution may modify project data.",
            }

        return await _gated_call(
            "execute_skill",
            {
                "skill_name": skill_name,
                "project_id": project_id,
                "parameters": parameters or {},
            },
            _handler,
        )

    @mcp.tool()
    async def create_project(name: str, description: str = "") -> dict:
        """Create a new research project.

        HIGH RISK: Creates persistent data.

        Args:
            name: Project name.
            description: Optional description.
        """

        async def _handler(db, args):
            import uuid as _uuid
            from app.models.project import Project

            project = Project(
                id=str(_uuid.uuid4()),
                name=args["name"],
                description=args.get("description", ""),
            )
            db.add(project)
            await db.commit()
            await db.refresh(project)
            return {
                "id": project.id,
                "name": project.name,
                "warning": "HIGH RISK: A new project has been created.",
            }

        return await _gated_call(
            "create_project",
            {"name": name, "description": description},
            _handler,
        )

    @mcp.tool()
    async def deploy_research(project_id: str, target: str = "report") -> dict:
        """Deploy research outputs (generate report, export data).

        HIGH RISK: May publish or export data externally.

        Args:
            project_id: Project to deploy.
            target: Deployment target (report, export, presentation).
        """

        async def _handler(db, args):
            # Placeholder: actual deployment logic depends on the target
            return {
                "status": "deployment_initiated",
                "project_id": args["project_id"],
                "target": args.get("target", "report"),
                "warning": "HIGH RISK: Research deployment initiated.",
            }

        return await _gated_call(
            "deploy_research",
            {"project_id": project_id, "target": target},
            _handler,
        )

else:
    # fastmcp not installed — expose a None sentinel
    mcp = None  # type: ignore[assignment]
