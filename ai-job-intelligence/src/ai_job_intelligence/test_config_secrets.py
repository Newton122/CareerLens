"""Tests for JWT signing-key resolution.

The key was previously hardcoded in the source as "change-this-in-production",
which meant anyone who could read the repository could forge a login token for
any account. These tests pin the guards that replaced it.
"""
from __future__ import annotations

import importlib
import sys

import pytest


# config resolves the key at import time, so importing it under the scenario
# being tested would raise before the test could assert anything. Import it once
# with a known-good key, then drive _resolve_secret_key directly.
_IMPORT_SAFE_KEY = "z" * 48


def _resolve(monkeypatch, tmp_path, **env):
    """Load config in isolation, then apply the scenario's environment."""
    # Stop python-dotenv from re-reading the developer's real .env.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("SECRET_KEY", _IMPORT_SAFE_KEY)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    for mod in list(sys.modules):
        if mod.startswith("ai_job_intelligence.config"):
            del sys.modules[mod]
    config = importlib.import_module("ai_job_intelligence.config")

    # Now set up the scenario under test.
    for var in ("SECRET_KEY", "JWT_SECRET_KEY", "APP_ENV"):
        monkeypatch.delenv(var, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setattr(config, "_SECRET_FILE", tmp_path / ".secret_key")
    monkeypatch.setattr(
        config, "IS_PRODUCTION", env.get("APP_ENV", "development") == "production"
    )
    return config


def test_production_requires_an_explicit_key(monkeypatch, tmp_path):
    config = _resolve(monkeypatch, tmp_path, APP_ENV="production")
    with pytest.raises(RuntimeError, match="required when APP_ENV=production"):
        config._resolve_secret_key()


@pytest.mark.parametrize(
    "placeholder",
    ["change-this-in-production", "changeme", "secret", "YOUR-SECRET-KEY-HERE"],
)
def test_known_placeholders_are_refused(monkeypatch, tmp_path, placeholder):
    config = _resolve(monkeypatch, tmp_path, SECRET_KEY=placeholder)
    with pytest.raises(RuntimeError, match="placeholder"):
        config._resolve_secret_key()


def test_short_keys_are_refused(monkeypatch, tmp_path):
    config = _resolve(monkeypatch, tmp_path, SECRET_KEY="tooshort")
    with pytest.raises(RuntimeError, match="at least"):
        config._resolve_secret_key()


def test_a_real_key_is_accepted(monkeypatch, tmp_path):
    good = "x" * 48
    config = _resolve(monkeypatch, tmp_path, SECRET_KEY=good, APP_ENV="production")
    assert config._resolve_secret_key() == good


def test_jwt_secret_key_alias_works(monkeypatch, tmp_path):
    good = "y" * 48
    config = _resolve(monkeypatch, tmp_path, JWT_SECRET_KEY=good)
    assert config._resolve_secret_key() == good


def test_development_generates_and_persists(monkeypatch, tmp_path):
    """A generated key must survive a restart, or every reload logs users out."""
    config = _resolve(monkeypatch, tmp_path)

    first = config._resolve_secret_key()
    assert len(first) >= 32
    assert (tmp_path / ".secret_key").exists()

    # A second resolution reuses the stored key rather than making a new one.
    assert config._resolve_secret_key() == first


def test_generated_key_file_is_private(monkeypatch, tmp_path):
    config = _resolve(monkeypatch, tmp_path)
    config._resolve_secret_key()
    mode = (tmp_path / ".secret_key").stat().st_mode & 0o777
    assert mode == 0o600, oct(mode)


def test_the_old_hardcoded_key_is_gone():
    """Regression: the literal must not reappear in the source."""
    from pathlib import Path

    auth = Path(__file__).parent / "services" / "auth.py"
    assert "change-this-in-production" not in auth.read_text()
