"""Google Stitch integration via MCP (Model Context Protocol).

Stitch only exposes an MCP server at https://stitch.googleapis.com/mcp.
This service wraps the MCP client to provide async Python methods for
project management, screen generation, editing, variants, and HTML retrieval.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.content_guard import ContentGuard

logger = logging.getLogger(__name__)
_guard = ContentGuard()

MCP_URL = "https://stitch.googleapis.com/mcp"


class StitchService:
    """Python wrapper for Google Stitch via MCP protocol."""

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _ensure_configured(self) -> None:
        if not settings.stitch_api_key:
            raise ValueError(
                "Stitch API key not configured. Set STITCH_API_KEY in settings."
            )

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Open a short-lived MCP session and call a single tool."""
        self._ensure_configured()

        from mcp.client.streamable_http import streamablehttp_client
        from mcp import ClientSession

        headers = {"X-Goog-Api-Key": settings.stitch_api_key}
        async with streamablehttp_client(MCP_URL, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

                # Parse first text content block as JSON if possible
                for content in result.content:
                    if hasattr(content, "text") and content.text:
                        try:
                            return json.loads(content.text)
                        except (json.JSONDecodeError, ValueError):
                            return {"text": content.text}
                    if hasattr(content, "data") and content.data:
                        return {"image_data": content.data, "mime_type": getattr(content, "mimeType", "image/png")}
                return {}

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check whether the Stitch MCP server is reachable."""
        try:
            self._ensure_configured()
            result = await self._call_tool("list_projects", {})
            return isinstance(result, dict)
        except Exception as exc:
            logger.debug("Stitch health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def create_project(self, title: str) -> dict:
        """Create a new Stitch project. Returns {name, title, ...}."""
        data = await self._call_tool("create_project", {"title": title})
        return data

    async def list_projects(self) -> list[dict]:
        """List all accessible Stitch projects."""
        data = await self._call_tool("list_projects", {})
        return data.get("projects", []) if isinstance(data, dict) else []

    @staticmethod
    def extract_project_id(project_name: str) -> str:
        """Extract numeric ID from 'projects/12345' format."""
        return project_name.split("/")[-1] if "/" in project_name else project_name

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------

    async def generate_screen(
        self,
        project_id: str,
        prompt: str,
        device_type: str = "DESKTOP",
        model: str = "GEMINI_3_FLASH",
    ) -> dict:
        """Generate a UI screen from a text prompt.

        Returns the raw Stitch response with outputComponents, sessionId, etc.
        """
        args: dict[str, Any] = {
            "projectId": project_id,
            "prompt": prompt,
            "deviceType": device_type,
        }
        if model and model != "MODEL_ID_UNSPECIFIED":
            args["modelId"] = model

        data = await self._call_tool("generate_screen_from_text", args)
        return data

    async def list_screens(self, project_id: str) -> list[dict]:
        """List all screens in a project."""
        data = await self._call_tool("list_screens", {"projectId": project_id})
        return data.get("screens", []) if isinstance(data, dict) else []

    async def get_screen(self, project_id: str, screen_id: str) -> dict:
        """Get screen details. Use full resource name format."""
        name = f"projects/{project_id}/screens/{screen_id}"
        data = await self._call_tool("get_screen", {
            "name": name,
            "projectId": project_id,
            "screenId": screen_id,
        })
        return data

    async def get_screen_html(self, project_id: str, screen_id: str) -> str:
        """Get the HTML content of a screen.

        Fetches screen details, finds the HTML download URL, downloads it,
        scans with ContentGuard, and returns the HTML string.
        """
        screen_data = await self.get_screen(project_id, screen_id)
        html_url = screen_data.get("htmlUrl") or screen_data.get("html_url", "")

        if html_url:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(html_url)
                resp.raise_for_status()
                html = resp.text
        else:
            # Some responses embed HTML inline
            html = screen_data.get("html", screen_data.get("htmlContent", ""))

        # Security: scan for injection
        if html:
            scan = _guard.scan_text(html)
            if not scan.clean:
                logger.warning("Stitch HTML flagged: %s", scan.threats)
                html = scan.cleaned_text

        return html

    async def get_screen_image(self, project_id: str, screen_id: str) -> bytes | None:
        """Get screenshot image as bytes. Returns None if unavailable."""
        name = f"projects/{project_id}/screens/{screen_id}"
        try:
            data = await self._call_tool("get_screen", {
                "name": name,
                "projectId": project_id,
                "screenId": screen_id,
            })
            image_url = data.get("imageUrl") or data.get("image_url", "")
            if image_url:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(image_url)
                    resp.raise_for_status()
                    return resp.content
            # Check for inline base64 image
            if data.get("image_data"):
                import base64
                return base64.b64decode(data["image_data"])
        except Exception as exc:
            logger.warning("Failed to get screen image: %s", exc)
        return None

    async def save_screen_image(
        self, project_id: str, screen_id: str, dest_dir: str | None = None
    ) -> str | None:
        """Download and save screenshot to design_screens_dir. Returns path."""
        image_bytes = await self.get_screen_image(project_id, screen_id)
        if not image_bytes:
            return None

        save_dir = Path(dest_dir or settings.design_screens_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / f"{screen_id}.png"
        path.write_bytes(image_bytes)
        return str(path)

    # ------------------------------------------------------------------
    # Edit & Variants (incremental — not regenerate from scratch)
    # ------------------------------------------------------------------

    async def edit_screen(
        self,
        project_id: str,
        screen_ids: list[str],
        instructions: str,
        device_type: str | None = None,
        model: str | None = None,
    ) -> dict:
        """Edit existing screens with natural-language instructions.

        This is an INCREMENTAL edit — Stitch modifies the existing screens
        rather than generating from scratch.
        """
        args: dict[str, Any] = {
            "projectId": project_id,
            "screenIds": screen_ids,
            "prompt": instructions,
        }
        if device_type:
            args["deviceType"] = device_type
        if model:
            args["modelId"] = model

        data = await self._call_tool("edit_screens", args)
        return data

    async def generate_variants(
        self,
        project_id: str,
        screen_ids: list[str],
        prompt: str,
        variant_count: int = 3,
        creative_range: str = "EXPLORE",
        aspects: list[str] | None = None,
    ) -> dict:
        """Generate design variants of existing screens.

        creative_range: REFINE | EXPLORE | REIMAGINE
        aspects: COLOR_SCHEME, LAYOUT, IMAGES, TEXT_FONT, TEXT_CONTENT
        """
        args: dict[str, Any] = {
            "projectId": project_id,
            "screenIds": screen_ids,
            "prompt": prompt,
            "options": {
                "variantCount": min(max(variant_count, 1), 5),
                "creativeRange": creative_range,
            },
        }
        if aspects:
            args["options"]["aspects"] = aspects

        data = await self._call_tool("generate_variants", args)
        return data

    # ------------------------------------------------------------------
    # Design Systems
    # ------------------------------------------------------------------

    async def create_design_system(self, project_id: str, name: str, theme: dict | None = None) -> dict:
        """Create a design system for a project."""
        args: dict[str, Any] = {"projectId": project_id, "displayName": name}
        if theme:
            args["theme"] = theme
        return await self._call_tool("create_design_system", args)

    async def list_design_systems(self, project_id: str) -> list[dict]:
        """List design systems for a project."""
        data = await self._call_tool("list_design_systems", {"projectId": project_id})
        return data.get("designSystems", []) if isinstance(data, dict) else []

    async def apply_design_system(
        self, project_id: str, design_system_name: str, screen_ids: list[str]
    ) -> dict:
        """Apply a design system to screens."""
        return await self._call_tool("apply_design_system", {
            "projectId": project_id,
            "designSystemName": design_system_name,
            "screenIds": screen_ids,
        })


stitch_service = StitchService()
