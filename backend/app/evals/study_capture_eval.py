"""S1-S5: does a messaging study capture exactly what a professional researcher expects?

Professional-readiness review (2026-09-26), Area 2. Drives synthetic participants through the real
inbound path (`process_inbound_channel_message`, the code a Telegram/Slack/WhatsApp webhook runs)
and the real survey ingestion (`ingest_responses`), against ground truth fixed by construction:

  S1 attribution   stored answers whose question is the prompt the participant was actually shown
  S2 completeness  answers given (including the closing question) stored exactly once
  S3 consent       evidence stored for a participant before consent, or for one who declined,
                   was screened out, or after STOP
  S4 quota         participants who started after the target was reached and still had answers
                   stored (anyone who starts once the study is full is turned away)
  S5 re-sync       duplicate survey evidence units after three syncs of the same responses

Every number is an exact count (the harness is deterministic; seed fixed). It only uses functions
that exist on ``main`` too, so the same file measures before and after.

    python -m app.evals.study_capture_eval --out report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid

QUESTIONS = [
    "How do you share reports with your team today?",
    "What slows that down?",
    "What would you change first?",
]
CLOSING = "Is there anything else you would like to tell us?"
SCREENER = "Do you export reports every week?"
CHANNELS = ("telegram", "slack", "whatsapp")
PATHS = ("complete", "complete", "complete", "decline", "screened_out", "stop_after_1", "quiet_after_2")


def _participant_script(path: str, n: int) -> tuple[list[str], list[tuple[str, str]]]:
    """Messages a participant sends, and the (question, answer) pairs a researcher expects stored."""
    answers = [f"P{n} answer {i + 1} about exports" for i in range(len(QUESTIONS))]
    closing = f"P{n} closing remark"
    if path == "decline":
        return [f"hello from P{n}", "no", "actually exports are slow"], []
    if path == "screened_out":
        return [f"hi from P{n}", "yes", "no", "but I have opinions"], []
    base = [f"hi from P{n}", "yes", "yes"]
    if path == "stop_after_1":
        return base + [answers[0], "STOP", "one more thing"], [(QUESTIONS[0], answers[0])]
    if path == "quiet_after_2":
        return base + answers[:2], list(zip(QUESTIONS[:2], answers[:2], strict=True))
    expected = list(zip(QUESTIONS, answers, strict=True)) + [(CLOSING, closing)]
    return base + answers + [closing], expected


async def _seed(target: int) -> tuple[str, dict[str, str], str]:
    from app.models.channel_instance import ChannelInstance
    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.research_deployment import ResearchDeployment

    await init_db()
    project_id = str(uuid.uuid4())
    instances = {platform: str(uuid.uuid4()) for platform in CHANNELS}
    deployment_id = str(uuid.uuid4())
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"S1-S5 eval {project_id[:8]}"))
        for platform, instance_id in instances.items():
            db.add(
                ChannelInstance(
                    id=instance_id,
                    platform=platform,
                    name=f"eval {platform}",
                    config_json="{}",
                    project_id=project_id,
                )
            )
        db.add(
            ResearchDeployment(
                id=deployment_id,
                project_id=project_id,
                name="S1-S5 study",
                deployment_type="interview",
                questions_json=json.dumps([{"text": q} for q in QUESTIONS]),
                config_json=json.dumps(
                    {
                        "consent_required": True,
                        "screener": [{"text": SCREENER, "accept": ["yes"]}],
                        "closing_question": CLOSING,
                        "adaptive": False,
                    }
                ),
                channel_instance_ids_json=json.dumps(list(instances.values())),
                state="active",
                target_responses=target,
            )
        )
        await db.commit()
    return project_id, instances, deployment_id


async def _stored_answers(project_id: str) -> list[tuple[str, str, str]]:
    """(participant source_location, question, answer) for every stored nugget, in order."""
    from sqlalchemy import select

    from app.models.database import async_session
    from app.models.finding import Nugget

    async with async_session() as db:
        rows = (
            (
                await db.execute(
                    select(Nugget)
                    .where(Nugget.project_id == project_id)
                    .order_by(Nugget.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
    out = []
    for row in rows:
        text = row.text or ""
        question, answer = ("", text)
        if text.startswith("Q: ") and "\nA: " in text:
            question, answer = text[3:].split("\nA: ", 1)
        out.append((row.source_location or "", question, answer))
    return out


async def measure_channels(n_per_channel: int = 10, seed: int = 7) -> dict:
    from app.channels.base import IncomingMessage
    from app.services.inbound_processor import process_inbound_channel_message

    rng = random.Random(seed)
    participants = []
    for platform in CHANNELS:
        for i in range(n_per_channel):
            n = len(participants) + 1
            participants.append((f"p{n:02d}", platform, rng.choice(PATHS), n))
    completes = sum(1 for p in participants if p[2] == "complete")
    # Quota: leave room for all but the last three planned completions, so the last ones must be
    # turned away; they are expected to store nothing.
    target = max(1, completes - 3)
    project_id, instances, _ = await _seed(target)

    expected: dict[str, list[tuple[str, str]]] = {}
    finished = 0
    turned_away: set[str] = set()
    for sender, platform, path, n in participants:
        messages, wanted = _participant_script(path, n)
        if finished >= target:
            # The study is full when this participant starts: whatever they meant to do, they are
            # turned away and nothing they send is research data.
            turned_away.add(sender)
            wanted = []
        elif path == "complete":
            finished += 1
        expected[sender] = wanted
        for text in messages:
            await process_inbound_channel_message(
                IncomingMessage(
                    channel=platform,
                    channel_id=f"chat-{sender}",
                    sender_id=sender,
                    sender_name=sender,
                    text=text,
                    instance_id=instances[platform],
                    metadata={"content_type": "text"},
                )
            )

    stored = await _stored_answers(project_id)
    by_sender: dict[str, list[tuple[str, str]]] = {}
    from sqlalchemy import select

    from app.models.channel_conversation import ChannelConversation
    from app.models.database import async_session

    async with async_session() as db:
        conversations = (
            (
                await db.execute(
                    select(ChannelConversation).where(ChannelConversation.project_id == project_id)
                )
            )
            .scalars()
            .all()
        )
    conv_to_sender = {c.id: c.participant_id for c in conversations}
    for location, question, answer in stored:
        conv = location.split(":conv:", 1)[1].split(":", 1)[0] if ":conv:" in location else ""
        by_sender.setdefault(conv_to_sender.get(conv, "?"), []).append((question, answer))

    stored_total = len(stored)
    correct = misattributed = not_research_data = 0
    given = sum(len(v) for v in expected.values())
    stored_once = 0
    for sender, pairs in by_sender.items():
        wanted = expected.get(sender, [])
        wanted_answers = {answer for _, answer in wanted}
        for question, answer in pairs:
            if (question, answer) in wanted:
                correct += 1
            elif answer in wanted_answers:
                misattributed += 1  # a real answer filed under a question the participant never saw
            else:
                # a greeting, consent or screener reply, text from someone who declined or was
                # turned away, or anything sent after STOP
                not_research_data += 1
    missing = []
    for sender, wanted in expected.items():
        pairs = by_sender.get(sender, [])
        stored_once += sum(1 for pair in wanted if pairs.count(pair) == 1)
        path = next(p[2] for p in participants if p[0] == sender)
        missing += [
            {"participant": sender, "path": path, "question": q, "times_stored": pairs.count((q, a))}
            for q, a in wanted
            if pairs.count((q, a)) != 1
        ]
    quota_overshoot = sum(1 for sender in turned_away if by_sender.get(sender))
    return {
        "participants": len(participants),
        "paths": {path: sum(1 for p in participants if p[2] == path) for path in sorted(set(PATHS))},
        "target_responses": target,
        "turned_away_by_quota": len(turned_away),
        "S1_attribution": {
            "correct": correct,
            "stored": stored_total,
            "share": round(correct / stored_total, 4) if stored_total else None,
            "misattributed": misattributed,
        },
        "S2_completeness": {
            "stored_exactly_once": stored_once,
            "given": given,
            "share": round(stored_once / given, 4) if given else None,
            "not_stored_exactly_once": missing,
        },
        "S3_non_research_data_stored": not_research_data,
        "S4_quota_overshoot": quota_overshoot,
    }


async def measure_survey_resync(syncs: int = 3) -> dict:
    from sqlalchemy import func, select

    from app.models.database import async_session, init_db
    from app.models.project import Project
    from app.models.research_validity import EvidenceUnit
    from app.models.survey_integration import SurveyIntegration, SurveyLink
    from app.services.survey_ingestion import ingest_responses

    await init_db()
    project_id = str(uuid.uuid4())
    integration = SurveyIntegration(
        id=str(uuid.uuid4()), platform="typeform", name="eval", config_json="{}",
        project_id=project_id,
    )
    link = SurveyLink(
        id=str(uuid.uuid4()), integration_id=integration.id, project_id=project_id,
        external_survey_id="form-eval", external_survey_name="S5 survey",
    )
    async with async_session() as db:
        db.add(Project(id=project_id, name="S5 eval"))
        db.add(integration)
        db.add(link)
        await db.commit()
    responses = [
        {"id": f"r{i}", "answers": [{"question": q, "answer": f"r{i} says {j}"}
                                    for j, q in enumerate(QUESTIONS)]}
        for i in range(30)
    ]
    counts = []
    for _ in range(syncs):
        async with async_session() as db:
            fresh = await db.get(SurveyLink, link.id)
            await ingest_responses(db, fresh, responses, project_id)
        async with async_session() as db:
            counts.append(
                await db.scalar(
                    select(func.count()).select_from(EvidenceUnit).where(
                        EvidenceUnit.project_id == project_id
                    )
                )
            )
    async with async_session() as db:
        final_link = await db.get(SurveyLink, link.id)
    return {
        "responses": len(responses),
        "evidence_units_after_each_sync": counts,
        "S5_duplicate_units": counts[-1] - counts[0],
        "response_count_after": final_link.response_count,
    }


async def run() -> dict:
    return {
        "measure": "S1-S5 study capture (professional-readiness review, Area 2)",
        "channels": await measure_channels(),
        "survey": await measure_survey_resync(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    import app.core.agentic  # noqa: F401  (import-order guard for the app's module graph)

    report = asyncio.run(run())
    text = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
