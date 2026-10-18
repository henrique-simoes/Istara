"""Decider endpoint configuration, locality and per-project egress (CF-SPEC-1, Phase 1).

Hosted deciders receive research data only when the project opted in (owner decision DEC-1);
local deciders keep data on the user's hardware. Keys never appear in configuration or reprs.
"""

import asyncio
import json

from app.core.decider.access import open_decider
from app.core.decider.credentials import resolve_api_key
from app.core.decider.registry import (
    DeciderEndpoint,
    DeciderUnavailable,
    parse_endpoints,
    require_egress_authorization,
)

JEV = {
    "endpoint_id": "jev",
    "base_url": "https://api.typesafe.ai",
    "model": "jev-1.13.0",
    "keychain_service": "istara-typesafe",
    "api_key_env": "ISTARA_TEST_TYPESAFE_KEY",
}
KEV_LOCAL = {"endpoint_id": "kev", "base_url": "http://127.0.0.1:8081", "model": "kev-4b"}


def _value_error(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def _unavailable(fn) -> str:
    try:
        fn()
    except DeciderUnavailable as error:
        return error.reason
    return "allowed"


def test_endpoints_parse_and_classify_locality():
    endpoints = parse_endpoints(json.dumps([JEV, KEV_LOCAL]))
    assert endpoints["jev"].is_hosted and endpoints["jev"].locality == "hosted"
    assert endpoints["kev"].locality == "local"
    assert endpoints["jev"].request_url == "https://api.typesafe.ai/v1/systemone"
    lan = DeciderEndpoint("lan", "http://192.168.1.20:8081/v1/systemone", "laya")
    assert lan.locality == "local" and lan.request_url == "http://192.168.1.20:8081/v1/systemone"
    assert parse_endpoints("") == {} and parse_endpoints("   ") == {}


def test_bad_configuration_is_refused_whole():
    assert _value_error(lambda: parse_endpoints('{"endpoint_id": "x"}'))
    assert _value_error(lambda: parse_endpoints(json.dumps([JEV, JEV])))
    assert _value_error(lambda: parse_endpoints(json.dumps([{**JEV, "api_key": "sk-123"}])))
    assert _value_error(lambda: DeciderEndpoint("x", "http://api.example.com", "m"))
    assert _value_error(lambda: DeciderEndpoint("x", "http://169.254.169.254", "m"))
    assert _value_error(lambda: DeciderEndpoint("x", "https://u:p@api.example.com", "m"))
    assert _value_error(lambda: DeciderEndpoint("x", "https://api.example.com", ""))
    assert _value_error(lambda: DeciderEndpoint("x", "https://a.example.com", "m", max_retries=9))
    assert _value_error(lambda: DeciderEndpoint("x", "https://a.example.com", "m", timeout_s=0))


def test_repr_never_shows_key_sources():
    text = repr(parse_endpoints(json.dumps([JEV]))["jev"])
    assert "istara-typesafe" not in text and "ISTARA_TEST_TYPESAFE_KEY" not in text


def test_hosted_egress_requires_project_opt_in():
    endpoints = parse_endpoints(json.dumps([JEV, KEV_LOCAL]))
    jev, kev = endpoints["jev"], endpoints["kev"]
    assert _unavailable(lambda: require_egress_authorization(jev, "p1", [])) == (
        "hosted_egress_not_authorized"
    )
    assert _unavailable(lambda: require_egress_authorization(jev, "p1", ["other"])) == (
        "hosted_egress_not_authorized"
    )
    assert _unavailable(lambda: require_egress_authorization(jev, "p1", ["jev"])) == "allowed"
    assert _unavailable(lambda: require_egress_authorization(kev, "p1", [])) == "allowed"
    assert _unavailable(lambda: require_egress_authorization(kev, "", [])) == "project_required"
    assert _unavailable(lambda: require_egress_authorization(jev, " ", ["jev"])) == (
        "project_required"
    )


def test_env_key_wins_and_missing_key_is_empty():
    import os

    os.environ["ISTARA_TEST_TYPESAFE_KEY"] = "sk-test-value"
    try:
        key = resolve_api_key(keychain_service="", env_var="ISTARA_TEST_TYPESAFE_KEY")
        assert key == "sk-test-value"
    finally:
        del os.environ["ISTARA_TEST_TYPESAFE_KEY"]
    assert resolve_api_key(keychain_service="", env_var="ISTARA_TEST_UNSET_KEY") == ""


def test_open_decider_refuses_unknown_and_unauthorized_before_any_request():
    endpoints = parse_endpoints(json.dumps([JEV, KEV_LOCAL]))

    async def reason(endpoint_id: str, project_id: str) -> str:
        try:
            await open_decider(endpoint_id, project_id, endpoints=endpoints)
        except DeciderUnavailable as error:
            return error.reason
        return "opened"

    assert asyncio.run(reason("missing", "p1")) == "unknown_endpoint"
    assert asyncio.run(reason("jev", "")) == "project_required"
    assert asyncio.run(reason("kev", "")) == "project_required"
    assert asyncio.run(reason("kev", "p1")) == "opened"
