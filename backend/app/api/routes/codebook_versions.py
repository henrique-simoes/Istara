"""Codebook Version API — persistent, versioned codebooks per project."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.codebook_version import CodebookVersion
from app.models.database import get_db

router = APIRouter(prefix="/codebook-versions")


class CodebookVersionCreate(BaseModel):
    project_id: str
    version: str = "1.0.0"
    codes: list[dict] = []
    change_log: str = ""
    created_by: str = ""
    methodology: str = "codebook_ta"


@router.get("/{project_id}")
async def get_codebook_versions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all codebook versions for a project, ordered by creation time (newest first)."""
    result = await db.execute(
        select(CodebookVersion).where(
            CodebookVersion.project_id == project_id
        ).order_by(CodebookVersion.created_at.desc())
    )
    return [cv.to_dict() for cv in result.scalars().all()]


@router.get("/{project_id}/latest")
async def get_latest_codebook(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest codebook version for a project."""
    result = await db.execute(
        select(CodebookVersion).where(
            CodebookVersion.project_id == project_id
        ).order_by(CodebookVersion.created_at.desc()).limit(1)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        return {"message": "No codebook versions found", "codes": []}
    return cv.to_dict()


@router.post("", status_code=201)
async def create_codebook_version(
    data: CodebookVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new codebook version."""
    cv = CodebookVersion(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        version=data.version,
        codes_json=json.dumps(data.codes),
        change_log=data.change_log,
        created_by=data.created_by,
        methodology=data.methodology,
    )
    db.add(cv)
    await db.commit()
    await db.refresh(cv)
    return cv.to_dict()


@router.get("/detail/{version_id}")
async def get_codebook_version_detail(
    version_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific codebook version by ID."""
    result = await db.execute(
        select(CodebookVersion).where(CodebookVersion.id == version_id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="Codebook version not found")
    return cv.to_dict()
