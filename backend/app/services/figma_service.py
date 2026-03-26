"""Python wrapper for Figma REST API v1."""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FigmaService:
    """Python wrapper for Figma REST API v1."""

    def _ensure_configured(self) -> None:
        if not settings.figma_api_token:
            raise ValueError(
                "Figma API token not configured. Set FIGMA_API_TOKEN in settings."
            )

    def _headers(self) -> dict[str, str]:
        return {"X-Figma-Token": settings.figma_api_token}

    @staticmethod
    def parse_figma_url(url: str) -> dict:
        """Parse a Figma URL into file_key and optional node_id."""
        match = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", url)
        file_key = match.group(1) if match else ""
        node_match = re.search(r"node-id=([^&]+)", url)
        node_id = node_match.group(1) if node_match else None
        return {"file_key": file_key, "node_id": node_id}

    async def health_check(self) -> bool:
        """Check whether the Figma API is reachable with valid credentials."""
        try:
            self._ensure_configured()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.figma_api_host}/v1/me", headers=self._headers()
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def get_file(self, file_key: str) -> dict:
        """Retrieve a full Figma file."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_file_nodes(self, file_key: str, node_ids: list[str]) -> dict:
        """Retrieve specific nodes from a Figma file."""
        self._ensure_configured()
        ids_param = ",".join(node_ids)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/nodes?ids={ids_param}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_images(
        self, file_key: str, node_ids: list[str], fmt: str = "png"
    ) -> dict:
        """Export node images from a Figma file."""
        self._ensure_configured()
        ids_param = ",".join(node_ids)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/images/{file_key}?ids={ids_param}&format={fmt}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_components(self, file_key: str) -> dict:
        """List all components in a Figma file."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/components",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_styles(self, file_key: str) -> dict:
        """List all styles in a Figma file."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/styles",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def extract_design_system(self, file_key: str) -> dict:
        """Combine components + styles into a design system summary."""
        self._ensure_configured()
        components = await self.get_components(file_key)
        styles = await self.get_styles(file_key)
        return {
            "file_key": file_key,
            "components": components.get("meta", {}).get("components", []),
            "styles": styles.get("meta", {}).get("styles", []),
        }


figma_service = FigmaService()
