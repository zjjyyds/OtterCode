from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ottercode.config import RuntimeConfigError, resolve_paths
from ottercode.core.runtime import AgentRuntime
from ottercode.core.session import SessionStore, SessionStoreError
from ottercode.tools.permissions import PermissionManager
from ottercode.tools.tasks import TaskManager


def _add_common_workspace_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve guarded shell and file write operations.",
    )


def _build_session_store(workspace: Path) -> SessionStore:
    paths = resolve_paths(workspace)
    paths.ensure()
    return SessionStore(paths.sessions_dir)


def _build_permission_manager(workspace: Path, *, yes: bool, session_id: str | None) -> PermissionManager:
    paths = resolve_paths(workspace)
    paths.ensure()
    return PermissionManager(
        paths.logs_dir,
        auto_approve=yes,
        interactive=sys.stdin.isatty(),
        session_id=session_id,
    )


def _print_recent_sessions(store: SessionStore) -> None:
    recent = store.list_recent(limit=5)
    if not recent:
        return
    print("Recent sessions:")
    for item in recent:
        print(f"  {item.session_id}  {item.preview}")


def _runtime_from_workspace(
    workspace: Path,
    *,
    session_store: SessionStore | None = None,
    session_id: str | None = None,
    permission_manager: PermissionManager | None = None,
) -> AgentRuntime:
    paths = resolve_paths(workspace)
    paths.ensure()
    return AgentRuntime(
        paths,
        session_store=session_store,
        session_id=session_id,
        permission_manager=permission_manager,
    )


def _handle_chat(args: argparse.Namespace) -> int:
    store = _build_session_store(args.workspace)
    _print_recent_sessions(store)
    session_id = store.new_session_id()
    print(f"Session: {session_id}")
    runtime = _runtime_from_workspace(
        args.workspace,
        session_store=store,
        session_id=session_id,
        permission_manager=_build_permission_manager(
            args.workspace,
            yes=args.yes,
            session_id=session_id,
        ),
    )
    return runtime.chat()


def _handle_run(args: argparse.Namespace) -> int:
    store = _build_session_store(args.workspace)
    session_id = store.new_session_id()
    runtime = _runtime_from_workspace(
        args.workspace,
        session_store=store,
        session_id=session_id,
        permission_manager=_build_permission_manager(
            args.workspace,
            yes=args.yes,
            session_id=session_id,
        ),
    )
    final_text, _ = runtime.run_prompt(args.prompt, verbose=True)
    if final_text:
        print(final_text)
    print(f"Session saved: {session_id}")
    return 0


def _handle_tasks_list(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.workspace)
    paths.ensure()
    task_manager = TaskManager(paths.tasks_dir)
    print(task_manager.list_all())
    return 0


def _handle_resume(args: argparse.Namespace) -> int:
    store = _build_session_store(args.workspace)
    history = store.load(args.session_id)
    print(f"Resuming session: {args.session_id}")
    runtime = _runtime_from_workspace(
        args.workspace,
        session_store=store,
        session_id=args.session_id,
        permission_manager=_build_permission_manager(
            args.workspace,
            yes=args.yes,
            session_id=args.session_id,
        ),
    )
    return runtime.chat(history=history)


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
    except (RuntimeConfigError, SessionStoreError) as exc:
        parser.exit(status=2, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
