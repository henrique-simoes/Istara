"""Tests for telemetry spans, agent hooks, and telemetry recorder."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch


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
            "reliability_score",
            "error_type",
            "error_message",
            "project_id",
            "task_id",
            "event_kind",
            "route_id",
            "donor_id",
            "retrieval_mode",
            "coding_run_id",
            "evidence_unit_id",
            "codebook_version_id",
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

    def test_trace_identifiers_fit_prefixed_agentic_ids(self):
        from app.models.telemetry_span import TelemetrySpan

        trace_column = TelemetrySpan.__table__.c.trace_id
        parent_column = TelemetrySpan.__table__.c.parent_id

        # Usage and agentic paths prefix a 32-character UUID hex value. The
        # schema must preserve the complete provenance handle rather than
        # truncating it or rejecting the telemetry write.
        assert trace_column.type.length >= len(f"agentic-{uuid.uuid4().hex}")
        assert parent_column.type.length >= len(f"agentic-{uuid.uuid4().hex}")


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
    def test_research_validity_telemetry_contract_covers_corrected_workflow(self):
        from app.core.research_validity import research_validity_telemetry_contract

        contract = research_validity_telemetry_contract()
        operations = {row["operation"] for row in contract["operations"]}
        categories = set(contract["categories"])

        assert contract["content_policy"] == "content_free_handles_only"
        assert {
            "evidence_extraction",
            "codebook_governance",
            "coding_reliability",
            "review_reconciliation",
            "donor_lifecycle",
            "retrieval_traceability",
            "context_safety",
            "promotion_gate",
            "governed_learning",
        }.issubset(categories)
        assert {
            "evidence_unit.extract",
            "codebook.freeze",
            "coding_run.model_selected",
            "coding_run.reliability",
            "coding_run.low_consensus",
            "reconciliation_decision.create",
            "donor.selected",
            "donor.served",
            "donor.failed",
            "retrieval.hybrid",
            "retrieval.graph_hybrid",
            "compression.protected_block",
            "finding.promotion",
            "report.promotion_gate",
            "autoresearch.validity_update",
            "self_evolution.proposal",
            "reasoning_bank.lesson",
            "memento_skill.health",
            "meta_hyperagent.proposal",
        }.issubset(operations)
        assert {"prompt", "response", "source_text", "quote", "token"}.issubset(
            set(contract["protected_fields"])
        )

    @pytest.mark.asyncio
    async def test_model_skill_stats_are_project_scoped(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import init_db

        await init_db()
        skill_name = f"thematic-analysis-{uuid.uuid4().hex[:8]}"
        model_a = f"model-a-{uuid.uuid4().hex[:8]}"
        model_b = f"model-b-{uuid.uuid4().hex[:8]}"
        await telemetry_recorder.record_model_performance(
            skill_name=skill_name,
            model_name=model_a,
            temperature=0.3,
            quality=0.9,
            success=True,
            project_id="project-a",
        )
        await telemetry_recorder.record_model_performance(
            skill_name=skill_name,
            model_name=model_b,
            temperature=0.3,
            quality=0.2,
            success=True,
            project_id="project-b",
        )

        project_a = await telemetry_recorder.get_model_intelligence("project-a")
        project_b = await telemetry_recorder.get_model_intelligence("project-b")

        project_a_models = {
            row["model_name"]
            for row in project_a["leaderboard"]
            if row["skill_name"] == skill_name
        }
        project_b_models = {
            row["model_name"]
            for row in project_b["leaderboard"]
            if row["skill_name"] == skill_name
        }
        assert project_a_models == {model_a}
        assert project_b_models == {model_b}

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
            health = recorder.write_health_snapshot()
            assert health["healthy"] is False
            assert health["write_failures"] == 1
            assert health["last_failure_at"]

    @pytest.mark.asyncio
    async def test_research_validity_audit_summarizes_content_free_handles(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import init_db

        project_id = f"proj-telemetry-audit-{uuid.uuid4().hex[:8]}"
        await init_db()

        await telemetry_recorder.record_research_validity_event(
            operation="coding_run.reliability",
            project_id=project_id,
            trace_id="trace-validity-audit",
            coding_run_id="run-audit-1",
            codebook_version_id="codebook-v1",
            reliability_score=0.42,
            status="degraded",
        )
        await telemetry_recorder.record_research_validity_event(
            operation="donor.served",
            project_id=project_id,
            trace_id="trace-validity-audit",
            coding_run_id="run-audit-1",
            model_name="local-test-model",
            donor_id="donor-a",
            route_id="donor-a:1",
            status="success",
        )
        await telemetry_recorder.record_research_validity_event(
            operation="retrieval.graph_hybrid",
            project_id=project_id,
            trace_id="trace-validity-audit",
            retrieval_mode="graph+hybrid",
            evidence_unit_id="eu-audit-1",
            status="success",
        )
        await telemetry_recorder.record_research_validity_event(
            operation="compression.protected_block",
            project_id=project_id,
            trace_id="trace-validity-audit",
            status="success",
        )
        await telemetry_recorder.record_research_validity_event(
            operation="report.promotion_gate",
            project_id=project_id,
            trace_id="trace-validity-audit",
            task_id="task-audit-1",
            status="degraded",
        )

        audit = await telemetry_recorder.get_research_validity_audit(project_id)

        assert audit["status"] == "ok"
        assert audit["content_policy"] == "content_free_handles_only"
        assert audit["operation_counts"]["coding_run.reliability"] == 1
        assert audit["operation_counts"]["donor.served"] == 1
        assert audit["category_counts"]["coding_reliability"] == 1
        assert audit["category_counts"]["donor_lifecycle"] == 1
        assert audit["retrieval_mode_counts"]["graph+hybrid"] == 1
        assert audit["donor_lifecycle_counts"]["donor.served"] == 1
        assert audit["route_evidence_count"] == 1
        assert audit["coding_run_ids"] == ["run-audit-1"]
        assert audit["evidence_unit_ids"] == ["eu-audit-1"]
        assert audit["codebook_version_ids"] == ["codebook-v1"]
        assert audit["reliability_summary"]["avg"] == 0.42
        assert "prompt" not in audit["route_evidence"][0]
        assert "response" not in audit["route_evidence"][0]
        assert "source_text" not in audit["route_evidence"][0]

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

    @pytest.mark.asyncio
    async def test_telemetry_opt_in_respects_flag(self):
        from app.core.agent_hooks import register_builtin_hooks, agent_hooks
        from app.config import settings

        # Clear existing hooks to avoid double-registration during test
        agent_hooks._hooks.clear()
        register_builtin_hooks()

        context = {"_start_time": 0, "skill_name": "test"}

        with patch(
            "app.core.telemetry.telemetry_recorder.record_span", new_callable=AsyncMock
        ) as mock_record:
            # 1. Test disabled (default)
            with patch.object(settings, "telemetry_enabled", False):
                await agent_hooks.fire("pre_task", context)
                await agent_hooks.fire("post_task", context)
                # Wait a bit
                import asyncio

                await asyncio.sleep(0.01)
                # Should not record spans if disabled
                assert mock_record.call_count == 0

            # Reset mock for phase 2
            mock_record.reset_mock()

            # 2. Test enabled
            with patch.object(settings, "telemetry_enabled", True):
                await agent_hooks.fire("pre_task", context)
                # Wait for the async task to run
                await asyncio.sleep(0.01)
                # Should record span if enabled
                assert mock_record.call_count == 1


class TestModelIntelligenceEndpoint:
    def test_model_intelligence_route_exists(self):
        from app.api.routes.metrics import router

        routes = [r.path for r in router.routes]
        assert any("model-intelligence" in r for r in routes), (
            f"model-intelligence route not found in {routes}"
        )
