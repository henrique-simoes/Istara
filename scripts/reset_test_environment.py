#!/usr/bin/env python3
"""Destructively reset the local Istara test environment.

This is intentionally not an application API. It exists for local simulation,
marathon, Colima/Docker, and real-user benchmark setup where the operator wants
to remove all users, projects, app data, and benchmark outputs before seeding a
known admin account.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
PROTECTED_PATHS = {
    (PROJECT_ROOT / "LLMs").resolve(),
    (PROJECT_ROOT / "Model_Finetuning").resolve(),
}

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "istara123"
DEFAULT_RESEARCHER_PASSWORD = "istara123"

RESET_ENV_FLAG = "ISTARA_DESTRUCTIVE_TEST_RESET"
RESET_CONFIRMATION = "DELETE-ISTARA-LOCAL-TEST-DATA"

ARTIFACT_PATHS = [
    "data/uploads",
    "data/projects",
    "data/lance_db",
    "data/keyword_index",
    "data/backups",
    "data/test-marathon",
    "data/embedding_cache.db",
    "data/reclaw.db",
    "data/watcher_state.json",
    "data/_agent_proposals.json",
    "data/_meta_audit_log.jsonl",
    "data/_meta_observations.json",
    "data/_meta_proposals.json",
    "data/_meta_variants.json",
    "tests/simulation/.results",
    "tests/real_user_benchmark/.results",
]

SETTING_PATH_FIELDS = [
    "upload_dir",
    "projects_dir",
    "lance_db_path",
    "backup_dir",
    "design_screens_dir",
    "runtime_personas_dir",
    "runtime_skills_dir",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset only the local Istara test database/artifacts and seed test users."
    )
    parser.add_argument(
        "--confirm", required=True, help=f"Must equal {RESET_CONFIRMATION}"
    )
    parser.add_argument("--admin-username", default=DEFAULT_ADMIN_USERNAME)
    parser.add_argument("--admin-password", default=DEFAULT_ADMIN_PASSWORD)
    parser.add_argument(
        "--researchers", type=int, default=0, help="Number of researcher_N users."
    )
    parser.add_argument("--researcher-password", default=DEFAULT_RESEARCHER_PASSWORD)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without deleting files."
    )
    return parser.parse_args()


def require_confirmation(args: argparse.Namespace) -> None:
    enabled = os.environ.get(RESET_ENV_FLAG, "").lower() in {"1", "true", "yes"}
    if not enabled:
        raise SystemExit(
            f"Refusing reset: set {RESET_ENV_FLAG}=1 to confirm local destructive intent."
        )
    if args.confirm != RESET_CONFIRMATION:
        raise SystemExit(f"Refusing reset: --confirm must be {RESET_CONFIRMATION}.")
    if args.researchers < 0:
        raise SystemExit("Refusing reset: --researchers cannot be negative.")


def resolve_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        raise SystemExit(
            "Refusing reset: DATABASE_URL is not local sqlite+aiosqlite. "
            "Use a separate manual migration/reset procedure for non-local databases."
        )
    raw_path = database_url.removeprefix(prefix)
    if raw_path in {"", ":memory:"}:
        raise SystemExit(
            "Refusing reset: in-memory or empty SQLite path is not resettable."
        )
    path = Path(raw_path)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    resolved = path.resolve()
    allowed_data_roots = {
        (PROJECT_ROOT / "data").resolve(),
        (BACKEND_ROOT / "data").resolve(),
    }
    if not any(
        data_root == resolved.parent or data_root in resolved.parents
        for data_root in allowed_data_roots
    ):
        raise SystemExit(
            f"Refusing reset: SQLite path is outside the local data directory: {resolved}"
        )
    return resolved


def resolve_setting_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


def iter_artifact_paths(settings: object) -> list[Path]:
    paths: list[Path] = []
    for field in SETTING_PATH_FIELDS:
        value = getattr(settings, field, "")
        if value:
            paths.append(resolve_setting_path(str(value)))

    data_dir = resolve_setting_path(str(getattr(settings, "data_dir", "./data")))
    paths.extend(
        [
            data_dir / "keyword_index",
            data_dir / "test-marathon",
            data_dir / "embedding_cache.db",
            data_dir / "reclaw.db",
            data_dir / "watcher_state.json",
            data_dir / "_agent_proposals.json",
            data_dir / "_meta_audit_log.jsonl",
            data_dir / "_meta_observations.json",
            data_dir / "_meta_proposals.json",
            data_dir / "_meta_variants.json",
        ]
    )

    # Also clear legacy repo-root artifacts from older reset/script cwd behavior.
    paths.extend(PROJECT_ROOT / relative_path for relative_path in ARTIFACT_PATHS)
    return list(dict.fromkeys(path.resolve() for path in paths))


def assert_not_protected(path: Path) -> None:
    resolved = path.resolve()
    for protected in PROTECTED_PATHS:
        if resolved == protected or protected in resolved.parents:
            raise SystemExit(
                f"Refusing reset: protected local artifact path would be touched: {resolved}"
            )


def remove_path(path: Path, *, dry_run: bool) -> None:
    assert_not_protected(path)
    if not path.exists():
        return
    label = str(path)
    try:
        label = str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        pass
    if dry_run:
        print(f"dry-run delete {label}")
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"deleted {label}")


def remove_sqlite_files(db_path: Path, *, dry_run: bool) -> None:
    for candidate in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        remove_path(candidate, dry_run=dry_run)


async def seed_users(args: argparse.Namespace) -> None:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    from app.core.auth import hash_password
    from app.core.field_encryption import hash_field
    from app.models.database import async_session, init_db
    from app.models.user import User

    await init_db()
    async with async_session() as session:
        session.add(
            User(
                id=str(uuid.uuid4()),
                username=args.admin_username,
                email=f"{args.admin_username}@istara.test",
                email_hash=hash_field(f"{args.admin_username}@istara.test"),
                password_hash=hash_password(args.admin_password),
                role="admin",
                display_name="Istara Test Admin",
            )
        )
        for index in range(1, args.researchers + 1):
            username = f"researcher_{index}"
            session.add(
                User(
                    id=str(uuid.uuid4()),
                    username=username,
                    email=f"{username}@istara.test",
                    email_hash=hash_field(f"{username}@istara.test"),
                    password_hash=hash_password(args.researcher_password),
                    role="researcher",
                    display_name=f"Istara Test Researcher {index}",
                )
            )
        await session.commit()


async def main() -> None:
    args = parse_args()
    require_confirmation(args)

    os.chdir(BACKEND_ROOT)
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from app.config import settings

    db_path = resolve_sqlite_path(settings.database_url)
    print("Istara local test reset")
    print(f"database={db_path}")
    print(f"admin={args.admin_username}")
    print(f"researchers={args.researchers}")

    remove_sqlite_files(db_path, dry_run=args.dry_run)
    for artifact_path in iter_artifact_paths(settings):
        remove_path(artifact_path, dry_run=args.dry_run)

    if args.dry_run:
        return

    await seed_users(args)
    print("seeded users")
    print("projects=0")


if __name__ == "__main__":
    asyncio.run(main())
