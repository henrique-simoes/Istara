"""Codebook Version API — persistent, versioned codebooks per project."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.models.code_application import CodeApplication
from app.models.codebook_version import CodebookVersion
from app.models.database import get_db
from app.models.finding import Nugget

router = APIRouter(prefix="/codebook-versions")


class CodebookVersionCreate(BaseModel):
    project_id: str
    version: str = "1.0.0"
    codes: list[dict] = []
    change_log: str = ""
    created_by: str = ""
    methodology: str = "codebook_ta"


def _safe_json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


async def _derived_codebook(project_id: str, db: AsyncSession) -> dict | None:
    """Build a codebook view from applied tags/codes when no version exists."""
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}

    nuggets = (
        await db.execute(select(Nugget.text, Nugget.tags).where(Nugget.project_id == project_id))
    ).all()
    for text, tags_json in nuggets:
        for tag in _safe_json_list(tags_json):
            if not isinstance(tag, str) or not tag.strip():
                continue
            counts[tag] = counts.get(tag, 0) + 1
            if len(examples.setdefault(tag, [])) < 2 and text:
                examples[tag].append(text[:260])

    code_rows = (
        await db.execute(
            select(
                CodeApplication.code_id,
                func.count(CodeApplication.id),
                func.avg(CodeApplication.confidence),
            )
            .where(CodeApplication.project_id == project_id)
            .group_by(CodeApplication.code_id)
        )
    ).all()
    confidence_by_code: dict[str, float | None] = {}
    for code_id, count, confidence in code_rows:
        if not code_id:
            continue
        counts[code_id] = counts.get(code_id, 0) + int(count or 0)
        confidence_by_code[code_id] = round(float(confidence), 3) if confidence is not None else None

    if not counts:
        return None

    codes = [
        {
            "code_id": tag,
            "label": tag,
            "brief_definition": "Derived from project tags and coding applications.",
            "full_definition": "This code is currently inferred from tags applied to findings, interview nuggets, or code applications.",
            "exclusion_criteria": "",
            "typical_example": examples.get(tag, [""])[0],
            "boundary_example": "\n".join(examples.get(tag, [])[1:]),
            "coding_method": "derived",
            "frequency": count,
            "parent_theme": None,
            "avg_confidence": confidence_by_code.get(tag),
        }
        for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]
    return {
        "id": f"derived-{project_id}",
        "project_id": project_id,
        "version": "derived",
        "codes": codes,
        "change_log": "Derived from project tags and code applications.",
        "created_by": "system",
        "methodology": "codebook_ta",
        "created_at": None,
    }


@router.get("/{project_id}")
async def get_codebook_versions(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all codebook versions for a project, ordered by creation time (newest first)."""
    await require_project_access(db, request, project_id, min_role="viewer")

    result = await db.execute(
        select(CodebookVersion).where(
            CodebookVersion.project_id == project_id
        ).order_by(CodebookVersion.created_at.desc())
    )
    versions = [cv.to_dict() for cv in result.scalars().all()]
    derived = await _derived_codebook(project_id, db)
    if derived:
        versions.append(derived)
    return versions


@router.get("/{project_id}/latest")
async def get_latest_codebook(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest codebook version for a project."""
    await require_project_access(db, request, project_id, min_role="viewer")

    result = await db.execute(
        select(CodebookVersion).where(
            CodebookVersion.project_id == project_id
        ).order_by(CodebookVersion.created_at.desc()).limit(1)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        derived = await _derived_codebook(project_id, db)
        return derived or {"message": "No codebook versions found", "codes": []}
    return cv.to_dict()


@router.post("", status_code=201)
async def create_codebook_version(
    data: CodebookVersionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new codebook version."""
    await require_project_access(db, request, data.project_id, min_role="researcher")

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
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific codebook version by ID."""
    result = await db.execute(
        select(CodebookVersion).where(CodebookVersion.id == version_id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="Codebook version not found")
    await require_project_access(db, request, cv.project_id, min_role="viewer")
    return cv.to_dict()
