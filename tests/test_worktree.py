from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ottercode.tools.permissions import PermissionManager
from ottercode.tools.tasks import TaskManager
from ottercode.worktree.events import EventBus
from ottercode.worktree.manager import WorktreeManager


class WorktreeManagerTests(unittest.TestCase):
    def test_create_list_run_remove_cycle(self) -> None:
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._git(repo, "init", "-b", "main")
            self._git(repo, "config", "user.email", "test@example.com")
            self._git(repo, "config", "user.name", "tester")
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-m", "init")

            tasks = TaskManager(repo / ".tasks")
            permissions = PermissionManager(repo / ".ottercode" / "logs", auto_approve=True, interactive=False)
            events = EventBus(repo / ".worktrees" / "events.jsonl")
            manager = WorktreeManager(repo, tasks, events, permissions)

            created = manager.create("feature-a")
            listed = manager.list_all()
            status = manager.status("feature-a")
            run_output = manager.run("feature-a", "pwd")
            removed = manager.remove("feature-a", force=True)
            events_payload = manager.events_recent(limit=10)

            self.assertEqual(created["name"], "feature-a")
            self.assertEqual(len(listed), 1)
            self.assertIn("wt/feature-a", listed[0]["branch"])
            self.assertIn("## wt/feature-a", status)
            self.assertIn("feature-a", run_output)
            self.assertIn("Removed worktree 'feature-a'", removed)
            self.assertEqual(events_payload[0]["event"], "worktree.create.before")
            self.assertEqual(events_payload[-1]["event"], "worktree.remove.after")
            index = json.loads((repo / ".worktrees" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["worktrees"][0]["status"], "removed")

    def _git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return (result.stdout + result.stderr).strip()


if __name__ == "__main__":
    unittest.main()
