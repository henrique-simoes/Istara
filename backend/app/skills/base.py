"""Base skill class — all UXR skills inherit from this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SkillPhase(str, Enum):
    """Double Diamond phase a skill belongs to."""

    DISCOVER = "discover"
    DEFINE = "define"
    DEVELOP = "develop"
    DELIVER = "deliver"


class SkillType(str, Enum):
    """Whether the skill is qualitative, quantitative, or mixed."""

    QUALITATIVE = "qualitative"
    QUANTITATIVE = "quantitative"
    MIXED = "mixed"


@dataclass
class SkillInput:
    """Input data for a skill execution."""

    project_id: str
    task_id: str | None = None
    files: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    user_context: str = ""
    project_context: str = ""
    company_context: str = ""
    model: str | None = None
    temperature: float | None = None


@dataclass
class SkillOutput:
    """Output from a skill execution.

    Skill outputs are visible candidate research artifacts. They are not
    reportable evidence until the Research Spine accepts/reconciles them from
    source-grounded coding, reliability checks, and human Done-task gates.
    """

    success: bool
    summary: str
    nuggets: list[dict] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    insights: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)  # filename → content
    suggestions: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    json_success: bool = True  # Track if LLM output was valid JSON
    research_validity: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.mark_research_artifacts_candidate()

    def mark_research_artifacts_candidate(self) -> None:
        """Mark skill-created research artifacts as provisional by default."""
        previous_validity = (
            self.research_validity if isinstance(self.research_validity, dict) else {}
        )
        self.research_validity = {
            **previous_validity,
            "status": "provisional",
            "artifact_state": "skill_output_candidate",
            "report_allowed": False,
            "promotion_required": ("source_grounded_coding_reliability_reconciliation_done_gate"),
        }
        artifact_states = {
            "nuggets": "candidate_atom",
            "facts": "candidate_fact",
            "insights": "candidate_insight",
            "recommendations": "candidate_recommendation",
        }
        for collection_name, artifact_state in artifact_states.items():
            for item in getattr(self, collection_name, []) or []:
                if not isinstance(item, dict):
                    continue
                item.setdefault("artifact_state", artifact_state)
                validity = item.get("research_validity")
                if not isinstance(validity, dict):
                    validity = {}
                item["research_validity"] = {
                    **validity,
                    "status": "provisional",
                    "artifact_state": artifact_state,
                    "report_allowed": False,
                    "promotion_required": (
                        "source_grounded_coding_reliability_reconciliation_done_gate"
                    ),
                }


class BaseSkill(ABC):
    """Abstract base class for all UXR skills.

    Every skill must implement:
    - name, description, phase, skill_type properties
    - plan(): Generate a research plan
    - execute(): Run the skill on input data
    - validate_output(): Check the output for quality
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier (e.g., 'user-interviews')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'User Interviews')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """What this skill does."""
        ...

    @property
    @abstractmethod
    def phase(self) -> SkillPhase:
        """Which Double Diamond phase this skill belongs to."""
        ...

    @property
    @abstractmethod
    def skill_type(self) -> SkillType:
        """Whether this is qualitative, quantitative, or mixed."""
        ...

    @property
    def version(self) -> str:
        """Skill version for tracking updates."""
        return "1.0.0"

    @abstractmethod
    async def plan(self, skill_input: SkillInput) -> dict:
        """Generate a research plan for this skill.

        Args:
            skill_input: Input context and parameters.

        Returns:
            A plan dict with steps, estimated time, required inputs, etc.
        """
        ...

    @abstractmethod
    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        """Execute the skill on the given input.

        Args:
            skill_input: Input data, files, and context.

        Returns:
            SkillOutput with findings, artifacts, and suggestions.
        """
        ...

    async def validate_output(self, output: SkillOutput) -> list[str]:
        """Validate the skill output for quality issues.

        Checks: summary presence, candidate evidence proposal, source attribution,
        code-ready candidate quality, and provisional evidence chain integrity.

        Args:
            output: The output to validate.

        Returns:
            List of warning messages (empty if all good).
        """
        warnings = []

        if not output.summary:
            warnings.append("No summary generated.")

        if not output.nuggets and not output.facts:
            warnings.append("No candidate evidence (nuggets or facts) proposed.")

        for nugget in output.nuggets:
            if not nugget.get("source"):
                warnings.append(
                    f"Candidate nugget missing source: '{nugget.get('text', '')[:50]}...'"
                )
            text = nugget.get("text", "")
            word_count = len(text.split())
            if word_count < 3:
                warnings.append(
                    f"Candidate nugget too short ({word_count} words): '{text[:50]}...'"
                )
            if not nugget.get("tags"):
                warnings.append(f"Candidate nugget missing tags/codes: '{text[:50]}...'")

        # Evidence chain integrity
        if output.insights and not output.facts and not output.nuggets:
            warnings.append(
                "Candidate insights generated without supporting nuggets or facts (broken provisional evidence chain)."
            )
        if output.recommendations and not output.insights:
            warnings.append(
                "Candidate recommendations generated without supporting insights (broken provisional evidence chain)."
            )

        # Confidence score bounds
        for finding_type in ["nuggets", "facts", "insights", "recommendations"]:
            for f in getattr(output, finding_type, []):
                conf = f.get("confidence")
                if conf is not None and isinstance(conf, (int, float)):
                    if conf < 0 or conf > 1:
                        warnings.append(
                            f"{finding_type} has invalid confidence {conf} (must be 0-1): '{f.get('text', '')[:40]}...'"
                        )

        # Source attribution on facts and insights
        for fact in output.facts:
            if not fact.get("nugget_ids") and not fact.get("source"):
                warnings.append(
                    f"Fact has no source or nugget link: '{fact.get('text', '')[:50]}...'"
                )

        return warnings

    def to_dict(self) -> dict:
        """Serialize skill metadata."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "phase": self.phase.value,
            "skill_type": self.skill_type.value,
            "version": self.version,
        }
