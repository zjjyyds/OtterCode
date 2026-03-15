from __future__ import annotations

import unittest
from pathlib import Path

from ottercode.cli import build_parser


class CliParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = build_parser()

    def test_run_parser_accepts_yes_flag(self) -> None:
        args = self.parser.parse_args(["run", "--yes", "hello world"])

        self.assertEqual(args.command, "run")
        self.assertTrue(args.yes)
        self.assertEqual(args.prompt, "hello world")
        self.assertEqual(args.workspace, Path.cwd())

    def test_worktree_create_parser_reads_task_id(self) -> None:
        args = self.parser.parse_args([
            "worktree",
            "create",
            "feature-a",
            "--task-id",
            "7",
            "--base-ref",
            "main",
        ])

        self.assertEqual(args.command, "worktree")
        self.assertEqual(args.worktree_command, "create")
        self.assertEqual(args.name, "feature-a")
        self.assertEqual(args.task_id, 7)
        self.assertEqual(args.base_ref, "main")


if __name__ == "__main__":
    unittest.main()
