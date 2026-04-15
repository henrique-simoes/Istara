"""Tests for telemetry spans, agent hooks, and telemetry recorder."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock


class TestTelemetrySpanModel:
    def test_telemetry_span_model_columns(self):
        from app.models.telemetry_span import TelemetrySpan

        columns = {c.name for c in TelemetrySpan.__table__.columns}
        required = {
            "id",
            "trace_id",
            "parent_id",
            "operation",
            "skill_name",
            "model_name",
            "agent_id",
            "started_at",
            "duration_ms",
            "status",
            "quality_score",
            "consensus_score",
            "error_type",
            "error_message",
            "project_id",
            "task_id",
            "temperature",
            "tool_name",
            "tool_success",
            "tool_duration_ms",
            "source",
            "created_at",
        }
        assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_telemetry_span_table_name(self):
        from app.models.telemetry_span import TelemetrySpan

        assert TelemetrySpan.__tablename__ == "telemetry_spans"

    def test_telemetry_span_no_content_fields(self):
        from app.models.telemetry_span import TelemetrySpan

        columns = {c.name for c in TelemetrySpan.__table__.columns}
        forbidden = {"prompt", "response", "user_content", "file_content", "url"}
        for field in forbidden:
            assert field not in columns, f"TelemetrySpan should not store {field}"


class TestAgentHooks:
    def test_agent_hooks_register_and_fire(self):
        from app.core.agent_hooks import AgentHooks

        hooks = AgentHooks()
        called = []

        async def my_hook(context):
            called.append(context.get("event", "unknown"))

        hooks.register("post_task", my_hook)
        assert len(hooks._hooks["post_task"]) == 1

    def test_agent_hooks_rejects_invalid_event(self):
        from app.core.agent_hooks import AgentHooks

        hooks = AgentHooks()
        with pytest.raises(ValueError, match="Unknown hook event"):
            hooks.register("invalid_event", AsyncMock())

    def test_agent_hooks_valid_events(self):
        from app.core.agent_hooks import AgentHooks

        hooks = AgentHooks()
        for event in (
            "pre_task",
            "post_task",
            "post_validation",
            "on_error",
            "on_completion",
        ):
            hooks.register(event, AsyncMock())


class TestTelemetryRecorder:
    @pytest.mark.asyncio
    async def test_record_span_handles_db_failure_gracefully(self):
        from app.core.telemetry import TelemetryRecorder

        recorder = TelemetryRecorder()
        with patch("app.core.telemetry.async_session") as mock_session:
            mock_session.side_effect = Exception("DB unavailable")
            result = await recorder.record_span(
                trace_id="test-trace-001",
                operation="skill_execute",
                skill_name="thematic-analysis",
                model_name="llama-3.1-70b",
                status="success",
                duration_ms=1500.0,
                quality_score=0.85,
                project_id="proj-123",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_model_intelligence_returns_structure(self):
        from app.core.telemetry import TelemetryRecorder

        recorder = TelemetryRecorder()
        with patch("app.core.telemetry.async_session") as mock_session:
            mock_ctx = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.execute = AsyncMock(
                side_effect=Exception("DB not available in test")
            )
            result = await recorder.get_model_intelligence("proj-123")
            assert "leaderboard" in result
            assert "error_taxonomy" in result
            assert "tool_success_rates" in result
            assert "latency_percentiles" in result
            assert result["project_id"] == "proj-123"


class TestModelIntelligenceEndpoint:
    def test_model_intelligence_route_exists(self):
        from app.api.routes.metrics import router

        routes = [r.path for r in router.routes]
        assert any("model-intelligence" in r for r in routes), (
            f"model-intelligence route not found in {routes}"
        )
