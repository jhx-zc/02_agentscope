"""Configuration helpers: paths, environment variables, and TOML parsing."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv as _load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config/agentscope.toml"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv(path: str | Path | None = None) -> None:
    """Load project-level environment variables without overriding the shell."""
    env_path = Path(path or DEFAULT_ENV_PATH)
    if env_path.exists():
        _load_dotenv(dotenv_path=env_path, override=False)


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the optional TOML config for the starter agent."""
    load_dotenv()
    config_path = Path(path or os.getenv("AGENTSCOPE_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return {}

    with config_path.open("rb") as file:
        return tomllib.load(file)


def _maybe_number(value: str | int | float) -> str | int | float:
    """try to convert string to number"""
    if isinstance(value, int | float):
        return value

    try:
        return int(value)        # "42" → 42 (int)
    except ValueError:
        pass

    try:
        return float(value)      # "3.14" → 3.14 (float)
    except ValueError:
        pass

    return value                 # "hello" → "hello" (保持字符串)
