from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

Message = dict[str, Any]


class SessionStoreError(RuntimeError):
    """Raised when session persistence fails."""


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    path: Path
    updated_at: float
    preview: str


class SessionStore:
    def __init__(self, sessions_dir: Path):
        self.dir = sessions_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def new_session_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        return f"sess_{timestamp}_{suffix}"

    def path_for(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.jsonl"

    def save(self, session_id: str, messages: list[Message]) -> Path:
        path = self.path_for(session_id)
        with path.open("w", encoding="utf-8") as handle:
            for message in messages:
                handle.write(json.dumps(self._serialize_message(message)) + "\n")
        return path

    def load(self, session_id: str) -> list[Message]:
        path = self.path_for(session_id)
        if not path.exists():
            raise SessionStoreError(f"Session '{session_id}' not found")

        messages = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            messages.append(
                {
                    "role": payload["role"],
                    "content": payload["content"],
                }
            )
        return messages

    def list_recent(self, limit: int = 5) -> list[SessionSummary]:
        files = sorted(self.dir.glob("sess_*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
        summaries = []
        for path in files[:limit]:
            session_id = path.stem
            preview = ""
            try:
                messages = self.load(session_id)
                preview = self._preview(messages)
            except Exception:
                preview = "(unreadable session)"
            summaries.append(
                SessionSummary(
                    session_id=session_id,
                    path=path,
                    updated_at=path.stat().st_mtime,
                    preview=preview,
                )
            )
        return summaries

    def _preview(self, messages: list[Message]) -> str:
        for message in messages:
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                text = content.strip()
                if text:
                    return text[:80]
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        text = str(part.get("text") or part.get("content") or "").strip()
                        if text:
                            return text[:80]
        return "(empty session)"

    def _serialize_message(self, message: Message) -> Message:
        return {
            "role": message["role"],
            "content": self._serialize_value(message.get("content")),
        }

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize_value(item) for key, item in value.items()}
        if hasattr(value, "type"):
            payload = {"type": getattr(value, "type")}
            for field in ("id", "name", "text", "input", "tool_use_id", "content"):
                if hasattr(value, field):
                    payload[field] = self._serialize_value(getattr(value, field))
            return payload
        return str(value)
