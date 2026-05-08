"""Shared contracts and helpers for Interfaces routes."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_thinking import ThinkingMode
from app.core.permissions import get_subject, is_global_admin, require_project_access
from app.models.design_screen import DesignScreen


def resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


def require_mock_interfaces_enabled() -> None:
    """Block mock design endpoints in public production installs by default."""
    if (
        settings.istara_runtime_profile == "public"
        and not settings.interfaces_mock_endpoints_enabled
    ):
        raise HTTPException(status_code=404, detail="Mock Interfaces endpoints are disabled.")


async def get_screen_or_404(db: AsyncSession, screen_id: str) -> DesignScreen:
    result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
    screen = result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen


async def require_integration_admin(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
) -> None:
    subject = get_subject(request)
    if is_global_admin(subject):
        return
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    await require_project_access(db, request, project_id, min_role="project_admin")


class DesignChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=20000)
    project_id: str = Field(..., min_length=1)
    session_id: str | None = None
    thinking_mode: ThinkingMode | None = None


class GenerateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1, max_length=12000)
    device_type: Literal["MOBILE", "DESKTOP", "TABLET", "AGNOSTIC"] = "DESKTOP"
    model: Literal["GEMINI_3_FLASH", "GEMINI_3_PRO", "MODEL_ID_UNSPECIFIED"] = "GEMINI_3_FLASH"
    seed_finding_ids: list[str] = Field(default_factory=list, max_length=10)


class EditRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1, max_length=12000)


class VariantRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)
    variant_type: Literal["REFINE", "EXPLORE", "REIMAGINE"] = "EXPLORE"
    count: int = Field(3, ge=1, le=5)


class FigmaImportRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    figma_url: str = Field(..., min_length=1, max_length=2048)


class FigmaExportRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)
    figma_file_key: str = Field(..., min_length=1, max_length=200)


class HandoffBriefRequest(BaseModel):
    project_id: str = Field(..., min_length=1)


class HandoffDevSpecRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)


class ConfigureStitchRequest(BaseModel):
    api_key: str = Field(default="", max_length=4096)
    project_id: str | None = Field(default=None, max_length=100)

    @field_validator("api_key")
    @classmethod
    def clean_api_key(cls, value: str) -> str:
        value = value.strip()
        if any(ch in value for ch in ("\n", "\r", "\x00")):
            raise ValueError("API keys cannot contain control characters")
        return value


class ConfigureFigmaRequest(BaseModel):
    api_token: str = Field(default="", max_length=4096)
    project_id: str | None = Field(default=None, max_length=100)

    @field_validator("api_token")
    @classmethod
    def clean_api_token(cls, value: str) -> str:
        value = value.strip()
        if any(ch in value for ch in ("\n", "\r", "\x00")):
            raise ValueError("API tokens cannot contain control characters")
        return value


class MockGenerateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    prompt: str = Field("Mock dashboard screen", min_length=1, max_length=12000)
    device_type: Literal["MOBILE", "DESKTOP", "TABLET", "AGNOSTIC"] = "DESKTOP"
    seed_finding_ids: list[str] = Field(default_factory=list, max_length=10)


class MockEditRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)
    instructions: str = Field("Make it blue and add a profile link", min_length=1, max_length=12000)


class MockVariantRequest(BaseModel):
    screen_id: str = Field(..., min_length=1)
    variant_type: Literal["REFINE", "EXPLORE", "REIMAGINE"] = "EXPLORE"
    count: int = Field(3, ge=1, le=5)


class MockFigmaImportRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    figma_url: str = Field(
        "https://www.figma.com/file/abc123XYZ/MockDesignSystem",
        min_length=1,
        max_length=2048,
    )
