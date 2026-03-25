"""UI Audit Agent — continuous UI quality, accessibility, and heuristics checking.

This agent validates the ReClaw UI by:
1. Fetching real frontend pages via HTTP and analyzing HTML structure
2. Checking API responses for consistency
3. Evaluating against Nielsen's 10 heuristics (using LLM + real data)
4. Accessibility compliance checks (WCAG 2.2)
5. Navigation path validation
6. Component consistency
7. Error state coverage
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import httpx

from app.api.websocket import broadcast_agent_status
from app.core.ollama import ollama

logger = logging.getLogger(__name__)

FRONTEND_BASE = os.getenv("RECLAW_FRONTEND_BASE", "http://localhost:3000")
API_BASE = os.getenv("RECLAW_API_BASE", "http://localhost:8000")


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
    pages_fetched: int = 0
    api_endpoints_checked: int = 0

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
        self._client: httpx.AsyncClient | None = None
        self._last_html: str = ""
        # Task execution worker
        from app.core.sub_agent_worker import SubAgentWorker
        self._worker = SubAgentWorker("reclaw-ui-audit", check_interval=30)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def start(self) -> None:
        """Start the continuous UI audit loop."""
        self._running = True
        logger.info("UI Audit Agent started.")

        # Start task worker alongside audit cycle
        asyncio.create_task(self._worker.start_task_loop())

        # Wait for frontend to be ready
        await asyncio.sleep(30)

        while self._running:
            try:
                await broadcast_agent_status(
                    "working", "UI Audit Agent: running quality checks..."
                )
                report = await self.run_audit()
                self._reports.append(report)

                if len(self._reports) > 50:
                    self._reports = self._reports[-50:]

                if report.critical_count > 0:
                    await broadcast_agent_status(
                        "warning",
                        f"UI Audit: {report.critical_count} critical issues! Score: {report.overall_score:.0f}/100",
                    )
                    logger.warning(f"UI Audit: {report.critical_count} critical issues found!")
                else:
                    await broadcast_agent_status(
                        "idle",
                        f"UI Audit complete. Score: {report.overall_score:.0f}/100",
                    )

            except Exception as e:
                logger.error(f"UI Audit error: {e}")
                await broadcast_agent_status("error", f"UI Audit error: {e}")

            await asyncio.sleep(self._audit_interval)

    def stop(self) -> None:
        self._running = False
        self._worker.stop_task_loop()

    async def run_audit(self) -> UIAuditReport:
        """Run a complete UI audit cycle."""
        report = UIAuditReport(timestamp=datetime.now(timezone.utc).isoformat())
        client = await self._get_client()

        # 1. Fetch frontend page and analyze HTML
        html_issues, pages = await self._analyze_frontend_html(client)
        report.issues.extend(html_issues)
        report.pages_fetched = pages
        if not html_issues:
            report.passed_checks.append("frontend_html")

        # 2. Check API response consistency
        api_issues, endpoints = await self._check_api_consistency(client)
        report.issues.extend(api_issues)
        report.api_endpoints_checked = endpoints
        if not api_issues:
            report.passed_checks.append("api_consistency")

        # 3. Accessibility check (from HTML analysis)
        a11y_issues = self._check_accessibility_from_html(self._last_html)
        report.issues.extend(a11y_issues)
        if not a11y_issues:
            report.passed_checks.append("accessibility")

        # 4. Navigation path validation
        nav_issues = self._check_navigation()
        report.issues.extend(nav_issues)
        if not nav_issues:
            report.passed_checks.append("navigation")

        # 5. Component consistency
        consistency_issues = self._check_consistency()
        report.issues.extend(consistency_issues)
        if not consistency_issues:
            report.passed_checks.append("consistency")

        # 6. Error state coverage (tests real API error responses)
        error_issues = await self._check_error_states(client)
        report.issues.extend(error_issues)
        if not error_issues:
            report.passed_checks.append("error_states")

        # 7. Heuristic evaluation (LLM-assisted with real data)
        heuristic_issues = await self._evaluate_heuristics_with_data(report)
        report.issues.extend(heuristic_issues)
        if not heuristic_issues:
            report.passed_checks.append("heuristics")

        # Calculate scores
        report.scores = self._calculate_scores(report)

        return report

    async def _analyze_frontend_html(self, client: httpx.AsyncClient) -> tuple[list[UIIssue], int]:
        """Fetch the frontend page and analyze HTML structure."""
        issues = []
        pages_fetched = 0

        try:
            resp = await client.get(FRONTEND_BASE)
            if resp.status_code == 200:
                pages_fetched = 1
                html = resp.text
                self._last_html = html

                # Check for essential meta tags
                if "viewport" not in html.lower():
                    issues.append(UIIssue(
                        category="accessibility",
                        severity=Severity.MAJOR,
                        location="index.html",
                        description="Missing viewport meta tag — mobile experience may be broken.",
                        heuristic="WCAG 1.4.10 Reflow",
                        recommendation="Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
                    ))

                # Check for lang attribute
                if not re.search(r'<html[^>]*lang=', html):
                    issues.append(UIIssue(
                        category="accessibility",
                        severity=Severity.MAJOR,
                        location="index.html",
                        description="Missing lang attribute on <html> element.",
                        heuristic="WCAG 3.1.1 Language of Page",
                        recommendation="Add lang='en' to the <html> tag.",
                    ))

                # Check for title
                if "<title>" not in html.lower() or "<title></title>" in html.lower():
                    issues.append(UIIssue(
                        category="accessibility",
                        severity=Severity.MINOR,
                        location="index.html",
                        description="Missing or empty page title.",
                        heuristic="WCAG 2.4.2 Page Titled",
                        recommendation="Set a descriptive page title.",
                    ))

                # Check JS bundle size (rough estimate from script tags)
                script_count = html.lower().count("<script")
                if script_count > 15:
                    issues.append(UIIssue(
                        category="performance",
                        severity=Severity.MINOR,
                        location="index.html",
                        description=f"Found {script_count} script tags — may impact initial load time.",
                        recommendation="Consider code splitting and lazy loading.",
                    ))

            else:
                issues.append(UIIssue(
                    category="availability",
                    severity=Severity.CRITICAL,
                    location="frontend",
                    description=f"Frontend returned HTTP {resp.status_code}",
                    recommendation="Ensure frontend dev server is running on port 3000.",
                ))

        except httpx.ConnectError:
            issues.append(UIIssue(
                category="availability",
                severity=Severity.CRITICAL,
                location="frontend",
                description="Cannot connect to frontend at " + FRONTEND_BASE,
                recommendation="Start the frontend dev server: npm --prefix frontend run dev",
            ))
        except Exception as e:
            logger.error(f"Frontend HTML fetch error: {e}")

        return issues, pages_fetched

    async def _check_api_consistency(self, client: httpx.AsyncClient) -> tuple[list[UIIssue], int]:
        """Check API endpoints return consistent, well-structured responses."""
        issues = []
        endpoints_checked = 0

        api_checks = [
            ("/api/health", "health"),
            ("/api/settings/status", "status"),
            ("/api/projects", "projects"),
            ("/api/skills", "skills"),
        ]

        for path, name in api_checks:
            try:
                resp = await client.get(f"{API_BASE}{path}")
                endpoints_checked += 1

                if resp.status_code != 200:
                    issues.append(UIIssue(
                        category="api_consistency",
                        severity=Severity.MAJOR,
                        location=path,
                        description=f"API endpoint {path} returned {resp.status_code}",
                        recommendation=f"Fix {name} endpoint to return 200.",
                    ))
                elif not resp.headers.get("content-type", "").startswith("application/json"):
                    issues.append(UIIssue(
                        category="api_consistency",
                        severity=Severity.MINOR,
                        location=path,
                        description=f"API endpoint {path} doesn't return application/json content-type",
                        recommendation="Set Content-Type: application/json header.",
                    ))
                else:
                    # Check response time
                    if hasattr(resp, "elapsed") and resp.elapsed.total_seconds() > 3:
                        issues.append(UIIssue(
                            category="performance",
                            severity=Severity.MINOR,
                            location=path,
                            description=f"API response time > 3s ({resp.elapsed.total_seconds():.1f}s)",
                            recommendation="Optimize query or add caching.",
                        ))

            except Exception as e:
                issues.append(UIIssue(
                    category="api_consistency",
                    severity=Severity.MAJOR,
                    location=path,
                    description=f"Failed to reach API endpoint {path}: {e}",
                    recommendation="Ensure backend is running on port 8000.",
                ))

        return issues, endpoints_checked

    def _check_accessibility_from_html(self, html: str) -> list[UIIssue]:
        """Analyze fetched HTML for accessibility issues."""
        issues = []
        if not html:
            return issues

        # Check for images without alt text
        imgs_without_alt = len(re.findall(r'<img(?![^>]*alt=)', html))
        if imgs_without_alt > 0:
            issues.append(UIIssue(
                category="accessibility",
                severity=Severity.MAJOR,
                location="global",
                description=f"Found {imgs_without_alt} images without alt attributes.",
                heuristic="WCAG 1.1.1 Non-text Content",
                recommendation="Add descriptive alt text to all images.",
            ))

        # Check for buttons without accessible names
        buttons_without_text = len(re.findall(r'<button[^>]*>\s*</button>', html))
        if buttons_without_text > 0:
            issues.append(UIIssue(
                category="accessibility",
                severity=Severity.MAJOR,
                location="global",
                description=f"Found {buttons_without_text} empty buttons without text or aria-label.",
                heuristic="WCAG 4.1.2 Name, Role, Value",
                recommendation="Add text content or aria-label to all buttons.",
            ))

        # Check for form inputs without labels
        inputs = len(re.findall(r'<input[^>]*>', html))
        labels = len(re.findall(r'<label', html))
        aria_labels_on_inputs = len(re.findall(r'<input[^>]*aria-label', html))
        if inputs > 0 and (labels + aria_labels_on_inputs) < inputs:
            issues.append(UIIssue(
                category="accessibility",
                severity=Severity.MINOR,
                location="global",
                description=f"Found {inputs} inputs but only {labels + aria_labels_on_inputs} labels/aria-labels.",
                heuristic="WCAG 1.3.1 Info and Relationships",
                recommendation="Ensure every input has an associated label or aria-label.",
            ))

        return issues

    def _check_navigation(self) -> list[UIIssue]:
        """Validate navigation paths and state management."""
        issues = []

        # Check if nav items are present in the fetched HTML
        required_nav_items = ["chat", "tasks", "findings", "settings"]
        if self._last_html:
            html_lower = self._last_html.lower()
            missing = [item for item in required_nav_items if item not in html_lower]
            if missing:
                issues.append(UIIssue(
                    category="navigation",
                    severity=Severity.MINOR,
                    location="frontend",
                    description=f"Navigation items not found in initial HTML: {', '.join(missing)} (may be client-rendered)",
                    recommendation="Verify all navigation items render client-side.",
                ))

        return issues

    def _check_consistency(self) -> list[UIIssue]:
        """Check for consistency across components."""
        issues = []

        # Expected component states
        components = {
            "chat_view": {"states": ["empty", "with_messages", "streaming", "error"]},
            "kanban_board": {"states": ["empty", "with_tasks", "dragging"]},
            "findings_view": {"states": ["empty", "with_data", "expanded_section"]},
            "settings_view": {"states": ["loading", "loaded", "error"]},
        }

        for comp_name, comp_data in components.items():
            states = comp_data.get("states", [])
            if "error" not in states:
                issues.append(UIIssue(
                    category="consistency",
                    severity=Severity.MINOR,
                    location=comp_name,
                    description=f"Component '{comp_name}' has no explicit error state defined.",
                    recommendation="Add error state handling with clear error message and retry action.",
                ))
            if "loading" not in states and "empty" not in states:
                issues.append(UIIssue(
                    category="consistency",
                    severity=Severity.COSMETIC,
                    location=comp_name,
                    description=f"Component '{comp_name}' has no explicit loading state defined.",
                    recommendation="Add loading skeleton or spinner for async data fetching.",
                ))

        return issues

    async def _check_error_states(self, client: httpx.AsyncClient) -> list[UIIssue]:
        """Test error states by sending bad requests to the API."""
        issues = []

        # Test invalid project ID
        try:
            resp = await client.get(f"{API_BASE}/api/projects/nonexistent-id-12345")
            if resp.status_code == 500:
                issues.append(UIIssue(
                    category="error_handling",
                    severity=Severity.MAJOR,
                    location="/api/projects/:id",
                    description="Invalid project ID returns 500 instead of 404.",
                    recommendation="Return 404 with clear error message for missing resources.",
                ))
        except Exception:
            pass

        # Test invalid task creation
        try:
            resp = await client.post(
                f"{API_BASE}/api/tasks",
                json={"title": ""},  # Missing required fields
            )
            if resp.status_code == 500:
                issues.append(UIIssue(
                    category="error_handling",
                    severity=Severity.MAJOR,
                    location="/api/tasks",
                    description="Invalid task creation returns 500 instead of 422.",
                    recommendation="Return 422 with validation error details.",
                ))
        except Exception:
            pass

        return issues

    async def _evaluate_heuristics_with_data(self, report: UIAuditReport) -> list[UIIssue]:
        """Use LLM to evaluate heuristics with real audit data as context."""
        issues = []

        existing_issues_summary = "\n".join(
            f"- [{i.severity.value}] {i.location}: {i.description}"
            for i in report.issues[:20]
        )

        prompt = f"""You are a UX expert evaluating a web application called ReClaw (a UX Research assistant).

Real audit data from this cycle:
- Frontend pages fetched: {report.pages_fetched}
- API endpoints checked: {report.api_endpoints_checked}
- Issues found so far: {len(report.issues)}
- Checks passed: {', '.join(report.passed_checks) or 'none yet'}

Existing issues found by automated checks:
{existing_issues_summary or 'None found by automated checks.'}

Based on the REAL data above, identify 3-5 additional heuristic issues that are
NOT already covered by the existing issues. Focus on actionable, specific issues.

Respond in JSON:
{{"issues": [{{"heuristic": "...", "severity": "minor|major", "location": "...",
"description": "...", "recommendation": "..."}}]}}"""

        try:
            resp = await ollama.chat(messages=[{"role": "user", "content": prompt}], temperature=0.3)
            text = resp.get("message", {}).get("content", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                for issue_data in data.get("issues", [])[:5]:
                    sev = issue_data.get("severity", "minor")
                    if sev not in ("critical", "major", "minor", "cosmetic"):
                        sev = "minor"
                    issues.append(UIIssue(
                        category="heuristic",
                        severity=Severity(sev),
                        location=issue_data.get("location", "unknown"),
                        description=issue_data.get("description", ""),
                        heuristic=issue_data.get("heuristic", ""),
                        recommendation=issue_data.get("recommendation", ""),
                    ))
        except Exception as e:
            logger.error(f"Heuristic evaluation error: {e}")

        return issues

    def _calculate_scores(self, report: UIAuditReport) -> dict:
        """Calculate scores per category."""
        categories = set(i.category for i in report.issues)
        scores = {}

        for cat in categories:
            cat_issues = [i for i in report.issues if i.category == cat]
            penalty = sum(
                25 if i.severity == Severity.CRITICAL else
                15 if i.severity == Severity.MAJOR else
                5 if i.severity == Severity.MINOR else 1
                for i in cat_issues
            )
            scores[cat] = max(0, 100 - penalty)

        # Add perfect scores for categories with no issues
        for check in report.passed_checks:
            if check not in scores:
                scores[check] = 100

        return scores

    def get_latest_report(self) -> UIAuditReport | None:
        return self._reports[-1] if self._reports else None

    def get_reports(self, limit: int = 10) -> list[UIAuditReport]:
        return self._reports[-limit:]


# Singleton
ui_audit_agent = UIAuditAgent()
