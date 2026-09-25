"""Agent memory manager — private scratchpads and active memory tools.

Agent notes are model output. They live in the project's DERIVED index (``rag.DERIVED_TABLE``),
never in the source evidence index, so a note can never be retrieved as evidence or confirm a
claim through ``self_check`` (F5). Each note row carries the writing agent in ``agent_id`` and is
read back with an exact, pre-filtered match: agent ``a1`` never sees agent ``a10``'s notes, and
other agents' notes cannot crowd an agent's own out of the top-k.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.core.content_guard import ContentGuard

logger = logging.getLogger(__name__)
_guard = ContentGuard()

# Notes written before derived text had its own index sit in the source table under this source.
_LEGACY_NOTE_SOURCE = "agent:{agent_id}:note"
_NOTE_LIST_LIMIT = 500


@dataclass
class MemoryNote:
    text: str
    agent_id: str
    project_id: str
    tags: list[str]
    timestamp: float
    source: str = "agent_note"


def _note_source(agent_id: str) -> str:
    return _LEGACY_NOTE_SOURCE.format(agent_id=agent_id)


def _where_equals(column: str, value: str) -> str:
    return f"{column} = '{str(value).replace(chr(39), chr(39) * 2)}'"


class AgentMemoryManager:
    """Manages per-agent private memory and active memory tools."""

    async def write_note(
        self, agent_id: str, project_id: str, note: str, tags: list[str] | None = None
    ) -> None:
        """Agent writes a private note to its memory (derived index, exact agent ownership)."""
        from app.core.embeddings import TextChunk
        from app.core.rag import ingest_derived_chunks

        # Content Guard: scan note before storage
        scan = _guard.scan_text(note)
        if scan.threat_level == "high":
            logger.warning("Agent %s note blocked: %s", agent_id, scan.threats)
            return  # reject high-threat notes
        note = scan.cleaned_text  # use sanitized version

        chunk = TextChunk(
            text=note,
            source=_note_source(agent_id),
            page=None,
            position=0,
            metadata={"agent_id": agent_id, "tags": tags or [], "timestamp": time.time()},
        )
        # Notes accumulate: never replace the agent's earlier notes.
        await ingest_derived_chunks(
            project_id, [chunk], agent_id=agent_id, kind="agent_note", replace_source=False
        )
        logger.info(f"Agent {agent_id} stored note in project {project_id}")

    async def read_notes(
        self, agent_id: str, project_id: str, query: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Read this agent's notes, optionally ranked by a semantic query."""
        if query:
            from app.core.rag import retrieve_derived_context

            results = await retrieve_derived_context(
                project_id, query, top_k=limit, agent_id=agent_id
            )
            return [{"text": r.text, "source": r.source, "score": r.score} for r in results]
        notes = await self.get_all_notes(project_id, agent_id)
        return notes[:limit]

    async def memory_search(
        self, agent_id: str, project_id: str, query: str, top_k: int = 5
    ) -> list[dict]:
        """Agent actively searches the shared project knowledge base (source evidence only)."""
        from app.core.rag import retrieve_context

        context = await retrieve_context(project_id, query, top_k=top_k)
        return [{"text": r.text, "source": r.source, "score": r.score} for r in context.retrieved]

    async def memory_store(
        self, agent_id: str, project_id: str, note: str, tags: list[str] | None = None
    ) -> None:
        """Agent deliberately stores a note in its derived memory with provenance."""
        await self.write_note(agent_id, project_id, note, tags)

    async def get_all_notes(self, project_id: str, agent_id: str | None = None) -> list[dict]:
        """Notes for the Memory UI, newest first, filtered in the query (never a whole-table load).

        Reads the derived index plus notes a build before the split wrote into the source table.
        """
        from app.core.rag import DERIVED_TABLE, VectorStore

        notes: list[dict] = []
        for table_name, where in (
            (
                DERIVED_TABLE,
                _where_equals("agent_id", agent_id) if agent_id else "source LIKE 'agent:%'",
            ),
            (
                "chunks",
                _where_equals("source", _note_source(agent_id))
                if agent_id
                else "source LIKE 'agent:%'",
            ),
        ):
            store = VectorStore(project_id, table_name=table_name)
            try:
                if not store._ensure_table():
                    continue
                table = store.db.open_table(store.table_name)
                columns = [c for c in ("text", "source", "created_at") if c in table.schema.names]
                rows = table.search().where(where).select(columns).limit(_NOTE_LIST_LIMIT).to_list()
            except Exception as e:
                logger.warning(f"Failed to get agent notes from {table_name}: {e}")
                continue
            notes.extend(
                {
                    "text": str(row.get("text", "")),
                    "source": str(row.get("source", "")),
                    "created_at": float(row.get("created_at") or 0.0),
                }
                for row in rows
            )
        notes.sort(key=lambda note: note["created_at"], reverse=True)
        return notes


agent_memory = AgentMemoryManager()
