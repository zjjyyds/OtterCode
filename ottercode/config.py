from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

APP_DIRNAME = ".ottercode"


class RuntimeConfigError(RuntimeError):
    """Raised when model configuration is missing or invalid."""


@dataclass(frozen=True)
class AppPaths:
    workspace: Path
    app_home: Path
    sessions_dir: Path
    logs_dir: Path
    tasks_dir: Path
    worktrees_dir: Path
    skills_dir: Path
    transcripts_dir: Path

    def ensure(self) -> None:
        self.app_home.mkdir(exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ModelSettings:
    model_id: str
    base_url: str | None


def resolve_paths(workspace: Path | None = None) -> AppPaths:
    root = (workspace or Path.cwd()).resolve()
    app_home = root / APP_DIRNAME
    return AppPaths(
        workspace=root,
        app_home=app_home,
        sessions_dir=app_home / "sessions",
        logs_dir=app_home / "logs",
        tasks_dir=root / ".tasks",
        worktrees_dir=root / ".worktrees",
        skills_dir=root / "skills",
        transcripts_dir=app_home / "transcripts",
    )


def load_model_settings(workspace: Path | None = None) -> ModelSettings:
    env_file = (workspace or Path.cwd()) / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    else:
        load_dotenv(override=True)

    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

    model_id = os.getenv("MODEL_ID")
    if not model_id:
        raise RuntimeConfigError(
            "MODEL_ID is not set. Copy .env.example to .env and choose a model."
        )

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        raise RuntimeConfigError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env first."
        )

    return ModelSettings(model_id=model_id, base_url=base_url)
