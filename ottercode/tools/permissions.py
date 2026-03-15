from __future__ import annotations

import json
import time
from pathlib import Path

from ottercode.tools.bash import BLOCKED_COMMAND_FRAGMENTS

MUTATING_SHELL_FRAGMENTS = (
    "git push",
    "git commit",
    "git reset",
    "git apply",
    "rm ",
    "mv ",
    "cp ",
    "mkdir ",
    "touch ",
    "chmod ",
    "chown ",
    "sed -i",
    "pip install",
    "npm install",
    "pnpm install",
    "yarn add",
    ">",
    ">>",
)


class PermissionManager:
    def __init__(
        self,
        logs_dir: Path,
        *,
        auto_approve: bool = False,
        interactive: bool = True,
        session_id: str | None = None,
    ):
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs_dir / "approvals.jsonl"
        self.auto_approve = auto_approve
        self.interactive = interactive
        self.session_id = session_id

    def authorize_shell(self, command: str, *, background: bool = False) -> tuple[bool, str]:
        normalized = " ".join(command.strip().split())
        if not normalized:
            return False, "Error: Empty shell command"

        blocked_fragment = next(
            (fragment for fragment in BLOCKED_COMMAND_FRAGMENTS if fragment in command),
            None,
        )
        if blocked_fragment:
            self._log(
                action="background_shell" if background else "shell",
                target=normalized,
                approved=False,
                mode="blocked",
                reason=f"blocked fragment: {blocked_fragment}",
            )
            return False, "Error: Dangerous command blocked"

        if not any(fragment in command for fragment in MUTATING_SHELL_FRAGMENTS):
            return True, ""

        return self._request_approval(
            action="background_shell" if background else "shell",
            target=normalized,
            prompt=f"Allow shell command? {normalized}",
            reason="mutating shell command",
        )

    def authorize_write(self, path: str, content: str) -> tuple[bool, str]:
        preview = f"{path} ({len(content)} bytes)"
        return self._request_approval(
            action="write_file",
            target=path,
            prompt=f"Allow write_file? {preview}",
            reason="file write",
        )

    def authorize_edit(self, path: str, old_text: str, new_text: str) -> tuple[bool, str]:
        summary = (
            f"{path} old={self._snippet(old_text)} new={self._snippet(new_text)}"
        )
        return self._request_approval(
            action="edit_file",
            target=path,
            prompt=f"Allow edit_file? {summary}",
            reason="file edit",
        )

    def _request_approval(self, *, action: str, target: str, prompt: str, reason: str) -> tuple[bool, str]:
        if self.auto_approve:
            self._log(action=action, target=target, approved=True, mode="auto", reason=reason)
            return True, ""

        if not self.interactive:
            self._log(
                action=action,
                target=target,
                approved=False,
                mode="non_interactive",
                reason=reason,
            )
            return False, f"Error: Approval required for {action}: {target}. Re-run with --yes or interactive input."

        try:
            answer = input(f"[approval] {prompt} [y/N]: ")
        except (EOFError, KeyboardInterrupt):
            answer = ""
        approved = answer.strip().lower() in {"y", "yes"}
        self._log(
            action=action,
            target=target,
            approved=approved,
            mode="prompt",
            reason=reason,
        )
        if approved:
            return True, ""
        return False, f"Error: Approval denied for {action}: {target}"

    def _log(self, *, action: str, target: str, approved: bool, mode: str, reason: str) -> None:
        payload = {
            "ts": time.time(),
            "session_id": self.session_id,
            "action": action,
            "target": target,
            "approved": approved,
            "mode": mode,
            "reason": reason,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _snippet(self, text: str, limit: int = 40) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."
