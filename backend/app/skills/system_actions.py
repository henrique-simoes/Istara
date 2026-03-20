"""System Action Tools — every ReClaw operation as an LLM-callable tool.

These tools allow agents to perform any user-level operation through chat:
creating tasks, searching documents, attaching files, moving tasks, querying
findings, and delegating work to other agents via A2A.

Architecture follows the state-of-the-art pattern from OpenClaw/Anthropic:
tools are defined as structured schemas, injected into the system prompt,
and the LLM decides which to call based on the conversation context.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import async_session
from app.models.task import Task, TaskStatus
from app.models.project import Project
from app.models.document import Document
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.agent import Agent

logger = logging.getLogger(__name__)


# ── Tool Definitions ──────────────────────────────────────────────

SYSTEM_TOOLS = [
    {
        "name": "create_task",
        "description": "Create a new research task on the Kanban board. Use when the user asks to start work, analyze something, or run a research skill. Ask for missing required fields conversationally.",
        "parameters": {
            "title": {"type": "string", "required": True, "description": "Clear task title describing what to do"},
            "description": {"type": "string", "required": False, "description": "Detailed description of the task"},
            "skill_name": {"type": "string", "required": False, "description": "UXR skill to use (e.g., 'user-interviews', 'competitive-analysis'). Leave empty for auto-detect."},
            "priority": {"type": "string", "required": False, "description": "urgent, high, medium, or low. Default: medium"},
            "instructions": {"type": "string", "required": False, "description": "Specific instructions for the agent executing this task"},
            "input_document_ids": {"type": "array", "required": False, "description": "List of document IDs to attach as inputs"},
            "urls": {"type": "array", "required": False, "description": "List of URLs for the agent to fetch and analyze"},
            "user_context": {"type": "string", "required": False, "description": "Additional context or constraints"},
        },
    },
    {
        "name": "search_documents",
        "description": "Search for documents in the current project by title, content, tags, or phase. Use when the user asks to find, locate, or look up a document or file.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Search query (matches title, description, content, tags, file name)"},
            "phase": {"type": "string", "required": False, "description": "Filter by Double Diamond phase: discover, define, develop, deliver"},
            "tag": {"type": "string", "required": False, "description": "Filter by tag"},
            "source": {"type": "string", "required": False, "description": "Filter by source: user_upload, agent_output, task_output, project_file, external"},
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks in the current project, optionally filtered by status. Use when the user asks about task status, what's in progress, or the work queue.",
        "parameters": {
            "status": {"type": "string", "required": False, "description": "Filter by status: backlog, in_progress, in_review, done"},
        },
    },
    {
        "name": "move_task",
        "description": "Move a task to a different Kanban column. Use when the user asks to start, pause, complete, or change a task's status.",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "The task ID to move"},
            "status": {"type": "string", "required": True, "description": "New status: backlog, in_progress, in_review, done"},
        },
    },
    {
        "name": "attach_document",
        "description": "Attach a document to a task as input or output. Use when the user says to use a specific file for a task, or to link a result to a task.",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "The task ID"},
            "document_id": {"type": "string", "required": True, "description": "The document ID to attach"},
            "direction": {"type": "string", "required": False, "description": "'input' (source material) or 'output' (produced result). Default: input"},
        },
    },
    {
        "name": "search_findings",
        "description": "Search research findings (nuggets, facts, insights, recommendations) in the project. Use when the user asks about research results, what was found, key insights, etc.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Search text to match against finding content"},
            "finding_type": {"type": "string", "required": False, "description": "Filter by type: nugget, fact, insight, recommendation"},
            "phase": {"type": "string", "required": False, "description": "Filter by Double Diamond phase"},
        },
    },
    {
        "name": "list_project_files",
        "description": "List all files in the project folder. Use when the user asks what files are available, what's been uploaded, or references a file by partial name.",
        "parameters": {},
    },
    {
        "name": "assign_agent",
        "description": "Assign an agent to a task. Use when the user asks to delegate work or assign a specific agent.",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "The task to assign"},
            "agent_id": {"type": "string", "required": True, "description": "The agent ID to assign (e.g., 'reclaw-main')"},
        },
    },
    {
        "name": "send_agent_message",
        "description": "Send a message to another agent via A2A protocol. Use for delegation, status updates, or inter-agent coordination.",
        "parameters": {
            "to_agent_id": {"type": "string", "required": True, "description": "Target agent ID"},
            "message_type": {"type": "string", "required": False, "description": "Message type: request, report, alert, delegate. Default: request"},
            "content": {"type": "string", "required": True, "description": "Message content"},
        },
    },
    {
        "name": "get_document_content",
        "description": "Get the text content of a specific document. Use when the user asks to read, view, or get details from a document.",
        "parameters": {
            "document_id": {"type": "string", "required": True, "description": "The document ID to read"},
        },
    },
    {
        "name": "search_memory",
        "description": "Search the project's memory and knowledge base using RAG. Use when the user asks to recall something, find information from past conversations, or query the knowledge base.",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "The search query"},
            "top_k": {"type": "integer", "required": False, "description": "Number of results (default 5)"},
        },
    },
    {
        "name": "update_task",
        "description": "Update fields on an existing task. Use when the user wants to change a task's title, description, priority, instructions, or other properties.",
        "parameters": {
            "task_id": {"type": "string", "required": True, "description": "The task ID to update"},
            "title": {"type": "string", "required": False, "description": "New title"},
            "description": {"type": "string", "required": False, "description": "New description"},
            "priority": {"type": "string", "required": False, "description": "New priority: urgent, high, medium, low"},
            "instructions": {"type": "string", "required": False, "description": "New specific instructions"},
            "skill_name": {"type": "string", "required": False, "description": "Change the assigned skill"},
        },
    },
    {
        "name": "sync_project_documents",
        "description": "Scan the project folder for new or untracked files and register them as documents. Use when the user mentions adding files to the folder, or when they want to refresh the document list.",
        "parameters": {},
    },
]


def build_tools_prompt() -> str:
    """Build the tools section for the system prompt.

    Uses a compact format to minimize token usage for local models:
    one-line description + parameter list per tool.
    """
    lines = [
        "## Available Tools",
        "",
        "You can perform actions in ReClaw by responding with a tool call in this exact JSON format:",
        "```json",
        '{"tool": "tool_name", "params": {"param1": "value1"}}',
        "```",
        "",
        "After executing the tool, I will show you the result. You can then call another tool or respond to the user.",
        "Only call a tool when the user's request requires an action. For general conversation, respond normally.",
        "When creating a task, if the user hasn't provided all needed information, ask them conversationally before calling the tool.",
        "",
        "### Tools:",
        "",
    ]

    for tool in SYSTEM_TOOLS:
        params_desc = []
        for pname, pinfo in tool["parameters"].items():
            req = " (required)" if pinfo.get("required") else ""
            params_desc.append(f"  - {pname}: {pinfo['description']}{req}")

        lines.append(f"**{tool['name']}** — {tool['description']}")
        if params_desc:
            lines.extend(params_desc)
        lines.append("")

    return "\n".join(lines)


# ── Tool Execution ────────────────────────────────────────────────


async def execute_tool(
    tool_name: str,
    params: dict[str, Any],
    project_id: str,
    agent_id: str = "reclaw-main",
) -> dict[str, Any]:
    """Execute a system action tool and return the result.

    Returns a dict with 'success' bool and 'result' or 'error' string.
    """
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    try:
        result = await executor(params, project_id, agent_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return {"success": False, "error": str(e)}


async def _exec_create_task(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(
            select(Task.position)
            .where(Task.project_id == project_id)
            .order_by(Task.position.desc())
            .limit(1)
        )
        max_pos = result.scalar() or 0

        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=params["title"],
            description=params.get("description", ""),
            skill_name=params.get("skill_name", ""),
            priority=params.get("priority", "medium"),
            instructions=params.get("instructions", ""),
            user_context=params.get("user_context", ""),
            input_document_ids=json.dumps(params.get("input_document_ids", [])),
            output_document_ids=json.dumps([]),
            urls=json.dumps(params.get("urls", [])),
            position=max_pos + 1,
        )
        db.add(task)
        await db.commit()

        # Wake the orchestrator
        from app.core.agent import agent as orchestrator

        orchestrator.wake()

        return f"Task created: '{task.title}' (ID: {task.id}, priority: {task.priority}, status: backlog)"


async def _exec_search_documents(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        query = select(Document).where(Document.project_id == project_id)

        search = params.get("query", "")
        if search:
            like = f"%{search}%"
            query = query.where(
                (Document.title.ilike(like))
                | (Document.description.ilike(like))
                | (Document.content_text.ilike(like))
                | (Document.tags.ilike(like))
                | (Document.file_name.ilike(like))
            )

        if params.get("phase"):
            query = query.where(Document.phase == params["phase"])
        if params.get("tag"):
            query = query.where(Document.tags.ilike(f'%{params["tag"]}%'))
        if params.get("source"):
            query = query.where(Document.source == params["source"])

        result = await db.execute(query.order_by(Document.created_at.desc()).limit(10))
        docs = result.scalars().all()

        if not docs:
            return f"No documents found matching '{search}' in this project."

        lines = [f"Found {len(docs)} document(s):"]
        for doc in docs:
            tags_str = ""
            try:
                tags = json.loads(doc.tags or "[]")
                if tags:
                    tags_str = f" [tags: {', '.join(tags[:3])}]"
            except Exception:
                pass
            lines.append(
                f"- **{doc.title}** (ID: {doc.id}, type: {doc.file_type or 'unknown'}, "
                f"phase: {doc.phase or 'none'}, source: {doc.source.value if doc.source else 'unknown'}){tags_str}"
            )
        return "\n".join(lines)


async def _exec_list_tasks(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        query = select(Task).where(Task.project_id == project_id)
        if params.get("status"):
            query = query.where(Task.status == TaskStatus(params["status"]))

        result = await db.execute(query.order_by(Task.position, Task.created_at))
        tasks = result.scalars().all()

        if not tasks:
            status_filter = f" with status '{params['status']}'" if params.get("status") else ""
            return f"No tasks found{status_filter} in this project."

        lines = [f"Found {len(tasks)} task(s):"]
        for t in tasks:
            agent_str = f", agent: {t.agent_id}" if t.agent_id else ""
            lines.append(
                f"- [{t.status.value.upper()}] **{t.title}** (ID: {t.id}, "
                f"priority: {t.priority}, progress: {int(t.progress * 100)}%{agent_str})"
            )
        return "\n".join(lines)


async def _exec_move_task(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(select(Task).where(Task.id == params["task_id"]))
        task = result.scalar_one_or_none()
        if not task:
            return f"Task not found: {params['task_id']}"

        old_status = task.status.value
        task.status = TaskStatus(params["status"])
        await db.commit()
        return f"Task '{task.title}' moved from {old_status} to {params['status']}."


async def _exec_attach_document(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(select(Task).where(Task.id == params["task_id"]))
        task = result.scalar_one_or_none()
        if not task:
            return f"Task not found: {params['task_id']}"

        doc_result = await db.execute(select(Document).where(Document.id == params["document_id"]))
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return f"Document not found: {params['document_id']}"

        direction = params.get("direction", "input")
        if direction == "output":
            ids = task.get_output_document_ids()
            if params["document_id"] not in ids:
                ids.append(params["document_id"])
                task.set_output_document_ids(ids)
        else:
            ids = task.get_input_document_ids()
            if params["document_id"] not in ids:
                ids.append(params["document_id"])
                task.set_input_document_ids(ids)

        # Also update the document's task_id reference
        doc.task_id = params["task_id"]
        await db.commit()
        return f"Document '{doc.title}' attached to task '{task.title}' as {direction}."


async def _exec_search_findings(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        search = params.get("query", "")
        finding_type = params.get("finding_type")
        phase = params.get("phase")
        results = []

        # Search across all finding types unless filtered
        types_to_search = []
        if not finding_type or finding_type == "nugget":
            types_to_search.append(("Nugget", Nugget))
        if not finding_type or finding_type == "fact":
            types_to_search.append(("Fact", Fact))
        if not finding_type or finding_type == "insight":
            types_to_search.append(("Insight", Insight))
        if not finding_type or finding_type == "recommendation":
            types_to_search.append(("Recommendation", Recommendation))

        for type_name, model_cls in types_to_search:
            query = select(model_cls).where(model_cls.project_id == project_id)
            if search:
                query = query.where(model_cls.text.ilike(f"%{search}%"))
            if phase and hasattr(model_cls, "phase"):
                query = query.where(model_cls.phase == phase)

            res = await db.execute(query.limit(5))
            for item in res.scalars().all():
                text_preview = item.text[:150] + "..." if len(item.text) > 150 else item.text
                results.append(f"- [{type_name}] {text_preview} (ID: {item.id})")

        if not results:
            return f"No findings found matching '{search}'."
        return f"Found {len(results)} finding(s):\n" + "\n".join(results)


async def _exec_list_project_files(params: dict, project_id: str, agent_id: str) -> str:
    upload_dir = Path(settings.upload_dir) / project_id
    if not upload_dir.exists():
        return "No project folder found. Upload files to get started."

    files = [f for f in upload_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        return "The project folder is empty."

    lines = [f"Found {len(files)} file(s) in the project folder:"]
    for f in sorted(files, key=lambda x: x.name):
        size_kb = f.stat().st_size / 1024
        lines.append(f"- {f.name} ({size_kb:.1f} KB, type: {f.suffix})")
    return "\n".join(lines)


async def _exec_assign_agent(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(select(Task).where(Task.id == params["task_id"]))
        task = result.scalar_one_or_none()
        if not task:
            return f"Task not found: {params['task_id']}"

        task.agent_id = params["agent_id"]
        await db.commit()

        from app.core.agent import agent as orchestrator

        orchestrator.wake()

        return f"Task '{task.title}' assigned to agent '{params['agent_id']}'. Agent woken to process."


async def _exec_send_agent_message(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        from app.services.a2a import send_message

        await send_message(
            db=db,
            from_agent_id=agent_id,
            to_agent_id=params["to_agent_id"],
            message_type=params.get("message_type", "request"),
            content=params["content"],
            metadata={"project_id": project_id},
        )
        return f"Message sent to agent '{params['to_agent_id']}': {params['content'][:100]}"


async def _exec_get_document_content(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(select(Document).where(Document.id == params["document_id"]))
        doc = result.scalar_one_or_none()
        if not doc:
            return f"Document not found: {params['document_id']}"

        content = doc.content_text or doc.content_preview or ""
        if not content and doc.file_path:
            try:
                path = Path(doc.file_path)
                if path.exists() and path.suffix in {".txt", ".md", ".csv"}:
                    content = path.read_text(errors="replace")[:5000]
            except Exception:
                pass

        if not content:
            return f"Document '{doc.title}' exists but has no readable text content (type: {doc.file_type})."

        preview = content[:3000] + "..." if len(content) > 3000 else content
        return (
            f"**{doc.title}** (phase: {doc.phase or 'none'}, "
            f"source: {doc.source.value if doc.source else 'unknown'})\n\n{preview}"
        )


async def _exec_search_memory(params: dict, project_id: str, agent_id: str) -> str:
    from app.core.rag import retrieve_context

    rag = await retrieve_context(project_id, params["query"], top_k=params.get("top_k", 5))

    if not rag.has_context:
        return f"No relevant information found in the knowledge base for: '{params['query']}'"

    lines = [f"Found {len(rag.retrieved)} relevant passage(s):"]
    for r in rag.retrieved:
        preview = r.text[:200] + "..." if len(r.text) > 200 else r.text
        lines.append(f"- [{r.source}] (score: {r.score:.2f}) {preview}")
    return "\n".join(lines)


async def _exec_update_task(params: dict, project_id: str, agent_id: str) -> str:
    async with async_session() as db:
        result = await db.execute(select(Task).where(Task.id == params["task_id"]))
        task = result.scalar_one_or_none()
        if not task:
            return f"Task not found: {params['task_id']}"

        updated_fields = []
        for field in ("title", "description", "priority", "instructions", "skill_name"):
            if field in params and params[field] is not None:
                setattr(task, field, params[field])
                updated_fields.append(field)

        await db.commit()
        return f"Task '{task.title}' updated: {', '.join(updated_fields)}."


async def _exec_sync_project_documents(params: dict, project_id: str, agent_id: str) -> str:
    """Trigger a document sync for the project folder."""
    upload_dir = Path(settings.upload_dir) / project_id
    if not upload_dir.exists():
        return "No project folder found."

    async with async_session() as db:
        # Find files not yet registered as documents
        files = [f for f in upload_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

        existing_result = await db.execute(
            select(Document.file_name).where(Document.project_id == project_id)
        )
        existing_names = {r for r in existing_result.scalars().all()}

        new_count = 0
        for f in files:
            if f.name not in existing_names:
                doc = Document(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=f.stem.replace("-", " ").replace("_", " ").title(),
                    file_name=f.name,
                    file_path=str(f),
                    file_type=f.suffix,
                    file_size=f.stat().st_size,
                    source="project_file",
                    status="ready",
                )
                db.add(doc)
                new_count += 1

        if new_count:
            await db.commit()

        return f"Synced project folder: {new_count} new document(s) registered, {len(files)} total files."


# ── Executor Registry ─────────────────────────────────────────────

TOOL_EXECUTORS = {
    "create_task": _exec_create_task,
    "search_documents": _exec_search_documents,
    "list_tasks": _exec_list_tasks,
    "move_task": _exec_move_task,
    "attach_document": _exec_attach_document,
    "search_findings": _exec_search_findings,
    "list_project_files": _exec_list_project_files,
    "assign_agent": _exec_assign_agent,
    "send_agent_message": _exec_send_agent_message,
    "get_document_content": _exec_get_document_content,
    "search_memory": _exec_search_memory,
    "update_task": _exec_update_task,
    "sync_project_documents": _exec_sync_project_documents,
}
