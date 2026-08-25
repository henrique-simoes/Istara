from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_evidence_unit_listing_supports_bounded_offset(monkeypatch):
    from app.api.routes import research_validity as route

    monkeypatch.setattr(route, "require_project_access", AsyncMock())

    class _Scalars:
        @staticmethod
        def all():
            return []

    class _Result:
        @staticmethod
        def scalars():
            return _Scalars()

    class _Db:
        statement = None

        async def execute(self, statement):
            self.statement = statement
            return _Result()

    db = _Db()
    await route.list_evidence_units(
        "project-a",
        object(),
        limit=25,
        offset=50,
        db=db,
    )

    params = db.statement.compile().params
    assert 25 in params.values()
    assert 50 in params.values()
