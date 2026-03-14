"""UI Audit Agent — continuous UI quality, accessibility, and heuristics checking.

This agent validates the ReClaw UI itself:
1. Heuristic evaluation (Nielsen's 10)
2. Accessibility compliance (WCAG 2.2)
3. Navigation path validation
4. Component consistency
5. Responsive behavior
6. Performance metrics
7. Error state coverage
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.core.ollama import ollama

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


@dataclass
class UIIssue:
    """A UI quality issue found by the audit agent."""

    category: str  # heuristic, accessibility, navigation, consistency, performance
    severity: Severity
    location: str  # component/page/route
    description: str
    heuristic: str = ""  # Which Nielsen heuristic or WCAG criterion
    recommendation: str = ""
    auto_fixable: bool = False


@dataclass
class UIAuditReport:
    """Complete UI audit report."""

    timestamp: str
    issues: list[UIIssue] = field(default_factory=list)
    scores: dict = field(default_factory=dict)
    passed_checks: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def overall_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)


class UIAuditAgent:
    """Continuously audits the ReClaw UI for quality issues."""

    def __init__(self) -> None:
        self._running = False
        self._audit_interval = 600  # 10 minutes
        self._reports: list[UIAuditReport] = []

        # UI component registry — what we know about the UI
        self._components = {
            "sidebar": {
                "path": "/",
                "elements": ["project_list", "navigation", "new_project_button", "collapse_toggle"],
                "states": ["expanded", "collapsed"],
            },
            "chat_view": {
                "path": "/",
                "elements": ["message_list", "input_field", "send_button", "file_upload", "streaming_indicator"],
                "states": ["empty", "with_messages", "streaming", "error"],
            },
            "kanban_board": {
                "path": "/tasks",
                "elements": ["columns", "task_cards", "add_task", "drag_handles"],
                "states": ["empty", "with_tasks", "dragging"],
            },
            "findings_view": {
                "path": "/findings",
                "elements": ["phase_tabs", "stats_cards", "sections", "drill_down"],
                "states": ["empty", "with_data", "expanded_section"],
            },
            "settings_view": {
                "path": "/settings",
                "elements": ["hardware_info", "model_status", "model_list"],
                "states": ["loading", "loaded", "error"],
            },
            "status_bar": {
                "path": "/",
                "elements": ["connection_indicator", "agent_status", "version"],
                "states": ["connected", "disconnected"],
            },
        }

        # Nielsen's 10 heuristics checklist
        self._heuristics = {
            "visibility": "Visibility of system status — user always knows what's happening",
            "match": "Match between system and real world — familiar language and concepts",
            "control": "User control and freedom — undo, redo, escape hatches",
            "consistency": "Consistency and standards — same actions produce same results",
            "error_prevention": "Error prevention — design prevents errors before they occur",
            "recognition": "Recognition rather than recall — minimize memory load",
            "flexibility": "Flexibility and efficiency — accelerators for experts",
            "aesthetics": "Aesthetic and minimalist design — no irrelevant information",
            "error_recovery": "Help users recognize, diagnose, and recover from errors",
            "help": "Help and documentation — accessible when needed",
        }

    async def start(self) -> None:
        """Start the continuous UI audit loop."""
        self._running = True
        logger.info("UI Audit Agent started.")

        while self._running:
            try:
                report = await self.run_audit()
                self._reports.append(report)

                if len(self._reports) > 50:
                    self._reports = self._reports[-50:]

                if report.critical_count > 0:
                    logger.warning(f"UI Audit: {report.critical_count} critical issues found!")

            except Exception as e:
                logger.error(f"UI Audit error: {e}")

            await asyncio.sleep(self._audit_interval)

    def stop(self) -> None:
        self._running = False

    async def run_audit(self) -> UIAuditReport:
        """Run a complete UI audit cycle."""
        report = UIAuditReport(timestamp=datetime.now(timezone.utc).isoformat())

        # 1. Heuristic evaluation
        heuristic_issues = await self._evaluate_heuristics()
        report.issues.extend(heuristic_issues)

        # 2. Accessibility check
        a11y_issues = self._check_accessibility()
        report.issues.extend(a11y_issues)

        # 3. Navigation path validation
        nav_issues = self._check_navigation()
        report.issues.extend(nav_issues)

        # 4. Component consistency
        consistency_issues = self._check_consistency()
        report.issues.extend(consistency_issues)

        # 5. Error state coverage
        error_issues = self._check_error_states()
        report.issues.extend(error_issues)

        # Calculate scores
        report.scores = self._calculate_scores(report)

        return report

    async def _evaluate_heuristics(self) -> list[UIIssue]:
        """Evaluate UI against Nielsen's 10 heuristics using LLM analysis."""
        issues = []

        # Use the LLM to evaluate the UI structure against heuristics
        ui_description = json.dumps(self._components, indent=2)

        prompt = f"""You are a UX expert performing a heuristic evaluation of a web application called ReClaw.

Here is the UI component structure:
{ui_description}

Nielsen's 10 heuristics:
{json.dumps(self._heuristics, indent=2)}

The app is a UX Research assistant with: chat view, kanban board, findings view with Double Diamond phases,
settings page, collapsible sidebar, and status bar.

Evaluate each component against each heuristic. Report ONLY actual issues you can identify
from the component structure. Don't report speculative issues.

Respond in JSON:
{{"issues": [{{"component": "...", "heuristic": "...", "severity": "critical|major|minor|cosmetic",
"description": "...", "recommendation": "..."}}]}}"""

        try:
            resp = await ollama.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
            text = resp.get("message", {}).get("content", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                for issue_data in data.get("issues", []):
                    issues.append(UIIssue(
                        category="heuristic",
                        severity=Severity(issue_data.get("severity", "minor")),
                        location=issue_data.get("component", "unknown"),
                        description=issue_data.get("description", ""),
                        heuristic=issue_data.get("heuristic", ""),
                        recommendation=issue_data.get("recommendation", ""),
                    ))
        except Exception as e:
            logger.error(f"Heuristic evaluation error: {e}")

        return issues

    def _check_accessibility(self) -> list[UIIssue]:
        """Check for common accessibility issues in the UI structure."""
        issues = []

        # Check for missing aria labels / roles in component definitions
        for comp_name, comp_data in self._components.items():
            # Check if interactive elements have proper labeling
            interactive = {"button", "input", "toggle", "drag"}
            for elem in comp_data.get("elements", []):
                has_interactive = any(i in elem.lower() for i in interactive)
                if has_interactive:
                    # Flag for review — can't verify without actual DOM
                    issues.append(UIIssue(
                        category="accessibility",
                        severity=Severity.MINOR,
                        location=f"{comp_name}/{elem}",
                        description=f"Interactive element '{elem}' — verify aria-label and keyboard accessibility.",
                        heuristic="WCAG 4.1.2 Name, Role, Value",
                        recommendation=f"Ensure '{elem}' has proper aria-label, role, and keyboard event handlers.",
                    ))

        # Check color contrast concerns
        issues.append(UIIssue(
            category="accessibility",
            severity=Severity.MINOR,
            location="global/colors",
            description="Verify color contrast ratios meet WCAG AA (4.5:1 for text, 3:1 for large text).",
            heuristic="WCAG 1.4.3 Contrast",
            recommendation="Run automated contrast checker on all text/background combinations.",
        ))

        # Check for keyboard navigation
        issues.append(UIIssue(
            category="accessibility",
            severity=Severity.MAJOR,
            location="kanban_board/drag_handles",
            description="Drag-and-drop must have keyboard alternative for accessibility.",
            heuristic="WCAG 2.1.1 Keyboard",
            recommendation="Add keyboard-operated move buttons (arrow keys or menu) as alternative to drag-and-drop.",
        ))

        return issues

    def _check_navigation(self) -> list[UIIssue]:
        """Validate navigation paths and state management."""
        issues = []

        # Check that all views are reachable
        required_views = {"chat", "tasks", "findings", "settings"}
        nav_elements = self._components.get("sidebar", {}).get("elements", [])

        if "navigation" not in nav_elements:
            issues.append(UIIssue(
                category="navigation",
                severity=Severity.CRITICAL,
                location="sidebar",
                description="No navigation element found in sidebar.",
                recommendation="Ensure sidebar has clear navigation links to all views.",
            ))

        # Check for back navigation / breadcrumbs in nested views
        issues.append(UIIssue(
            category="navigation",
            severity=Severity.MINOR,
            location="findings_view/drill_down",
            description="Drill-down view should have breadcrumb navigation for context.",
            heuristic="Recognition rather than recall",
            recommendation="Add breadcrumb trail: Project > Phase > Finding Type > Specific Finding.",
        ))

        return issues

    def _check_consistency(self) -> list[UIIssue]:
        """Check for consistency across components."""
        issues = []

        # Check that all components have proper state handling
        for comp_name, comp_data in self._components.items():
            states = comp_data.get("states", [])
            if "error" not in states and comp_name not in {"status_bar", "sidebar"}:
                issues.append(UIIssue(
                    category="consistency",
                    severity=Severity.MINOR,
                    location=comp_name,
                    description=f"Component '{comp_name}' has no explicit error state defined.",
                    recommendation="Add error state handling with clear error message and retry action.",
                ))

            if "loading" not in states and comp_name not in {"status_bar", "sidebar"}:
                issues.append(UIIssue(
                    category="consistency",
                    severity=Severity.COSMETIC,
                    location=comp_name,
                    description=f"Component '{comp_name}' has no explicit loading state defined.",
                    recommendation="Add loading skeleton or spinner for async data fetching.",
                ))

        return issues

    def _check_error_states(self) -> list[UIIssue]:
        """Check for proper error state coverage."""
        issues = []

        error_scenarios = [
            ("chat_view", "Ollama offline — chat should show clear error, not just fail silently"),
            ("chat_view", "Network disconnect during streaming — handle gracefully"),
            ("kanban_board", "Failed task move — should rollback optimistic update"),
            ("findings_view", "Empty project — should show helpful onboarding message"),
            ("settings_view", "Hardware detection failure — show fallback information"),
        ]

        for component, scenario in error_scenarios:
            issues.append(UIIssue(
                category="error_handling",
                severity=Severity.MINOR,
                location=component,
                description=f"Error scenario to verify: {scenario}",
                recommendation="Test this scenario and ensure graceful degradation.",
            ))

        return issues

    def _calculate_scores(self, report: UIAuditReport) -> dict:
        """Calculate scores per category."""
        categories = set(i.category for i in report.issues)
        scores = {}

        for cat in categories:
            cat_issues = [i for i in report.issues if i.category == cat]
            # Score: 100 - (critical*25 + major*15 + minor*5 + cosmetic*1)
            penalty = sum(
                25 if i.severity == Severity.CRITICAL else
                15 if i.severity == Severity.MAJOR else
                5 if i.severity == Severity.MINOR else 1
                for i in cat_issues
            )
            scores[cat] = max(0, 100 - penalty)

        return scores

    def get_latest_report(self) -> UIAuditReport | None:
        return self._reports[-1] if self._reports else None

    def get_reports(self, limit: int = 10) -> list[UIAuditReport]:
        return self._reports[-limit:]


# Singleton
ui_audit_agent = UIAuditAgent()
