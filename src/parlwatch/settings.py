"""Runtime settings and YAML config loading. PROJECT_ROOT is the current working directory."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path.cwd()


def load_env(env_file: Path | None = None) -> None:
    """Export `.env` into os.environ so LiteLLM and API clients see provider keys."""
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PW_", env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'parlwatch.db'}"
    data_dir: Path = PROJECT_ROOT / "data"
    configs_dir: Path = PROJECT_ROOT / "configs"
    contact_email: str = ""
    app_name: str = "parlwatch"
    app_url: str = "https://github.com/fredbuildsai/parlwatch"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml(name: str) -> dict[str, Any]:
    path = get_settings().configs_dir / name
    return yaml.safe_load(path.read_text()) or {}
