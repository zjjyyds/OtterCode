from __future__ import annotations

from pathlib import Path

MAX_OUTPUT_CHARS = 50000


def safe_path(workspace: Path, raw_path: str) -> Path:
    path = (workspace / raw_path).resolve()
    if not path.is_relative_to(workspace):
        raise ValueError(f"Path escapes workspace: {raw_path}")
    return path


def run_read(workspace: Path, path: str, limit: int | None = None) -> str:
    try:
        lines = safe_path(workspace, path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:MAX_OUTPUT_CHARS]
    except Exception as exc:  # pragma: no cover - defensive formatting
        return f"Error: {exc}"


def run_write(workspace: Path, path: str, content: str) -> str:
    try:
        file_path = safe_path(workspace, path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as exc:  # pragma: no cover - defensive formatting
        return f"Error: {exc}"


def run_edit(workspace: Path, path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(workspace, path)
        content = file_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as exc:  # pragma: no cover - defensive formatting
        return f"Error: {exc}"
