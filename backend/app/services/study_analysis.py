"""Analyse what a study collected, through the Research Spine (D-7).

Answers captured from a messaging study or a survey are raw evidence, not findings. To analyse
them a researcher gets what an interview upload gets: the answers become one pseudonymised
transcript document in the project (evidence units, provenance-carrying chunks), and a Kanban
task runs an analysis skill on exactly that document. The skill's nuggets are grounded in the
transcript's spans, coded by the governed coding run, reviewed, and reach a report only through
an approved Done task.

Each answer is one speaker turn, ``P01: [Asked: <question>] <answer>``, so a coder sees the
question as context inside the unit and a quoted answer is an exact substring of the document.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.task import Task, TaskStatus

# Skill that analyses each kind of study.
ANALYSIS_SKILL = {
    "interview": "user-interviews",
    "diary_study": "diary-studies",
    "survey": "thematic-analysis",
}


def _slug(text: str) -> str:
    kept = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text.strip().lower())
    return "-".join(part for part in kept.split("-") if part)[:60] or "study"


def transcript_text(title: str, participants: list[tuple[str, str, list[tuple[str, str]]]]) -> str:
    """Render participants as ``(label, note, [(question, answer), ...])`` speaker turns."""
    lines = [
        f"# Study responses: {title}",
        "",
        f"Exported {datetime.now(UTC).date().isoformat()}. Participants are pseudonymised; "
        "only their answers are included, each with the question it answered.",
    ]
    for label, note, answers in participants:
        if not answers:
            continue
        lines += ["", f"## {label}" + (f" ({note})" if note else "")]
        for question, answer in answers:
            flat = " ".join(str(answer).split())
            lines += ["", f"{label}: [Asked: {' '.join(str(question).split())}] {flat}"]
    return "\n".join(lines) + "\n"


async def ingest_text_document(
    db: AsyncSession,
    project_id: str,
    *,
    file_name: str,
    text: str,
    tags: list[str],
) -> Document:
    """Store a text source the way an upload is stored: file, document, evidence units, chunks."""
    from app.core.file_encryption import encrypt_file_in_place, protect_document_text
    from app.core.file_processor import process_file
    from app.services.research_validity_service import (
        persist_document_source_evidence_units,
        record_source_evidence_unit_telemetry,
    )
    from app.services.retrieval_provenance import index_document_source_chunks

    folder = Path(settings.upload_dir) / project_id
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{uuid.uuid4()}.md"
    file_path.write_text(text, encoding="utf-8")
    result = process_file(file_path)
    content_text = "\n\n".join(c.text for c in result.chunks) if result.chunks else text
    document = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=file_name,
        file_name=file_name,
        file_path=str(file_path),
        file_type=".md",
        file_size=len(text.encode("utf-8")),
        source=DocumentSource.EXTERNAL,
        status=DocumentStatus.READY,
        tags=json.dumps(tags),
        content_text=protect_document_text(content_text),
        content_preview=content_text[:500],
    )
    db.add(document)
    units = await persist_document_source_evidence_units(
        db,
        project_id=project_id,
        document_id=document.id,
        source_text=content_text,
        source_location=file_name,
        source_document_id=document.id,
        source_type="study_responses",
        method="study_export",
        phase=document.phase,
        version=1,
        metadata={"file_name": file_name, "ingestion_surface": "study_analysis"},
    )
    await db.commit()
    await record_source_evidence_unit_telemetry(project_id=project_id, units=units)
    if result.chunks:
        await index_document_source_chunks(
            project_id,
            result.chunks,
            document_id=document.id,
            units=units,
            document_text=content_text,
        )
    encrypt_file_in_place(file_path)
    return document


async def _create_analysis_task(
    db: AsyncSession,
    project_id: str,
    *,
    title: str,
    skill_name: str,
    document: Document,
    description: str,
) -> Task:
    from sqlalchemy import func

    max_pos = (
        await db.scalar(select(func.max(Task.position)).where(Task.project_id == project_id)) or 0
    )
    task = Task(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=title,
        description=description,
        skill_name=skill_name,
        agent_id="istara-main",
        priority="medium",
        status=TaskStatus.BACKLOG,
        position=max_pos + 1,
        input_document_ids=json.dumps([document.id]),
    )
    db.add(task)
    await db.commit()
    try:
        from app.core.agent import agent as agent_orchestrator

        agent_orchestrator.wake()
    except Exception:
        pass
    return task


async def analyse_deployment(db: AsyncSession, deployment) -> dict:
    """Turn a deployment's stored answers into a transcript and an analysis task."""
    from app.services.deployment_service import export_deployment_rows

    rows = await export_deployment_rows(db, deployment)
    by_participant: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    for row in rows:
        label = row["participant"]
        note = ", ".join(v for v in (row.get("channel"), row.get("conversation_state")) if v)
        entry = by_participant.setdefault(label, (note, []))
        if row.get("answer"):
            entry[1].append((row.get("question") or "", row["answer"]))
    participants = [(label, note, answers) for label, (note, answers) in by_participant.items()]
    answered = sum(len(answers) for _, _, answers in participants)
    if answered == 0:
        return {"status": "nothing_to_analyse", "answers": 0}
    name = f"{_slug(deployment.name)}-responses.md"
    document = await ingest_text_document(
        db,
        deployment.project_id,
        file_name=name,
        text=transcript_text(deployment.name, participants),
        tags=["study-responses", f"deployment:{deployment.id}"],
    )
    skill = ANALYSIS_SKILL.get(deployment.deployment_type, "thematic-analysis")
    task = await _create_analysis_task(
        db,
        deployment.project_id,
        title=f"Analyse responses: {deployment.name}",
        skill_name=skill,
        document=document,
        description=(
            f"Analyse {answered} answers from {len(participants)} participants of "
            f"'{deployment.name}' ({name}). Findings stay provisional until coded, reconciled "
            "and approved."
        ),
    )
    return {
        "status": "created",
        "answers": answered,
        "participants": sum(1 for _, _, a in participants if a),
        "document_id": document.id,
        "task_id": task.id,
        "skill_name": skill,
    }


async def analyse_survey_link(db: AsyncSession, link, answers: list[dict]) -> dict:
    """Turn a survey link's stored answers (``export`` rows) into a transcript and a task."""
    by_response: dict[str, list[tuple[str, str]]] = {}
    for index, row in enumerate(answers):
        key = row.get("response_id") or f"anonymous-{index + 1}"
        by_response.setdefault(key, []).append((row.get("question") or "", row.get("answer", "")))
    participants = [
        (f"R{number:02d}", f"response {key}", pairs)
        for number, (key, pairs) in enumerate(by_response.items(), start=1)
    ]
    answered = sum(len(pairs) for _, _, pairs in participants)
    if answered == 0:
        return {"status": "nothing_to_analyse", "answers": 0}
    survey_name = link.external_survey_name or link.external_survey_id
    name = f"{_slug(survey_name)}-survey-responses.md"
    document = await ingest_text_document(
        db,
        link.project_id,
        file_name=name,
        text=transcript_text(survey_name, participants),
        tags=["survey-responses", f"survey-link:{link.id}"],
    )
    task = await _create_analysis_task(
        db,
        link.project_id,
        title=f"Analyse survey: {survey_name}",
        skill_name=ANALYSIS_SKILL["survey"],
        document=document,
        description=(
            f"Analyse {answered} answers from {len(participants)} responses to '{survey_name}' "
            f"({name}). Findings stay provisional until coded, reconciled and approved."
        ),
    )
    return {
        "status": "created",
        "answers": answered,
        "participants": len(participants),
        "document_id": document.id,
        "task_id": task.id,
        "skill_name": ANALYSIS_SKILL["survey"],
    }
