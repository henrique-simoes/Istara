from app.api.routes.updates import is_newer

def test_is_newer_numeric():
    # Basic numeric comparison
    assert is_newer("2026.04.02.10", "2026.04.02.9") is True
    assert is_newer("2026.04.02.2", "2026.04.02.10") is False
    assert is_newer("2026.04.03.1", "2026.04.02.100") is True
    
    # Same version
    assert is_newer("2026.04.02.11", "2026.04.02.11") is False
    
    # Different component lengths
    assert is_newer("2026.04.02", "2026.04.02.1") is False
    assert is_newer("2026.04.02.1", "2026.04.02") is True
    
    # Unknown cases
    assert is_newer("unknown", "2026.04.02") is False
    assert is_newer("2026.04.02", "unknown") is True
    
    # Text in versions (fallback to string)
    assert is_newer("v2", "v1") is True
