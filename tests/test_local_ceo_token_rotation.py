import stat

import pytest

from scripts.rotate_local_ceo_token import RotationError, replace_dotenv_token


def test_replace_dotenv_token_preserves_other_settings_and_private_mode(tmp_path):
    path = tmp_path / ".env.local"
    path.write_text("AAO_POSTGRES_URL=postgresql://private\nAAO_CEO_TOKEN=old-secret\n")
    path.chmod(0o600)

    replace_dotenv_token(path, "n" * 43)

    contents = path.read_text()
    assert "AAO_POSTGRES_URL=postgresql://private\n" in contents
    assert "AAO_CEO_TOKEN=" + "n" * 43 + "\n" in contents
    assert "old-secret" not in contents
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_replace_dotenv_token_appends_when_missing(tmp_path):
    path = tmp_path / ".env.local"
    path.write_text("AAO_ENV=development")
    path.chmod(0o600)

    replace_dotenv_token(path, "n" * 43)

    assert path.read_text() == "AAO_ENV=development\nAAO_CEO_TOKEN=" + "n" * 43 + "\n"


def test_replace_dotenv_token_refuses_duplicate_or_non_private_config(tmp_path):
    path = tmp_path / ".env.local"
    path.write_text("AAO_CEO_TOKEN=one\nAAO_CEO_TOKEN=two\n")
    path.chmod(0o600)
    with pytest.raises(RotationError, match="duplicate"):
        replace_dotenv_token(path, "n" * 43)

    path.write_text("AAO_CEO_TOKEN=one\n")
    path.chmod(0o640)
    with pytest.raises(RotationError, match="private"):
        replace_dotenv_token(path, "n" * 43)
