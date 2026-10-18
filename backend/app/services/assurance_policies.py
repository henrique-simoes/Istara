"""Read a project's stored assurance mode (``project_assurance_policies``).

Kept apart from the validation services so that callers on the Research Spine side (decider triage)
can read the mode without importing the LLM validation stack.
"""

from __future__ import annotations

from app.core.assurance import ProjectAssurance


async def load_project_assurance(project_id: str) -> ProjectAssurance:
    """The project's stored choice, or ``auto`` (the pre-modes behaviour) when it has none."""
    from app.models.assurance_policy import ProjectAssurancePolicy
    from app.models.database import async_session

    async with async_session() as session:
        row = await session.get(ProjectAssurancePolicy, project_id)
    if row is None:
        return ProjectAssurance()
    return ProjectAssurance(
        mode=row.mode,
        llm_method=row.llm_method,
        llm_judges=row.llm_judges,
        decider_endpoint_ids=tuple(row.decider_endpoint_ids()),
    )
