"""Python wrapper for Figma REST API v1."""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FigmaService:
    """Python wrapper for Figma REST API v1."""

    def _resolve_token(self, api_token: str | None = None) -> str:
        return (api_token if api_token is not None else settings.figma_api_token).strip()

    def _ensure_configured(self, api_token: str | None = None) -> str:
        resolved_token = self._resolve_token(api_token)
        if not resolved_token:
            raise ValueError("Figma API token not configured for this project.")
        return resolved_token

    def _headers(self, api_token: str | None = None) -> dict[str, str]:
        return {"X-Figma-Token": self._ensure_configured(api_token)}

    @staticmethod
    def parse_figma_url(url: str) -> dict:
        """Parse a Figma URL into file_key and optional node_id."""
        match = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", url)
        file_key = match.group(1) if match else ""
        node_match = re.search(r"node-id=([^&]+)", url)
        node_id = node_match.group(1) if node_match else None
        return {"file_key": file_key, "node_id": node_id}

    async def health_check(self, api_token: str | None = None) -> bool:
        """Check whether the Figma API is reachable with valid credentials."""
        try:
            token = self._ensure_configured(api_token)
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{settings.figma_api_host}/v1/me", headers=self._headers(token)
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def get_file(self, file_key: str, api_token: str | None = None) -> dict:
        """Retrieve a full Figma file."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}",
                headers=self._headers(api_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_file_nodes(
        self,
        file_key: str,
        node_ids: list[str],
        api_token: str | None = None,
    ) -> dict:
        """Retrieve specific nodes from a Figma file."""
        ids_param = ",".join(node_ids)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/nodes?ids={ids_param}",
                headers=self._headers(api_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_images(
        self,
        file_key: str,
        node_ids: list[str],
        fmt: str = "png",
        api_token: str | None = None,
    ) -> dict:
        """Export node images from a Figma file."""
        ids_param = ",".join(node_ids)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/images/{file_key}?ids={ids_param}&format={fmt}",
                headers=self._headers(api_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_components(self, file_key: str, api_token: str | None = None) -> dict:
        """List all components in a Figma file."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/components",
                headers=self._headers(api_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_styles(self, file_key: str, api_token: str | None = None) -> dict:
        """List all styles in a Figma file."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{settings.figma_api_host}/v1/files/{file_key}/styles",
                headers=self._headers(api_token),
            )
            resp.raise_for_status()
            return resp.json()

    async def extract_design_system(self, file_key: str, api_token: str | None = None) -> dict:
        """Combine components + styles into a design system summary."""
        components = await self.get_components(file_key, api_token=api_token)
        styles = await self.get_styles(file_key, api_token=api_token)
        return {
            "file_key": file_key,
            "components": components.get("meta", {}).get("components", []),
            "styles": styles.get("meta", {}).get("styles", []),
        }


figma_service = FigmaService()
