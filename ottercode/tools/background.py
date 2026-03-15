from __future__ import annotations

import subprocess
import threading
import uuid
from pathlib import Path
from queue import Queue

MAX_RESULT_CHARS = 50000
MAX_NOTIFICATION_CHARS = 500


class BackgroundManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.tasks: dict[str, dict[str, str | None]] = {}
        self.notifications: Queue[dict[str, str]] = Queue()

    def run(self, command: str, timeout: int = 120) -> str:
        task_id = str(uuid.uuid4())[:8]
        self.tasks[task_id] = {
            "status": "running",
            "command": command,
            "result": None,
        }
        thread = threading.Thread(
            target=self._exec,
            args=(task_id, command, timeout),
            daemon=True,
        )
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _exec(self, task_id: str, command: str, timeout: int) -> None:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()[:MAX_RESULT_CHARS]
            self.tasks[task_id].update(
                {
                    "status": "completed",
                    "result": output or "(no output)",
                }
            )
        except Exception as exc:  # pragma: no cover - subprocess safety net
            self.tasks[task_id].update({"status": "error", "result": str(exc)})

        self.notifications.put(
            {
                "task_id": task_id,
                "status": str(self.tasks[task_id]["status"]),
                "result": str(self.tasks[task_id]["result"] or "")[:MAX_NOTIFICATION_CHARS],
            }
        )

    def check(self, task_id: str | None = None) -> str:
        if task_id:
            task = self.tasks.get(task_id)
            if not task:
                return f"Unknown: {task_id}"
            return f"[{task['status']}] {task.get('result', '(running)')}"
        return (
            "\n".join(
                f"{task_id}: [{task['status']}] {str(task['command'])[:60]}"
                for task_id, task in self.tasks.items()
            )
            or "No bg tasks."
        )

    def drain(self) -> list[dict[str, str]]:
        notifications: list[dict[str, str]] = []
        while not self.notifications.empty():
            notifications.append(self.notifications.get_nowait())
        return notifications
