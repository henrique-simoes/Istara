"""MCP security service — access control, rate limiting, and audit logging.

SECURITY: ReClaw is local-first.  The MCP server breaks that boundary by
allowing external AI agents to access local research data.  Every tool
invocation must pass through this service before executing.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_access_policy import MCPAccessPolicy
from app.models.mcp_audit_log import MCPAuditEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool -> policy field mapping
# ---------------------------------------------------------------------------

TOOL_PERMISSION_MAP: dict[str, str] = {
    "list_skills": "allow_list_skills",
    "execute_skill": "allow_execute_skill",
    "get_findings": "allow_get_findings",
    "create_project": "allow_create_project",
    "list_projects": "allow_list_projects",
    "search_memory": "allow_search_memory",
    "deploy_research": "allow_deploy_research",
    "get_deployment_status": "allow_get_deployment_status",
}

TOOL_RISK_LEVELS: dict[str, str] = {
    "list_skills": "low",
    "list_projects": "low",
    "get_deployment_status": "low",
    "get_findings": "sensitive",
    "search_memory": "sensitive",
    "execute_skill": "high",
    "create_project": "high",
    "deploy_research": "high",
}


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


async def get_default_policy(db: AsyncSession) -> MCPAccessPolicy | None:
    """Retrieve the default access policy (is_default=True)."""
    result = await db.execute(
        select(MCPAccessPolicy).where(MCPAccessPolicy.is_default.is_(True)).limit(1)
    )
    return result.scalar_one_or_none()


async def ensure_default_policy(db: AsyncSession) -> MCPAccessPolicy:
    """Return the default policy, creating one if none exists.

    The default policy has LOW-risk tools enabled and everything else OFF.
    """
    policy = await get_default_policy(db)
    if policy:
        return policy

    policy = MCPAccessPolicy(
        id=str(uuid.uuid4()),
        name="Default Policy",
        description=(
            "Auto-created default policy. LOW-risk tools are enabled; "
            "SENSITIVE and HIGH-risk tools are disabled."
        ),
        is_default=True,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    logger.info("Created default MCP access policy: %s", policy.id)
    return policy


# ---------------------------------------------------------------------------
# Access checks
# ---------------------------------------------------------------------------


async def check_access(
    db: AsyncSession,
    tool_name: str,
    arguments: dict | None = None,
) -> tuple[bool, str]:
    """Check whether a tool invocation is allowed under the current policy.

    Returns:
        (allowed, reason) — allowed is True if permitted, reason explains why not.
    """
    policy = await get_default_policy(db)
    if not policy:
        return False, "No MCP access policy configured"

    # Check per-tool permission
    field_name = TOOL_PERMISSION_MAP.get(tool_name)
    if not field_name:
        return False, f"Unknown tool: {tool_name}"

    allowed = getattr(policy, field_name, False)
    if not allowed:
        risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")
        return False, f"Tool '{tool_name}' is disabled (risk: {risk})"

    # For project-scoped tools, check project allowlist
    if arguments and "project_id" in arguments:
        project_id = arguments["project_id"]
        allowed_ids_raw = policy.allowed_project_ids_json or "[]"
        try:
            allowed_ids = json.loads(allowed_ids_raw)
        except (json.JSONDecodeError, TypeError):
            allowed_ids = []

        if allowed_ids and "*" not in allowed_ids:
            if project_id not in allowed_ids:
                return False, f"Project '{project_id}' is not in the allowed project list"

    # Rate-limit check for high-risk tools
    if TOOL_RISK_LEVELS.get(tool_name) == "high":
        within_limits = await enforce_rate_limits(db, policy, tool_name)
        if not within_limits:
            return False, f"Rate limit exceeded for '{tool_name}'"

    return True, "access_granted"


async def enforce_rate_limits(
    db: AsyncSession,
    policy: MCPAccessPolicy,
    tool_name: str,
) -> bool:
    """Check whether a high-risk tool is within its rate limit.

    Uses the audit log to count invocations in the past hour.
    """
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    result = await db.execute(
        select(func.count(MCPAuditEntry.id)).where(
            MCPAuditEntry.tool_name == tool_name,
            MCPAuditEntry.access_granted.is_(True),
            MCPAuditEntry.timestamp >= one_hour_ago,
        )
    )
    count = result.scalar() or 0

    if tool_name == "execute_skill":
        return count < policy.max_skill_executions_per_hour

    # Generic high-risk limit: 20 per hour
    return count < 20


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


async def audit_request(
    db: AsyncSession,
    tool_name: str,
    args: dict,
    caller: str,
    granted: bool,
    result_summary: str = "",
    duration_ms: float = 0,
) -> None:
    """Record an MCP request in the audit log."""
    policy = await get_default_policy(db)

    entry = MCPAuditEntry(
        id=str(uuid.uuid4()),
        tool_name=tool_name,
        arguments_json=json.dumps(args) if args else "{}",
        caller_info=caller,
        policy_id=policy.id if policy else None,
        access_granted=granted,
        result_summary=result_summary[:500] if result_summary else "",
        duration_ms=duration_ms,
    )
    db.add(entry)
    await db.commit()


# ---------------------------------------------------------------------------
# Exposure & audit reporting
# ---------------------------------------------------------------------------


async def get_exposure_summary(db: AsyncSession) -> dict:
    """Summarise what is currently exposed via MCP.

    Returns counts of enabled tools by risk level, recent request volume,
    and denied-request count.
    """
    policy = await get_default_policy(db)
    if not policy:
        return {"status": "no_policy", "exposed_tools": 0}

    enabled_by_risk: dict[str, list[str]] = {"low": [], "sensitive": [], "high": []}
    for tool_name, field_name in TOOL_PERMISSION_MAP.items():
        if getattr(policy, field_name, False):
            risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")
            enabled_by_risk.setdefault(risk, []).append(tool_name)

    # Recent activity counts (last 24h)
    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    total_result = await db.execute(
        select(func.count(MCPAuditEntry.id)).where(
            MCPAuditEntry.timestamp >= one_day_ago,
        )
    )
    denied_result = await db.execute(
        select(func.count(MCPAuditEntry.id)).where(
            MCPAuditEntry.timestamp >= one_day_ago,
            MCPAuditEntry.access_granted.is_(False),
        )
    )

    total_24h = total_result.scalar() or 0
    denied_24h = denied_result.scalar() or 0

    total_enabled = sum(len(v) for v in enabled_by_risk.values())

    return {
        "policy_id": policy.id,
        "policy_name": policy.name,
        "exposed_tools": total_enabled,
        "enabled_by_risk": enabled_by_risk,
        "requests_last_24h": total_24h,
        "denied_last_24h": denied_24h,
        "warning": (
            "SENSITIVE or HIGH-risk tools are enabled. External agents can "
            "access research data."
        )
        if enabled_by_risk.get("sensitive") or enabled_by_risk.get("high")
        else None,
    }


async def get_audit_log(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retrieve recent audit log entries."""
    result = await db.execute(
        select(MCPAuditEntry)
        .order_by(MCPAuditEntry.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    entries = result.scalars().all()
    return [e.to_dict() for e in entries]
