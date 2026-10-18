"""Decision-model settings and project policy routes (CF-SPEC-1, Phase 7).

Keys go to custody and never come back; only global admins configure endpoints; a project admin
chooses the mode and deciders, and a hosted decider is refused without the project's explicit
egress opt-in (DEC-1). Persistence and key custody are stubbed: nothing touches Keychain, the env
file or the network.
"""

import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.routes import decision_models as routes
from app.config import settings
from app.main import app
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.project_member import ProjectMember

SECRET = "sk-test-not-a-real-key-123456"


@pytest.fixture
def custody(monkeypatch):
    stored: dict[str, str] = {}
    monkeypatch.setattr(settings, "decider_endpoints_json", "", raising=False)
    monkeypatch.setattr(routes, "persist_env_value", lambda key, value: True)
    monkeypatch.setattr(routes, "store_api_key", lambda eid, key: stored.__setitem__(eid, key))
    monkeypatch.setattr(routes, "delete_api_key", lambda eid: stored.pop(eid, None))
    monkeypatch.setattr(
        routes,
        "resolve_api_key",
        lambda *, keychain_service="", keychain_account="", env_var="": stored.get(
            keychain_account, ""
        ),
    )
    return stored


@pytest_asyncio.fixture
async def admin(admin_auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=admin_auth_headers
    ) as client:
        yield client


@pytest_asyncio.fixture
async def researcher(researcher_auth_headers):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=researcher_auth_headers
    ) as client:
        yield client


async def _add(admin, endpoint_id, base_url, model="jev-1.14.0", api_key=""):
    return await admin.post(
        "/api/settings/decision-models",
        json={"endpoint_id": endpoint_id, "base_url": base_url, "model": model, "api_key": api_key},
    )


@pytest.mark.asyncio
async def test_admin_configures_endpoints_and_keys_never_come_back(admin, custody):
    local = await _add(admin, "kev-local", "http://127.0.0.1:8080", model="kev-1")
    assert local.status_code == 200, local.text
    assert local.json()["endpoint"]["credential_status"] == "not_needed"

    missing = await _add(admin, "jev", "https://api.typesafe.ai")
    assert missing.status_code == 400 and missing.json()["detail"] == "decider_api_key_required"

    hosted = await _add(admin, "jev", "https://api.typesafe.ai", api_key=SECRET)
    assert hosted.status_code == 200 and custody == {"jev": SECRET}
    assert SECRET not in hosted.text and SECRET not in settings.decider_endpoints_json

    listing = await admin.get("/api/settings/decision-models")
    assert listing.status_code == 200 and SECRET not in listing.text
    views = {item["endpoint_id"]: item for item in listing.json()["endpoints"]}
    assert views["jev"]["locality"] == "hosted"
    assert views["jev"]["credential_status"] == "configured"
    assert views["kev-local"]["locality"] == "local"
    assert any(p["model"] == "jev-1.14.0" for p in listing.json()["presets"])
    stored = json.loads(settings.decider_endpoints_json)
    assert {item["endpoint_id"] for item in stored} == {"kev-local", "jev"}

    duplicate = await _add(admin, "jev", "https://api.typesafe.ai", api_key=SECRET)
    assert duplicate.status_code == 409

    removed = await admin.delete("/api/settings/decision-models/jev")
    assert removed.status_code == 200 and "jev" not in custody
    assert (await admin.delete("/api/settings/decision-models/jev")).status_code == 404


@pytest.mark.asyncio
async def test_non_admins_cannot_configure_endpoints(researcher, custody, monkeypatch):
    monkeypatch.setattr(settings, "team_mode", True)
    assert (await researcher.get("/api/settings/decision-models")).status_code == 403
    response = await _add(researcher, "x", "http://127.0.0.1:8080", model="m")
    assert response.status_code == 403


async def _project(role: str) -> str:
    await init_db()
    project_id = f"project-dm-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Decision models"))
        db.add(
            ProjectMember(
                id=uuid.uuid4().hex, project_id=project_id, user_id="test-researcher", role=role
            )
        )
        await db.commit()
    return project_id


@pytest.mark.asyncio
async def test_project_policy_requires_explicit_egress_for_hosted_deciders(admin, custody):
    await _add(admin, "kev-local", "http://127.0.0.1:8080", model="kev-1")
    await _add(admin, "jev", "https://api.typesafe.ai", api_key=SECRET)
    project_id = await _project("project_admin")
    url = f"/api/projects/{project_id}/decision-models"

    initial = (await admin.get(url)).json()
    assert initial["mode"] == "auto" and initial["decider_endpoint_ids"] == []
    assert initial["hosted_egress_endpoint_ids"] == []

    async def put(**body):
        return await admin.put(url, json={"mode": "decision_models", **body})

    assert (await put()).json()["detail"] == "mode_needs_a_decider"
    no_opt_in = await put(decider_endpoint_ids=["jev"])
    assert no_opt_in.json()["detail"] == "hosted_decider_needs_egress_opt_in"
    local_opt_in = await put(
        decider_endpoint_ids=["kev-local"], hosted_egress_endpoint_ids=["kev-local"]
    )
    assert local_opt_in.json()["detail"] == "egress_opt_in_is_for_hosted_endpoints"
    assert (await put(decider_endpoint_ids=["nope"])).json()["detail"] == "unknown_decider_endpoint"
    assert (await admin.put(url, json={"mode": "bogus"})).status_code == 400

    ok = await put(decider_endpoint_ids=["jev", "kev-local"], hosted_egress_endpoint_ids=["jev"])
    assert ok.status_code == 200, ok.text
    stored = (await admin.get(url)).json()
    assert stored["mode"] == "decision_models"
    assert stored["decider_endpoint_ids"] == ["jev", "kev-local"]
    assert stored["hosted_egress_endpoint_ids"] == ["jev"]
    assert stored["trust"] == []

    from app.core.decider.access import authorized_hosted_endpoint_ids
    from app.services.assurance_policies import load_project_assurance

    assert (await load_project_assurance(project_id)).decider_endpoint_ids == ("jev", "kev-local")
    async with async_session() as db:
        assert await authorized_hosted_endpoint_ids(db, project_id) == ["jev"]


@pytest.mark.asyncio
async def test_project_researchers_read_but_only_project_admins_change(
    researcher, custody, monkeypatch
):
    monkeypatch.setattr(settings, "team_mode", True)
    project_id = await _project("researcher")
    url = f"/api/projects/{project_id}/decision-models"
    view = await researcher.get(url)
    assert view.status_code == 200 and view.json()["can_edit"] is False
    assert (await researcher.put(url, json={"mode": "none"})).status_code == 403
