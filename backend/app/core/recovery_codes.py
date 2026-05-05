"""Recovery-code lifecycle helpers."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import hash_recovery_code, verify_recovery_code
from app.core.client_identity import get_client_ip
from app.models.recovery_code import RecoveryCode
from app.models.user import User


def _sha256(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request_ip_hash(request: Request | None) -> str:
    if request is None:
        return ""
    return _sha256(get_client_ip(request, settings.trusted_proxy_hosts))


def _request_user_agent_hash(request: Request | None) -> str:
    if request is None:
        return ""
    return _sha256(request.headers.get("user-agent", ""))


async def recovery_code_record_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(RecoveryCode).where(RecoveryCode.user_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def migrate_legacy_recovery_codes(db: AsyncSession, user: User) -> None:
    """Move old newline-separated hashes into the recovery_codes table once."""
    if not user.recovery_codes_hashed:
        return
    if await recovery_code_record_count(db, user.id) > 0:
        return

    now = datetime.now(UTC)
    batch_id = str(uuid.uuid4())
    for legacy_hash in (line.strip() for line in user.recovery_codes_hashed.splitlines()):
        if not legacy_hash:
            continue
        db.add(
            RecoveryCode(
                id=str(uuid.uuid4()),
                user_id=user.id,
                code_hash=legacy_hash,
                batch_id=batch_id,
                created_by_user_id="legacy-column",
                created_at=now,
            )
        )
    user.recovery_codes_hashed = None


async def replace_recovery_codes(
    db: AsyncSession,
    *,
    user_id: str,
    codes: list[str],
    request: Request | None = None,
    created_by_user_id: str = "",
) -> None:
    """Replace all unused recovery codes with a new one-time code batch."""
    now = datetime.now(UTC)
    await db.execute(
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.used_at.is_(None),
            RecoveryCode.replaced_at.is_(None),
        )
        .values(replaced_at=now)
    )

    batch_id = str(uuid.uuid4())
    for code in codes:
        db.add(
            RecoveryCode(
                id=str(uuid.uuid4()),
                user_id=user_id,
                code_hash=hash_recovery_code(code),
                batch_id=batch_id,
                created_by_user_id=created_by_user_id[:36],
                created_at=now,
            )
        )


async def consume_recovery_code(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    request: Request | None = None,
) -> bool:
    """Mark a matching recovery code as used without deleting audit metadata."""
    await migrate_legacy_recovery_codes(db, user)
    result = await db.execute(
        select(RecoveryCode)
        .where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.used_at.is_(None),
            RecoveryCode.replaced_at.is_(None),
        )
        .order_by(RecoveryCode.created_at.asc())
    )
    now = datetime.now(UTC)
    for record in result.scalars().all():
        if verify_recovery_code(code, record.code_hash):
            record.used_at = now
            record.used_ip_hash = _request_ip_hash(request)
            record.used_user_agent_hash = _request_user_agent_hash(request)
            return True
    return False


async def recovery_code_status(db: AsyncSession, user: User) -> dict[str, Any]:
    """Return current recovery-code batch status."""
    await migrate_legacy_recovery_codes(db, user)
    current = await db.execute(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.replaced_at.is_(None),
        )
    )
    records = current.scalars().all()
    remaining = sum(1 for record in records if record.used_at is None)
    return {"remaining": remaining, "total": len(records) or 8}
