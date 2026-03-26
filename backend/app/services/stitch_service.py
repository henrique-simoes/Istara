"""Python wrapper for Google Stitch REST API."""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.core.content_guard import ContentGuard

logger = logging.getLogger(__name__)
_guard = ContentGuard()


class StitchService:
    """Python wrapper for Google Stitch REST API."""

    def __init__(self) -> None:
        self._base_url = ""
        self._api_key = ""

    def _ensure_configured(self) -> None:
        self._api_key = settings.stitch_api_key
        self._base_url = settings.stitch_api_host
        if not self._api_key:
            raise ValueError("Stitch API key not configured. Set STITCH_API_KEY in settings.")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def health_check(self) -> bool:
        """Check whether the Stitch API is reachable."""
        try:
            self._ensure_configured()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._base_url}/v1/projects", headers=self._headers()
                )
                return resp.status_code < 500
        except Exception:
            return False

    async def create_project(self, name: str) -> dict:
        """Create a new Stitch project."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}/v1/projects",
                headers=self._headers(),
                json={"title": name},
            )
            resp.raise_for_status()
            return resp.json()

    async def generate_screen(
        self,
        project_id: str,
        prompt: str,
        device_type: str = "DESKTOP",
        model: str = "GEMINI_3_FLASH",
    ) -> dict:
        """Generate a UI screen from a text prompt."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/v1/projects/{project_id}/screens:generate",
                headers=self._headers(),
                json={"prompt": prompt, "deviceType": device_type, "modelId": model},
            )
            resp.raise_for_status()
            data = resp.json()
            # Scan generated HTML for injection
            if "html" in data:
                scan = _guard.scan_text(data["html"])
                if not scan.clean:
                    logger.warning(f"Stitch HTML flagged: {scan.threats}")
                    data["html"] = scan.cleaned_text
            return data

    async def edit_screen(
        self, screen_id: str, project_id: str, instructions: str
    ) -> dict:
        """Edit an existing screen with natural-language instructions."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self._base_url}/v1/projects/{project_id}/screens/{screen_id}:edit",
                headers=self._headers(),
                json={"prompt": instructions},
            )
            resp.raise_for_status()
            data = resp.json()
            if "html" in data:
                scan = _guard.scan_text(data["html"])
                if not scan.clean:
                    data["html"] = scan.cleaned_text
            return data

    async def generate_variants(
        self,
        screen_id: str,
        project_id: str,
        variant_type: str = "EXPLORE",
        count: int = 3,
    ) -> list:
        """Generate design variants of an existing screen."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{self._base_url}/v1/projects/{project_id}/screens/{screen_id}:variants",
                headers=self._headers(),
                json={"creativeRange": variant_type, "variantCount": count},
            )
            resp.raise_for_status()
            variants = resp.json().get("variants", [])
            for v in variants:
                if "html" in v:
                    scan = _guard.scan_text(v["html"])
                    if not scan.clean:
                        v["html"] = scan.cleaned_text
            return variants

    async def get_screen(self, project_id: str, screen_id: str) -> dict:
        """Retrieve a single screen by ID."""
        self._ensure_configured()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/v1/projects/{project_id}/screens/{screen_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()


stitch_service = StitchService()
