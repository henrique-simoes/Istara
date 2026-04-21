"""Tests for participant simulation and audit log middleware."""

import json
import pytest
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "backend" / "app" / "skills" / "definitions"


class TestParticipantSimulation:
    def test_participant_simulation_skill_json_valid(self):
        path = SKILLS_DIR / "participant-simulation.json"
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["name"] == "participant-simulation"
        assert data["phase"] == "define"
        assert data["skill_type"] == "mixed"
        assert data["enabled"] is True
        assert (
            "game" in data["execute_prompt"].lower()
            or "simulation" in data["execute_prompt"].lower()
        )

    def test_participant_simulation_has_nash_and_satisficing(self):
        path = SKILLS_DIR / "participant-simulation.json"
        with open(path) as f:
            data = json.load(f)
        prompt = data["execute_prompt"].lower()
        assert "nash" in prompt or "equilibrium" in prompt
        assert "satisfic" in prompt

    def test_participant_simulation_scope_map(self):
        from app.core.report_manager import SCOPE_MAP

        assert "participant-simulation" in SCOPE_MAP
        assert SCOPE_MAP["participant-simulation"] == "Simulation Analysis"


class TestParticipantSimulationModule:
    def test_import_participant_simulation(self):
        from app.core.participant_simulation import (
            ParticipantStrategy,
            ParticipantProfile,
            GameScenario,
            SimulationResult,
            choose_action,
            simulate_response_mode,
            generate_participant_cohort,
            run_simulation_round,
            prisoner_dilemma_payoffs,
            stag_hunt_payoffs,
        )

    def test_participant_strategy_enum(self):
        from app.core.participant_simulation import ParticipantStrategy

        assert ParticipantStrategy.COOPERATIVE.value == "cooperative"
        assert ParticipantStrategy.ADVERSARIAL.value == "adversarial"
        assert len(list(ParticipantStrategy)) == 7

    def test_participant_profile_validation(self):
        from app.core.participant_simulation import (
            ParticipantProfile,
            ParticipantStrategy,
        )

        p = ParticipantProfile(
            id="P01",
            name="Test",
            strategy=ParticipantStrategy.COOPERATIVE,
            patience=1.5,
            honesty_bias=-0.1,
        )
        assert p.patience == 1.0
        assert p.honesty_bias == 0.0

    def test_prisoner_dilemma_payoffs(self):
        from app.core.participant_simulation import prisoner_dilemma_payoffs

        payoffs = prisoner_dilemma_payoffs()
        assert payoffs["defect"]["cooperate"] > payoffs["cooperate"]["cooperate"]
        assert payoffs["cooperate"]["cooperate"] > payoffs["defect"]["defect"]

    def test_stag_hunt_payoffs(self):
        from app.core.participant_simulation import stag_hunt_payoffs

        payoffs = stag_hunt_payoffs()
        assert payoffs["stag"]["stag"] > payoffs["hare"]["hare"]

    def test_generate_cohort(self):
        from app.core.participant_simulation import (
            generate_participant_cohort, ParticipantProfile, ParticipantStrategy,
        )
        cohort = generate_participant_cohort(5)
        assert len(cohort) == 5
        assert all(isinstance(p, ParticipantProfile) for p in cohort)
        assert all(p.strategy in list(ParticipantStrategy) for p in cohort)

    def test_cooperative_strategy_cooperates(self):
        from app.core.participant_simulation import (
            ParticipantProfile,
            ParticipantStrategy,
            GameScenario,
            choose_action,
            prisoner_dilemma_payoffs,
        )

        p = ParticipantProfile(
            id="P01",
            name="Coop",
            strategy=ParticipantStrategy.COOPERATIVE,
            engagement_level=1.0,
            patience=1.0,
        )
        scenario = GameScenario(
            id="pd",
            name="PD",
            description="Prisoner's Dilemma",
            scenario_type="prisoners_dilemma",
            payoffs=prisoner_dilemma_payoffs(),
        )
        action = choose_action(p, scenario, opponent_last_action="cooperate")
        assert action == "cooperate"

    def test_selfish_strategy_defects(self):
        from app.core.participant_simulation import (
            ParticipantProfile,
            ParticipantStrategy,
            GameScenario,
            choose_action,
            prisoner_dilemma_payoffs,
        )

        p = ParticipantProfile(
            id="P02",
            name="Selfish",
            strategy=ParticipantStrategy.SELFISH,
            engagement_level=1.0,
            patience=1.0,
            risk_aversion=0.0,
        )
        scenario = GameScenario(
            id="pd",
            name="PD",
            description="PD",
            scenario_type="prisoners_dilemma",
            payoffs=prisoner_dilemma_payoffs(),
        )
        action = choose_action(p, scenario, opponent_last_action="cooperate")
        assert action == "defect"

    def test_reciprocating_strategy_mirrors(self):
        from app.core.participant_simulation import (
            ParticipantProfile,
            ParticipantStrategy,
            GameScenario,
            choose_action,
            prisoner_dilemma_payoffs,
        )

        p = ParticipantProfile(
            id="P03",
            name="Recip",
            strategy=ParticipantStrategy.RECIPROCATING,
            engagement_level=1.0,
            patience=1.0,
        )
        scenario = GameScenario(
            id="pd",
            name="PD",
            description="PD",
            scenario_type="prisoners_dilemma",
            payoffs=prisoner_dilemma_payoffs(),
        )
        assert (
            choose_action(p, scenario, opponent_last_action="cooperate") == "cooperate"
        )
        assert choose_action(p, scenario, opponent_last_action="defect") == "defect"

    def test_run_simulation_round(self):
        from app.core.participant_simulation import (
            generate_participant_cohort,
            GameScenario,
            run_simulation_round,
            prisoner_dilemma_payoffs,
        )

        cohort = generate_participant_cohort(4, scenario_type="mixed")
        scenario = GameScenario(
            id="pd",
            name="PD",
            description="PD",
            scenario_type="prisoners_dilemma",
            payoffs=prisoner_dilemma_payoffs(),
        )
        results = run_simulation_round(cohort, scenario, rounds=3)
        assert len(results) == 12  # 4 participants x 3 rounds
        assert all(r.participant_id for r in results)
        assert all(r.strategy for r in results)
        assert all(r.choice in ["cooperate", "defect"] for r in results)


class TestAuditMiddleware:
    def test_audit_log_model_columns(self):
        from app.core.audit_middleware import AuditLog

        columns = {c.name for c in AuditLog.__table__.columns}
        assert "id" in columns
        assert "timestamp" in columns
        assert "user_id" in columns
        assert "method" in columns
        assert "path" in columns
        assert "status_code" in columns
        assert "duration_ms" in columns
        assert "ip_address" in columns
        assert "project_id" in columns

    def test_audit_log_skip_paths(self):
        from app.core.audit_middleware import SKIP_PATHS, SKIP_PREFIXES

        assert "/health" in SKIP_PATHS
        assert "/docs" in SKIP_PATHS
        assert "/api/mcp/server" in SKIP_PREFIXES

    def test_audit_log_table_name(self):
        from app.core.audit_middleware import AuditLog

        assert AuditLog.__tablename__ == "audit_log"
