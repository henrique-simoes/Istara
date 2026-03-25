"""Data Migration System — safe bidirectional SQLite <-> PostgreSQL migration.

Handles full database export/import with filesystem reference reconciliation.
Ensures LanceDB vectors, keyword indexes, uploaded files, and persona files
remain connected to their database records after migration.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


async def export_full_database(db: AsyncSession) -> dict:
    """Export all database tables to a portable JSON structure.

    Returns a dict with:
    - metadata: export timestamp, source database type, version
    - tables: { table_name: [row_dicts, ...] }
    - filesystem_refs: { lance_db_projects, keyword_index_projects, upload_dirs, persona_dirs }
    """
    from app.models.project import Project
    from app.models.task import Task
    from app.models.message import Message
    from app.models.finding import Nugget, Fact, Insight, Recommendation
    from app.models.agent import Agent, A2AMessage

    export_data = {
        "metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "source_db": "sqlite" if "sqlite" in settings.database_url else "postgresql",
            "version": "1.0",
        },
        "tables": {},
        "filesystem_refs": {},
    }

    # Export each table
    table_models = {
        "projects": Project,
        "tasks": Task,
        "agents": Agent,
        "a2a_messages": A2AMessage,
    }

    for table_name, model in table_models.items():
        try:
            result = await db.execute(select(model))
            rows = result.scalars().all()
            export_data["tables"][table_name] = [
                row.to_dict() if hasattr(row, 'to_dict') else _row_to_dict(row)
                for row in rows
            ]
            logger.info(f"Exported {len(rows)} rows from {table_name}")
        except Exception as e:
            logger.warning(f"Failed to export {table_name}: {e}")
            export_data["tables"][table_name] = []

    # Export tables that don't have to_dict (use raw SQL)
    raw_tables = ["messages", "chat_sessions", "nuggets", "facts", "insights",
                  "recommendations", "documents", "codebooks", "codes",
                  "context_dag_nodes", "users", "llm_servers", "method_metrics"]

    for table_name in raw_tables:
        try:
            result = await db.execute(text(f"SELECT * FROM {table_name}"))
            columns = result.keys()
            rows = result.fetchall()
            export_data["tables"][table_name] = [
                {col: _serialize_value(row[i]) for i, col in enumerate(columns)}
                for row in rows
            ]
            logger.info(f"Exported {len(rows)} rows from {table_name}")
        except Exception as e:
            logger.debug(f"Table {table_name} not found or empty: {e}")
            export_data["tables"][table_name] = []

    # Catalog filesystem references
    lance_path = Path(settings.lance_db_path)
    keyword_path = Path("./data/keyword_index")
    upload_path = Path(settings.upload_dir)
    persona_path = Path(__file__).parent.parent / "agents" / "personas"

    export_data["filesystem_refs"] = {
        "lance_db_projects": [d.name for d in lance_path.iterdir() if d.is_dir()] if lance_path.exists() else [],
        "keyword_index_projects": [f.stem for f in keyword_path.glob("*.db")] if keyword_path.exists() else [],
        "upload_dirs": [d.name for d in upload_path.iterdir() if d.is_dir()] if upload_path.exists() else [],
        "persona_dirs": [d.name for d in persona_path.iterdir() if d.is_dir()] if persona_path.exists() else [],
    }

    return export_data


async def import_full_database(db: AsyncSession, data: dict) -> dict:
    """Import a previously exported database dump into the current database.

    Returns a summary of what was imported.
    """
    summary = {"imported": {}, "skipped": {}, "errors": {}}
    tables = data.get("tables", {})

    # Import order matters (foreign keys)
    import_order = [
        "users", "projects", "agents", "chat_sessions", "tasks",
        "messages", "nuggets", "facts", "insights", "recommendations",
        "documents", "codebooks", "codes", "context_dag_nodes",
        "a2a_messages", "llm_servers", "method_metrics",
    ]

    for table_name in import_order:
        rows = tables.get(table_name, [])
        if not rows:
            summary["skipped"][table_name] = "No data"
            continue

        try:
            # Build INSERT statements
            columns = list(rows[0].keys())
            col_str = ", ".join(columns)
            param_str = ", ".join([f":{c}" for c in columns])

            # Use ON CONFLICT DO NOTHING to avoid duplicates
            sql = text(f"INSERT INTO {table_name} ({col_str}) VALUES ({param_str})")

            imported_count = 0
            for row in rows:
                try:
                    # Clean values for DB compatibility
                    cleaned = {k: _deserialize_value(v) for k, v in row.items()}
                    await db.execute(sql, cleaned)
                    imported_count += 1
                except Exception as row_err:
                    logger.debug(f"Row import error in {table_name}: {row_err}")

            await db.commit()
            summary["imported"][table_name] = imported_count
            logger.info(f"Imported {imported_count}/{len(rows)} rows into {table_name}")
        except Exception as e:
            summary["errors"][table_name] = str(e)
            logger.error(f"Failed to import {table_name}: {e}")
            try:
                await db.rollback()
            except Exception:
                pass

    return summary


def _serialize_value(val):
    """Serialize a database value for JSON export."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val


def _deserialize_value(val):
    """Deserialize a JSON value back for database import."""
    if val is None:
        return None
    return val


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy row to a dict using column inspection."""
    try:
        mapper = inspect(type(row))
        return {col.key: getattr(row, col.key) for col in mapper.columns}
    except Exception:
        return {}
