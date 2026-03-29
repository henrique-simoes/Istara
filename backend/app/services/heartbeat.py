"""Heartbeat manager — periodic health checks for all agents."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.datetime_utils import ensure_utc
from app.models.agent import Agent, AgentState, HeartbeatStatus
from app.models.database import async_session

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Monitors agent health with periodic heartbeat checks."""

    def __init__(self) -> None:
        self._running = False
        self._check_interval = 15  # seconds between heartbeat cycles

    async def start(self) -> None:
        """Start the heartbeat monitoring loop."""
        self._running = True
        logger.info("Heartbeat manager started")

        while self._running:
            try:
                await self._check_all_agents()
            except Exception as e:
                logger.error(f"Heartbeat cycle error: {e}")

            await asyncio.sleep(self._check_interval)

    def stop(self) -> None:
        self._running = False
        logger.info("Heartbeat manager stopped")

    async def _check_all_agents(self) -> None:
        """Run heartbeat checks for all active agents."""
        from app.api.websocket import manager as ws_manager

        async with async_session() as db:
            result = await db.execute(
                select(Agent).where(Agent.is_active == True)
            )
            agents = result.scalars().all()

            now = datetime.now(timezone.utc)
            batch_update = []

            for agent in agents:
                if agent.state == AgentState.STOPPED:
                    new_status = HeartbeatStatus.STOPPED
                elif agent.state == AgentState.ERROR:
                    # Auto-recover agents stuck in ERROR state:
                    # If no recent error log in last 2 minutes, reset to IDLE.
                    if agent.last_heartbeat_at:
                        err_elapsed = (now - ensure_utc(agent.last_heartbeat_at)).total_seconds()
                        if err_elapsed > 120:
                            agent.state = AgentState.IDLE
                            new_status = HeartbeatStatus.HEALTHY
                            logger.info(
                                f"Auto-recovered agent {agent.name} from ERROR to IDLE "
                                f"(no recent errors for {err_elapsed:.0f}s)"
                            )
                        else:
                            new_status = HeartbeatStatus.ERROR
                    else:
                        new_status = HeartbeatStatus.ERROR
                elif agent.state == AgentState.PAUSED:
                    new_status = HeartbeatStatus.DEGRADED
                elif agent.state in (AgentState.IDLE, AgentState.WORKING):
                    # Check if agent has been responsive within its heartbeat window
                    if agent.last_heartbeat_at:
                        elapsed = (now - ensure_utc(agent.last_heartbeat_at)).total_seconds()
                        if elapsed > agent.heartbeat_interval_seconds * 3:
                            new_status = HeartbeatStatus.ERROR
                        elif elapsed > agent.heartbeat_interval_seconds * 1.5:
                            new_status = HeartbeatStatus.DEGRADED
                        else:
                            new_status = HeartbeatStatus.HEALTHY
                    else:
                        # No heartbeat yet — mark healthy if agent is active
                        new_status = HeartbeatStatus.HEALTHY
                else:
                    new_status = HeartbeatStatus.STOPPED

                if agent.heartbeat_status != new_status or agent.state != AgentState.STOPPED:
                    agent.heartbeat_status = new_status
                    agent.last_heartbeat_at = now
                    batch_update.append({
                        "agent_id": agent.id,
                        "name": agent.name,
                        "status": new_status.value,
                        "state": agent.state.value,
                    })

            await db.commit()

            # Broadcast all heartbeat updates in one batch
            if batch_update:
                try:
                    await ws_manager.broadcast("heartbeat_batch", {
                        "agents": batch_update,
                    })
                except Exception:
                    pass  # Don't let WS errors stop heartbeat


heartbeat_manager = HeartbeatManager()
