"""Web and context DAG executors for system action tools."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from sqlalchemy import select

from app.models.database import async_session


async def _exec_web_fetch(params: dict, project_id: str, agent_id: str) -> str:
    """Fetch a web page and convert to readable text."""
    import httpx as _httpx

    url = params.get("url", "")
    max_chars = params.get("max_chars", 4000)

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return json.dumps({"error": "Only http:// and https:// URLs are supported"})

    hostname = parsed.hostname or ""
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}
    if hostname in blocked_hosts:
        return json.dumps({"error": "Cannot fetch internal/private network URLs for security"})
    if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
        parts = hostname.split(".")
        if hostname.startswith("172.") and len(parts) >= 2:
            try:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return json.dumps(
                        {"error": "Cannot fetch internal/private network URLs for security"}
                    )
            except ValueError:
                pass
        if hostname.startswith("10.") or hostname.startswith("192.168."):
            return json.dumps({"error": "Cannot fetch internal/private network URLs for security"})

    try:
        async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Istara/1.0 (UX Research Agent)"},
            )
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type:
                try:
                    from html2text import HTML2Text

                    h = HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = True
                    h.body_width = 0
                    text = h.handle(resp.text)
                except ImportError:
                    text = re.sub(r"<[^>]+>", "", resp.text)
                    text = re.sub(r"\s+", " ", text).strip()
            else:
                text = resp.text

            if len(text) > max_chars:
                text = (
                    text[:max_chars]
                    + f"\n\n[Truncated -- showing first {max_chars} of {len(text)} characters]"
                )

            return json.dumps(
                {
                    "url": str(resp.url),
                    "status": resp.status_code,
                    "content_length": len(text),
                    "content": text,
                }
            )
    except _httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}", "url": url}
        )
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


async def _exec_browse_website(params: dict, project_id: str, agent_id: str) -> dict:
    """Execute browse_website tool."""
    from app.services.browser_service import BROWSER_AVAILABLE, browse_website

    if not BROWSER_AVAILABLE:
        return {
            "error": "browser-use not installed. Install: pip install browser-use langchain-openai"
        }

    url = params.get("url", "")
    task = params.get("task", "")
    max_steps = params.get("max_steps", 10)
    if not url:
        return {"error": "url is required"}
    if not task:
        return {"error": "task is required"}

    return await browse_website(url=url, task=task, max_steps=max_steps)


async def _latest_session_id(project_id: str) -> str | None:
    async with async_session() as db:
        from app.models.session import ChatSession

        result = await db.execute(
            select(ChatSession.id)
            .where(ChatSession.project_id == project_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        return result.scalar()


async def _exec_context_expand(params: dict, project_id: str, agent_id: str) -> str:
    """Execute context_expand tool."""
    from app.core.context_tools import context_expand

    session_id = await _latest_session_id(project_id)
    if not session_id:
        return "Error: No active session found for this project."
    return await context_expand(session_id=session_id, node_id=params["node_id"])


async def _exec_context_grep(params: dict, project_id: str, agent_id: str) -> str:
    """Execute context_grep tool."""
    from app.core.context_tools import context_grep

    session_id = await _latest_session_id(project_id)
    if not session_id:
        return "Error: No active session found for this project."
    return await context_grep(session_id=session_id, query=params["query"])
