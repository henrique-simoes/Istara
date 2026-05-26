from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reset_test_environment.py"


def test_destructive_test_reset_is_guarded_and_local_only():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "ISTARA_DESTRUCTIVE_TEST_RESET" in source
    assert "DELETE-ISTARA-LOCAL-TEST-DATA" in source
    assert "sqlite+aiosqlite:///" in source
    assert "Refusing reset: DATABASE_URL is not local" in source
    assert "allowed_data_roots" in source
    assert "BACKEND_ROOT / path" in source
    assert "os.chdir(BACKEND_ROOT)" in source


def test_destructive_test_reset_protects_local_model_artifacts():
    source = SCRIPT.read_text(encoding="utf-8")

    assert '"LLMs"' in source
    assert '"Model_Finetuning"' in source
    assert "assert_not_protected" in source


def test_destructive_test_reset_seeds_named_test_identities_without_projects():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'DEFAULT_ADMIN_USERNAME = "admin"' in source
    assert 'DEFAULT_ADMIN_PASSWORD = "istara123"' in source
    assert 'DEFAULT_RESEARCHER_PASSWORD = "istara123"' in source
    assert 'username = f"researcher_{index}"' in source
    assert "hash_field" in source
    assert "email_hash=" in source
    assert 'print("projects=0")' in source
