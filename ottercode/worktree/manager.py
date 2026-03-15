from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from ottercode.tools.permissions import PermissionManager
from ottercode.worktree.events import EventBus


class WorktreeError(RuntimeError):
    """Raised when worktree operations fail."""


def detect_repo_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    root = Path(result.stdout.strip())
    return root if root.exists() else None


class WorktreeManager:
    def __init__(
        self,
        workspace: Path,
        tasks: Any,
        events: EventBus,
        permissions: PermissionManager,
    ):
        self.workspace = workspace.resolve()
        self.repo_root = detect_repo_root(self.workspace) or self.workspace
        self.tasks = tasks
        self.events = events
        self.permissions = permissions
        self.dir = self.repo_root / ".worktrees"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"worktrees": []}, indent=2), encoding="utf-8")
        self.git_available = self._is_git_repo()

    def create(self, name: str, task_id: int | None = None, base_ref: str = "HEAD") -> dict[str, Any]:
        self._validate_git_repo()
        self._validate_name(name)
        if self._find(name):
            raise WorktreeError(f"Worktree '{name}' already exists in index")
        if task_id is not None and not self.tasks.exists(task_id):
            raise WorktreeError(f"Task {task_id} not found")

        path = self.dir / name
        branch = f"wt/{name}"
        self.events.emit(
            "worktree.create.before",
            task={"id": task_id} if task_id is not None else {},
            worktree={"name": name, "base_ref": base_ref},
        )
        try:
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])
            entry = {
                "name": name,
                "path": str(path),
                "branch": branch,
                "task_id": task_id,
                "status": "active",
                "created_at": time.time(),
            }
            index = self._load_index()
            index["worktrees"].append(entry)
            self._save_index(index)
            if task_id is not None:
                self.tasks.bind_worktree(task_id, name)
            self.events.emit(
                "worktree.create.after",
                task={"id": task_id} if task_id is not None else {},
                worktree={
                    "name": name,
                    "path": str(path),
                    "branch": branch,
                    "status": "active",
                },
            )
            return entry
        except Exception as exc:
            self.events.emit(
                "worktree.create.failed",
                task={"id": task_id} if task_id is not None else {},
                worktree={"name": name, "base_ref": base_ref},
                error=str(exc),
            )
            raise WorktreeError(str(exc)) from exc

    def list_all(self) -> list[dict[str, Any]]:
        return self._load_index().get("worktrees", [])

    def status(self, name: str) -> str:
        self._validate_git_repo()
        worktree = self._find_or_raise(name)
        path = Path(worktree["path"])
        if not path.exists():
            raise WorktreeError(f"Worktree path missing: {path}")
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (result.stdout + result.stderr).strip() or "Clean worktree"

    def run(self, name: str, command: str) -> str:
        self._validate_git_repo()
        worktree = self._find_or_raise(name)
        path = Path(worktree["path"])
        if not path.exists():
            raise WorktreeError(f"Worktree path missing: {path}")
        allowed, message = self.permissions.authorize_shell(command)
        if not allowed:
            return message
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return "Error: Timeout (300s)"
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"

    def remove(self, name: str, *, force: bool = False, complete_task: bool = False) -> str:
        self._validate_git_repo()
        worktree = self._find_or_raise(name)
        self.events.emit(
            "worktree.remove.before",
            task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
            worktree={"name": name, "path": worktree.get("path")},
        )
        try:
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(worktree["path"])
            self._run_git(args)

            if complete_task and worktree.get("task_id") is not None:
                task_id = int(worktree["task_id"])
                before = self.tasks.get_data(task_id)
                self.tasks.update(task_id, status="completed")
                self.tasks.unbind_worktree(task_id)
                self.events.emit(
                    "task.completed",
                    task={
                        "id": task_id,
                        "subject": before.get("subject", ""),
                        "status": "completed",
                    },
                    worktree={"name": name},
                )

            index = self._load_index()
            for item in index.get("worktrees", []):
                if item.get("name") == name:
                    item["status"] = "removed"
                    item["removed_at"] = time.time()
            self._save_index(index)
            self.events.emit(
                "worktree.remove.after",
                task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
                worktree={"name": name, "path": worktree.get("path"), "status": "removed"},
            )
            return f"Removed worktree '{name}'"
        except Exception as exc:
            self.events.emit(
                "worktree.remove.failed",
                task={"id": worktree.get("task_id")} if worktree.get("task_id") is not None else {},
                worktree={"name": name, "path": worktree.get("path")},
                error=str(exc),
            )
            raise WorktreeError(str(exc)) from exc

    def events_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.events.list_recent(limit)

    def _validate_name(self, name: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", name or ""):
            raise WorktreeError("Invalid worktree name. Use 1-40 chars: letters, numbers, ., _, -")

    def _validate_git_repo(self) -> None:
        if not self.git_available:
            raise WorktreeError("Not in a git repository. worktree commands require git.")

    def _is_git_repo(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_git(self, args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            message = (result.stdout + result.stderr).strip()
            raise WorktreeError(message or f"git {' '.join(args)} failed")
        return (result.stdout + result.stderr).strip() or "(no output)"

    def _load_index(self) -> dict[str, Any]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self, data: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _find(self, name: str) -> dict[str, Any] | None:
        for worktree in self._load_index().get("worktrees", []):
            if worktree.get("name") == name:
                return worktree
        return None

    def _find_or_raise(self, name: str) -> dict[str, Any]:
        worktree = self._find(name)
        if not worktree:
            raise WorktreeError(f"Unknown worktree '{name}'")
        return worktree
