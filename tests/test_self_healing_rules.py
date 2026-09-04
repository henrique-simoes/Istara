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
    async def test_error_rate_is_a_bounded_fraction_of_attempts(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        error = MockSpan(status="error")
        success = MockSpan(status="success")

        for _ in range(20):
            await rules.evaluate_span(error)
        assert rules._error_rate("proj-123:thematic-analysis:llama-3.1-70b") == 1.0

        rules = SelfHealingRules()
        for _ in range(20):
            await rules.evaluate_span(success)
        for _ in range(5):
            await rules.evaluate_span(error)
        rate = rules._error_rate("proj-123:thematic-analysis:llama-3.1-70b")
        assert rate == 0.2
        assert 0.0 <= rate <= 1.0

    @pytest.mark.asyncio
    async def test_tool_failure_rate_uses_successful_attempts_as_denominator(self):
        from app.core.self_healing_rules import SelfHealingRules

        rules = SelfHealingRules()
        failed = MockSpan(
            status="success", operation="tool_call", tool_success=False, tool_name="mcp_search"
        )
        successful = MockSpan(
            status="success", operation="tool_call", tool_success=True, tool_name="mcp_search"
        )
        for _ in range(3):
            await rules.evaluate_span(successful)
        for _ in range(1):
            actions = await rules.evaluate_span(failed)
        rate = rules._error_rate("tool:mcp_search")
        assert rate == 0.25
        assert all(a["error_rate"] <= 1.0 for a in actions if "error_rate" in a)

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
        mock_session.__aenter__.return_value = mock_session
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(rules, "_get_session", return_value=mock_session):
            result = await rules.evaluate_all("proj-123")

        assert result["project_id"] == "proj-123"
        assert "total_issues" in result
        assert "by_trigger" in result
        assert "actions" in result
        assert isinstance(result["total_issues"], int)
