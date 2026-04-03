import pytest
from fastapi import Request
from app.api.routes.auth import is_request_local

def test_is_request_local():
    class MockClient:
        def __init__(self, host):
            self.host = host

    class MockRequest:
        def __init__(self, headers, client_host):
            self.headers = headers
            self.client = MockClient(client_host)

    # 1. Direct local connection (Industry Standard)
    assert is_request_local(MockRequest({}, "127.0.0.1")) is True
    assert is_request_local(MockRequest({}, "::1")) is True

    # 2. Direct remote connection (Must be blocked)
    assert is_request_local(MockRequest({}, "192.168.1.5")) is False
    assert is_request_local(MockRequest({}, "203.0.113.1")) is False

    # 3. Remote user attempting to spoof via Tunnel/Proxy (CRITICAL)
    # The direct connection is from a remote IP, but they add local headers
    assert is_request_local(MockRequest({"x-forwarded-for": "127.0.0.1"}, "203.0.113.1")) is False
    
    # 4. Legit tunnel terminating at localhost (CRITICAL)
    # The direct connection is local (the tunnel), but the original IP is remote
    assert is_request_local(MockRequest({"x-forwarded-for": "203.0.113.1"}, "127.0.0.1")) is False
    assert is_request_local(MockRequest({"x-real-ip": "203.0.113.1"}, "127.0.0.1")) is False

    # 5. Chain of proxies starting from remote
    assert is_request_local(MockRequest({"x-forwarded-for": "203.0.113.1, 127.0.0.1"}, "127.0.0.1")) is False

    # 6. Entirely local chain (Safe)
    assert is_request_local(MockRequest({"x-forwarded-for": "127.0.0.1"}, "127.0.0.1")) is True
