from __future__ import annotations

import argparse
from pathlib import Path

from ottercode.config import RuntimeConfigError, resolve_paths
from ottercode.core.runtime import AgentRuntime
from ottercode.tools.tasks import TaskManager


def _add_common_workspace_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root. Defaults to the current directory.",
    )


def _runtime_from_args(args: argparse.Namespace) -> AgentRuntime:
    paths = resolve_paths(args.workspace)
    paths.ensure()
    return AgentRuntime(paths)


def _handle_chat(args: argparse.Namespace) -> int:
    runtime = _runtime_from_args(args)
    return runtime.chat()


def _handle_run(args: argparse.Namespace) -> int:
    runtime = _runtime_from_args(args)
    final_text, _ = runtime.run_prompt(args.prompt, verbose=True)
    if final_text:
        print(final_text)
    return 0


def _handle_tasks_list(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.workspace)
    paths.ensure()
    task_manager = TaskManager(paths.tasks_dir)
    print(task_manager.list_all())
    return 0


def _handle_resume(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.workspace)
    paths.ensure()
    print(f"Resume scaffold for session '{args.session_id}'")
    print(f"Sessions directory: {paths.sessions_dir}")
    print("Session restoration is not implemented yet.")
    return 0


def _handle_worktree(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.workspace)
    paths.ensure()
    print(f"Worktree command '{args.worktree_command}' scaffold")
    print(f"Worktree directory: {paths.worktrees_dir}")
    print("Worktree management is not implemented yet.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ottercode",
        description="OtterCode: a local AI coding agent CLI for repository tasks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Start interactive agent mode.")
    _add_common_workspace_arg(chat_parser)
    chat_parser.set_defaults(func=_handle_chat)

    run_parser = subparsers.add_parser("run", help="Run a one-shot prompt.")
    _add_common_workspace_arg(run_parser)
    run_parser.add_argument("prompt", help="User prompt to execute.")
    run_parser.set_defaults(func=_handle_run)

    tasks_parser = subparsers.add_parser("tasks", help="Task operations.")
    tasks_subparsers = tasks_parser.add_subparsers(dest="tasks_command", required=True)
    tasks_list_parser = tasks_subparsers.add_parser("list", help="List tasks.")
    _add_common_workspace_arg(tasks_list_parser)
    tasks_list_parser.set_defaults(func=_handle_tasks_list)

    resume_parser = subparsers.add_parser("resume", help="Resume a saved session.")
    _add_common_workspace_arg(resume_parser)
    resume_parser.add_argument("session_id", help="Session identifier.")
    resume_parser.set_defaults(func=_handle_resume)

    worktree_parser = subparsers.add_parser("worktree", help="Worktree operations.")
    worktree_subparsers = worktree_parser.add_subparsers(dest="worktree_command", required=True)
    for name in ("create", "list", "status", "run", "remove", "events"):
        subparser = worktree_subparsers.add_parser(name, help=f"{name.title()} worktrees.")
        _add_common_workspace_arg(subparser)
        subparser.set_defaults(func=_handle_worktree)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeConfigError as exc:
        parser.exit(status=2, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
