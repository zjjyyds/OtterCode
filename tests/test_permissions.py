from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ottercode.tools.permissions import PermissionManager


class PermissionManagerTests(unittest.TestCase):
    def test_non_interactive_write_requires_approval(self) -> None:
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp) / "logs"
            manager = PermissionManager(logs_dir, auto_approve=False, interactive=False, session_id="sess_perm")

            allowed, message = manager.authorize_write("note.txt", "hello")

            self.assertFalse(allowed)
            self.assertIn("Approval required", message)
            log_entries = (logs_dir / "approvals.jsonl").read_text(encoding="utf-8").splitlines()
            payload = json.loads(log_entries[0])
            self.assertFalse(payload["approved"])
            self.assertEqual(payload["action"], "write_file")

    def test_auto_approve_mutating_shell_logs_approval(self) -> None:
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp) / "logs"
            manager = PermissionManager(logs_dir, auto_approve=True, interactive=False, session_id="sess_auto")

            allowed, message = manager.authorize_shell("mkdir build")

            self.assertTrue(allowed)
            self.assertEqual(message, "")
            payload = json.loads((logs_dir / "approvals.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertTrue(payload["approved"])
            self.assertEqual(payload["mode"], "auto")
            self.assertEqual(payload["action"], "shell")

    def test_blocked_shell_is_rejected_immediately(self) -> None:
        with TemporaryDirectory() as tmp:
            logs_dir = Path(tmp) / "logs"
            manager = PermissionManager(logs_dir, auto_approve=True, interactive=False, session_id="sess_block")

            allowed, message = manager.authorize_shell("sudo rm -rf /tmp/demo")

            self.assertFalse(allowed)
            self.assertIn("Dangerous command blocked", message)
            payload = json.loads((logs_dir / "approvals.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["mode"], "blocked")


if __name__ == "__main__":
    unittest.main()
