"""Regression tests for the background heartbeat writer."""

import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import OperationalError

from app.models.agent import AgentState, HeartbeatStatus
from app.services import heartbeat as heartbeat_module


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_heartbeat_retries_transient_sqlite_lock(monkeypatch):
    """A concurrent writer must not permanently poison the heartbeat loop."""

    agent = SimpleNamespace(
        id="heartbeat-lock-agent",
        name="Heartbeat lock agent",
        state=AgentState.IDLE,
        heartbeat_interval_seconds=60,
        heartbeat_status=HeartbeatStatus.HEALTHY,
        last_heartbeat_at=None,
    )

    class _Session:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        async def execute(self, _statement):
            return _Result([agent])

        async def commit(self):
            self.commits += 1
            if self.commits == 1:
                raise OperationalError(
                    "UPDATE agents",
                    {},
                    sqlite3.OperationalError("database is locked"),
                )

        async def rollback(self):
            self.rollbacks += 1

    session = _Session()
    monkeypatch.setattr(
        heartbeat_module,
        "async_session",
        lambda: _SessionContext(session),
    )
    monkeypatch.setattr(
        heartbeat_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock()),
    )
    from app.api.websocket import manager

    monkeypatch.setattr(manager, "broadcast", AsyncMock())

    await heartbeat_module.HeartbeatManager()._check_all_agents()

    assert session.commits == 2
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_heartbeat_does_not_retry_non_lock_database_errors(monkeypatch):
    """Unexpected database failures remain visible to the heartbeat supervisor."""

    agent = SimpleNamespace(
        id="heartbeat-error-agent",
        name="Heartbeat error agent",
        state=AgentState.IDLE,
        heartbeat_interval_seconds=60,
        heartbeat_status=HeartbeatStatus.HEALTHY,
        last_heartbeat_at=None,
    )

    class _Session:
        async def execute(self, _statement):
            return _Result([agent])

        async def commit(self):
            raise OperationalError(
                "UPDATE agents",
                {},
                sqlite3.OperationalError("disk I/O error"),
            )

        async def rollback(self):
            raise AssertionError("non-lock failures must not be retried")

    monkeypatch.setattr(
        heartbeat_module,
        "async_session",
        lambda: _SessionContext(_Session()),
    )

    with pytest.raises(OperationalError, match="disk I/O error"):
        await heartbeat_module.HeartbeatManager()._check_all_agents()
