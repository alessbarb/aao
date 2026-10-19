"""Local configuration stays opt-in, safe, and process-env-first."""
import os

import pytest

from aao import environment_settings


def test_selected_env_file_does_not_override_process_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    (tmp_path / ".env.local").write_text("AAO_CEO_TOKEN=from-file\n")
    monkeypatch.setenv("AAO_ENV", "development")
    monkeypatch.setenv("AAO_CEO_TOKEN", "from-process")
    monkeypatch.delenv("AAO_ENV_FILE", raising=False)
    environment_settings.load_local_env()
    assert os.getenv("AAO_CEO_TOKEN") == "from-process"


def test_explicit_test_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    (tmp_path / ".env.test").write_text("AAO_TEST_DB_DISPOSABLE=no\n")
    monkeypatch.setenv("AAO_ENV_FILE", ".env.test")
    monkeypatch.setenv("AAO_ENV", "test")
    assert environment_settings.load_local_env() == tmp_path / ".env.test"


def test_arbitrary_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.setenv("AAO_ENV", "development")
    monkeypatch.setenv("AAO_ENV_FILE", "../private.env")
    with pytest.raises(RuntimeError, match="AAO_ENV_FILE"):
        environment_settings.load_local_env()


def test_production_never_loads_dotenv(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    (tmp_path / ".env.local").write_text("AAO_WORK_TOKEN=from-file\n")
    monkeypatch.delenv("AAO_WORK_TOKEN", raising=False)
    monkeypatch.setenv("AAO_ENV", "production")
    monkeypatch.delenv("AAO_ENV_FILE", raising=False)
    assert environment_settings.load_local_env() is None
    assert os.getenv("AAO_WORK_TOKEN") is None
