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


class TestEnhancedToolAndSteeringTelemetry:
    @pytest.mark.asyncio
    async def test_record_tool_call_persists_canonical_otel_span(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import async_session, init_db
        from app.models.telemetry_span import TelemetrySpan
        from sqlalchemy import select

        await init_db()
        project_id = f"proj-tool-{uuid.uuid4().hex[:8]}"
        trace_id = f"trace-tool-{uuid.uuid4().hex[:8]}"

        await telemetry_recorder.record_tool_call(
            tool_name="search_documents",
            duration_ms=42.5,
            success=True,
            project_id=project_id,
            agent_id="test-agent",
            trace_id=trace_id,
            task_id="task-123",
        )

        async with async_session() as session:
            stmt = select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "tool_call",
            )
            res = await session.execute(stmt)
            span = res.scalar_one_or_none()

            assert span is not None
            assert span.tool_name == "search_documents"
            assert span.tool_success == 1
            assert span.tool_duration_ms == 42.5
            assert span.status == "success"
            assert span.agent_id == "test-agent"
            assert span.task_id == "task-123"

    @pytest.mark.asyncio
    async def test_record_steering_event_persists_action_and_queue_depth(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import async_session, init_db
        from app.models.telemetry_span import TelemetrySpan
        from sqlalchemy import select

        await init_db()
        project_id = f"proj-steer-{uuid.uuid4().hex[:8]}"

        await telemetry_recorder.record_steering_event(
            project_id=project_id,
            agent_id="istara-main",
            action="steer_queued",
            queue_depth=3,
        )

        async with async_session() as session:
            stmt = select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "steering.event",
            )
            res = await session.execute(stmt)
            span = res.scalar_one_or_none()

            assert span is not None
            assert span.event_kind == "agent_steering"
            assert span.agent_id == "istara-main"
            assert "steer_queued:queue_depth=3" in span.route_id

    @pytest.mark.asyncio
    async def test_record_reliability_evaluation_persists_research_metrics(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import async_session, init_db
        from app.models.telemetry_span import TelemetrySpan
        from sqlalchemy import select

        await init_db()
        project_id = f"proj-reliability-{uuid.uuid4().hex[:8]}"

        await telemetry_recorder.record_reliability_evaluation(
            project_id=project_id,
            coding_run_id="run-kripp-1",
            metric_name="fleiss_kappa",
            score=0.74,
            alpha=0.71,
            threshold=0.60,
            rater_count=3,
            item_count=12,
            promotion_status="accepted",
        )

        async with async_session() as session:
            stmt = select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "coding_run.reliability",
            )
            res = await session.execute(stmt)
            span = res.scalar_one_or_none()

            assert span is not None
            assert span.reliability_score == 0.74
            assert span.consensus_score == 0.71
            assert span.status == "success"
            assert "fleiss_kappa:raters=3:items=12:threshold=0.6" in span.route_id

    @pytest.mark.asyncio
    async def test_execute_tool_telemetry_integration(self):
        from app.skills.system_actions import execute_tool
        from app.models.database import async_session, init_db
        from app.models.telemetry_span import TelemetrySpan
        from sqlalchemy import select

        await init_db()
        project_id = f"proj-exec-{uuid.uuid4().hex[:8]}"

        # 1. Unknown tool
        unknown_res = await execute_tool("nonexistent_tool_xyz", {}, project_id=project_id)
        assert unknown_res["success"] is False

        # 2. Known tool (search_documents)
        known_res = await execute_tool(
            "search_documents",
            {"query": "test query"},
            project_id=project_id,
            agent_id="test-agent",
        )
        assert known_res["success"] is True

        async with async_session() as session:
            stmt = select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "tool_call",
            ).order_by(TelemetrySpan.created_at.asc())
            res = await session.execute(stmt)
            spans = res.scalars().all()

            assert len(spans) == 2
            # Span 0: unknown tool
            assert spans[0].tool_name == "nonexistent_tool_xyz"
            assert spans[0].tool_success == 0
            assert spans[0].error_type == "unknown_tool"

            # Span 1: search_documents
            assert spans[1].tool_name == "search_documents"
            assert spans[1].tool_success == 1
            assert spans[1].tool_duration_ms > 0
            assert spans[1].agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_get_model_intelligence_includes_enhanced_aggregates(self):
        from app.core.telemetry import telemetry_recorder
        from app.models.database import init_db

        await init_db()
        project_id = f"proj-intel-{uuid.uuid4().hex[:8]}"

        await telemetry_recorder.record_tool_call(
            tool_name="create_task",
            duration_ms=10.0,
            success=True,
            project_id=project_id,
        )
        await telemetry_recorder.record_tool_call(
            tool_name="create_task",
            duration_ms=20.0,
            success=True,
            project_id=project_id,
        )
        await telemetry_recorder.record_tool_call(
            tool_name="create_task",
            duration_ms=30.0,
            success=False,
            error_type="validation_error",
            project_id=project_id,
        )
        await telemetry_recorder.record_steering_event(
            project_id=project_id,
            agent_id="istara-main",
            action="steer_queued",
        )

        intel = await telemetry_recorder.get_model_intelligence(project_id)

        assert "tool_summary" in intel
        assert intel["tool_summary"]["total_calls"] == 3
        assert intel["tool_summary"]["distinct_tools"] == 1
        assert intel["tool_summary"]["overall_success_rate"] == 0.667

        assert "steering_summary" in intel
        assert intel["steering_summary"]["total_events"] == 1
        assert intel["steering_summary"]["action_counts"].get("steer_queued") == 1

        tool_rates = intel["tool_success_rates"]
        assert len(tool_rates) == 1
        assert tool_rates[0]["tool"] == "create_task"
        assert tool_rates[0]["p50_duration_ms"] == 20.0
        assert tool_rates[0]["min_duration_ms"] == 10.0
        assert tool_rates[0]["max_duration_ms"] == 30.0
