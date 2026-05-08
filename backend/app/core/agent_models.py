"""Data models and shared helpers for the Istara agent orchestrator."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket import (
    broadcast_agent_status,
    broadcast_agent_thinking,
    broadcast_finding_created,
    broadcast_plan_progress,
    broadcast_suggestion,
    broadcast_task_progress,
    broadcast_task_queue_update,
)
from app.config import settings
from app.core.agent_hooks import agent_hooks
from app.core.checkpoint import complete_checkpoint, create_checkpoint, update_checkpoint
from app.core.context_hierarchy import context_hierarchy
from app.core.datetime_utils import ensure_utc
from app.core.embeddings import TextChunk
from app.core.ollama import ollama
from app.core.rag import ingest_chunks, retrieve_context
from app.core.resource_governor import governor
from app.core.self_check import Confidence, verify_claim
from app.core.steering import steering_manager
from app.core.telemetry import telemetry_recorder
from app.models.agent import Agent, AgentState
from app.models.database import async_session
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.skills.base import SkillInput, SkillOutput
from app.skills.registry import registry
from app.skills.skill_manager import skill_manager

_META_SKILL_SIMILARITY_THRESHOLD = 0.6


def _resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


@dataclass
class ResearchStep:
    """A single step in a research plan."""

    id: str
    description: str
    skill_name: str | None = None
    status: str = "pending"  # pending | executing | completed | failed
    result: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class ResearchPlan:
    """A decomposed research plan with ordered steps."""

    question: str
    steps: list[ResearchStep] = field(default_factory=list)
    past_steps: list[ResearchStep] = field(default_factory=list)
    status: str = "planning"  # planning | executing | replanning | complete

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "status": self.status,
            "steps": [
                {
                    "id": s.id,
                    "desc": s.description,
                    "skill": s.skill_name,
                    "status": s.status,
                    "result": s.result[:200],
                    "depends_on": s.depends_on,
                }
                for s in self.steps
            ],
            "completed": [
                {"id": s.id, "desc": s.description, "status": s.status} for s in self.past_steps
            ],
        }
