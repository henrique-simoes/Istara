"""Tests for self-healing rules — telemetry-driven automated detection."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class MockSpan:
    def __init__(
        self,
        status="success",
        operation="skill_execute",
        skill_name="thematic-analysis",
        model_name="llama-3.1-70b",
        project_id="proj-123",
        duration_ms=5000.0,
        tool_success=None,
        tool_name=None,
        error_type=None,
    ):
        self.status = status
        self.operation = operation
        self.skill_name = skill_name
        self.model_name = model_name
        self.project_id = project_id
        self.duration_ms = duration_ms
        self.tool_success = tool_success
        self.tool_name = tool_name
        self.error_type = error_type


class TestSelfHealingRules:
    @pytest.mark.asyncio
    async def test_high_error_rate_triggers_action(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        span = MockSpan(status="error")

        actions = []
        for _ in range(20):
            a = await rules.evaluate_span(span)
            actions.extend(a)

        assert len(actions) > 0
        triggers = [a["trigger"] for a in actions]
        assert "high_error_rate" in triggers

    @pytest.mark.asyncio
    async def test_slow_execution_triggers_action(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        span = MockSpan(duration_ms=200_000)

        actions = await rules.evaluate_span(span)
        triggers = [a["trigger"] for a in actions]
        assert "slow_execution" in triggers

    @pytest.mark.asyncio
    async def test_successful_span_triggers_no_actions(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        span = MockSpan(status="success", duration_ms=5000)

        actions = await rules.evaluate_span(span)
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_tool_failure_spike_triggers_action(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        span = MockSpan(
            operation="tool_call", tool_success=False, tool_name="mcp_search"
        )

        actions = []
        for _ in range(20):
            a = await rules.evaluate_span(span)
            actions.extend(a)

        triggers = [a["trigger"] for a in actions]
        assert "tool_failure_spike" in triggers

    @pytest.mark.asyncio
    async def test_evaluate_all_returns_summary(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=AsyncMock(return_value=[]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(rules, "_get_session", return_value=mock_session):
            result = await rules.evaluate_all("proj-123")

        assert result["project_id"] == "proj-123"
        assert "total_issues" in result
        assert "by_trigger" in result
        assert "actions" in result
        assert isinstance(result["total_issues"], int)
