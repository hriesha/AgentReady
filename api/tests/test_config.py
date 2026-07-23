"""Settings loading: defaults, env overrides, and key secrecy."""

from app.config import Settings

ENV_VARS = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_MAX_RPM",
    "DATABASE_URL",
    "WEB_ORIGIN",
    "DEMO_MODE",
)


def fresh_settings():
    """Build Settings without reading any local .env file."""
    return Settings(_env_file=None)


def clear_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults(monkeypatch):
    clear_env(monkeypatch)
    settings = fresh_settings()
    assert settings.llm_api_key.get_secret_value() == ""
    assert settings.llm_base_url == ""
    assert settings.llm_model == ""
    assert settings.llm_max_rpm == 12
    assert settings.database_url == "sqlite:///./agentready.db"
    assert settings.web_origin == "http://localhost:5173"
    assert settings.demo_mode is False


def test_env_overrides(monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "test-key-value")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_MAX_RPM", "5")
    monkeypatch.setenv("DEMO_MODE", "true")
    settings = fresh_settings()
    assert settings.llm_api_key.get_secret_value() == "test-key-value"
    assert settings.llm_base_url == "https://example.test/v1/"
    assert settings.llm_model == "test-model"
    assert settings.llm_max_rpm == 5
    assert settings.demo_mode is True


def test_api_key_never_leaks(monkeypatch):
    clear_env(monkeypatch)
    monkeypatch.setenv("LLM_API_KEY", "test-key-value")
    settings = fresh_settings()
    assert "test-key-value" not in repr(settings)
    assert "test-key-value" not in str(settings)
    assert "test-key-value" not in settings.model_dump_json()
