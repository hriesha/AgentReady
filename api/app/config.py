"""Application settings loaded from environment variables.

Values come from the environment, or from a local .env file during
development. The .env file is never committed. The LLM API key is wrapped in
SecretStr so it cannot leak through logs, repr, or serialized output. LLM
endpoint values have no defaults in code: they are supplied entirely by the
environment, documented in .env.example.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_max_rpm: int = 12

    database_url: str = "sqlite:///./agentready.db"
    web_origin: str = "http://localhost:5173"
    demo_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the settings singleton, reading the environment once."""
    return Settings()
