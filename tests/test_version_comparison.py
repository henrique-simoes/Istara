from types import SimpleNamespace

from app.api.routes.updates import get_latest_release_version_from_git, is_newer

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


def test_get_latest_release_version_from_git_parses_newest_tag(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="\n".join([
                "sha refs/tags/v2026.04.02.14",
                "sha refs/tags/v2026.04.03",
                "sha refs/tags/v2026.04.03.2",
            ]),
        )

    monkeypatch.setattr("app.api.routes.updates.subprocess.run", fake_run)
    assert get_latest_release_version_from_git() == "2026.04.03.2"


def test_get_latest_release_version_from_git_handles_failures(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr("app.api.routes.updates.subprocess.run", fake_run)
    assert get_latest_release_version_from_git() == ""
