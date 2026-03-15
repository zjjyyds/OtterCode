from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from ottercode.config import AppPaths, load_model_settings
from ottercode.core.compact import auto_compact, estimate_tokens, microcompact
from ottercode.tools.background import BackgroundManager
from ottercode.tools.bash import run_bash
from ottercode.tools.files import run_edit, run_read, run_write
from ottercode.tools.skills import SkillLoader
from ottercode.tools.tasks import TaskManager
from ottercode.tools.todo import TodoManager

Message = dict[str, Any]
TOKEN_THRESHOLD = 100000
MAX_TURNS = 30
MAX_MODEL_TOKENS = 8000


class AgentRuntime:
    def __init__(self, paths: AppPaths):
        self.paths = paths
        self.paths.ensure()
        self.model_settings = load_model_settings(self.paths.workspace)
        self.client = Anthropic(base_url=self.model_settings.base_url)
        self.todo = TodoManager()
        self.skills = SkillLoader(self.paths.skills_dir)
        self.tasks = TaskManager(self.paths.tasks_dir)
        self.background = BackgroundManager(self.paths.workspace)

    @property
    def system_prompt(self) -> str:
        return (
            f"You are a coding agent at {self.paths.workspace}. Use tools to solve tasks.\n"
            "Prefer task_create/task_update/task_list for multi-step work. "
            "Use TodoWrite for short checklists.\n"
            "Use task for isolated exploration or implementation. "
            "Use load_skill for specialized knowledge.\n"
            f"Skills:\n{self.skills.descriptions()}"
        )

    def run_prompt(
        self,
        prompt: str,
        *,
        history: list[Message] | None = None,
        verbose: bool = False,
    ) -> tuple[str, list[Message]]:
        messages = history if history is not None else []
        messages.append({"role": "user", "content": prompt})
        self.agent_loop(messages, verbose=verbose)
        return self.extract_last_text(messages), messages

    def chat(self) -> int:
        history: list[Message] = []
        while True:
            try:
                query = input("\033[36mottercode >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                return 0

            stripped = query.strip()
            if not stripped:
                continue
            if stripped.lower() in ("q", "exit"):
                return 0
            if stripped == "/compact":
                if history:
                    print("[manual compact via /compact]")
                    history[:] = auto_compact(
                        history,
                        client=self.client,
                        model=self.model_settings.model_id,
                        transcripts_dir=self.paths.transcripts_dir,
                    )
                continue
            if stripped == "/tasks":
                print(self.tasks.list_all())
                continue

            final_text, _ = self.run_prompt(stripped, history=history, verbose=True)
            if final_text:
                print(final_text)
            print()

    def agent_loop(self, messages: list[Message], *, verbose: bool = False) -> None:
        rounds_without_todo = 0
        while True:
            microcompact(messages)
            if estimate_tokens(messages) > TOKEN_THRESHOLD:
                if verbose:
                    print("[auto-compact triggered]")
                messages[:] = auto_compact(
                    messages,
                    client=self.client,
                    model=self.model_settings.model_id,
                    transcripts_dir=self.paths.transcripts_dir,
                )

            notifications = self.background.drain()
            if notifications:
                text = "\n".join(
                    f"[bg:{item['task_id']}] {item['status']}: {item['result']}"
                    for item in notifications
                )
                messages.append(
                    {
                        "role": "user",
                        "content": f"<background-results>\n{text}\n</background-results>",
                    }
                )
                messages.append(
                    {"role": "assistant", "content": "Noted background results."}
                )

            response = self.client.messages.create(
                model=self.model_settings.model_id,
                system=self.system_prompt,
                messages=messages,
                tools=self.tool_definitions,
                max_tokens=MAX_MODEL_TOKENS,
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return

            results = []
            used_todo = False
            manual_compact = False
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "compress":
                    manual_compact = True
                output = self.dispatch_tool(block.name, block.input)
                if verbose:
                    print(f"> {block.name}: {str(output)[:200]}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    }
                )
                if block.name == "TodoWrite":
                    used_todo = True

            rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
            if self.todo.has_open_items() and rounds_without_todo >= 3:
                results.insert(0, {"type": "text", "text": "<reminder>Update your todos.</reminder>"})
            messages.append({"role": "user", "content": results})

            if manual_compact:
                if verbose:
                    print("[manual compact]")
                messages[:] = auto_compact(
                    messages,
                    client=self.client,
                    model=self.model_settings.model_id,
                    transcripts_dir=self.paths.transcripts_dir,
                )

    def dispatch_tool(self, name: str, payload: dict[str, Any]) -> str:
        handlers = {
            "bash": lambda **kw: run_bash(
                self.paths.workspace,
                kw["command"],
            ),
            "read_file": lambda **kw: run_read(
                self.paths.workspace,
                kw["path"],
                kw.get("limit"),
            ),
            "write_file": lambda **kw: run_write(
                self.paths.workspace,
                kw["path"],
                kw["content"],
            ),
            "edit_file": lambda **kw: run_edit(
                self.paths.workspace,
                kw["path"],
                kw["old_text"],
                kw["new_text"],
            ),
            "TodoWrite": lambda **kw: self.todo.update(kw["items"]),
            "task": lambda **kw: self.run_subagent(
                kw["prompt"],
                kw.get("agent_type", "Explore"),
            ),
            "load_skill": lambda **kw: self.skills.load(kw["name"]),
            "compress": lambda **kw: "Compressing...",
            "background_run": lambda **kw: self.background.run(
                kw["command"],
                kw.get("timeout", 120),
            ),
            "check_background": lambda **kw: self.background.check(kw.get("task_id")),
            "task_create": lambda **kw: self.tasks.create(
                kw["subject"],
                kw.get("description", ""),
            ),
            "task_get": lambda **kw: self.tasks.get(kw["task_id"]),
            "task_update": lambda **kw: self.tasks.update(
                kw["task_id"],
                kw.get("status"),
                kw.get("add_blocked_by"),
                kw.get("add_blocks"),
            ),
            "task_list": lambda **kw: self.tasks.list_all(),
        }
        try:
            handler = handlers.get(name)
            return handler(**payload) if handler else f"Unknown tool: {name}"
        except Exception as exc:  # pragma: no cover - tool surface formatting
            return f"Error: {exc}"

    def run_subagent(self, prompt: str, agent_type: str = "Explore") -> str:
        tools = self.subagent_tool_definitions(agent_type)
        handlers = {
            "bash": lambda **kw: run_bash(self.paths.workspace, kw["command"]),
            "read_file": lambda **kw: run_read(self.paths.workspace, kw["path"]),
            "write_file": lambda **kw: run_write(
                self.paths.workspace,
                kw["path"],
                kw["content"],
            ),
            "edit_file": lambda **kw: run_edit(
                self.paths.workspace,
                kw["path"],
                kw["old_text"],
                kw["new_text"],
            ),
        }
        messages: list[Message] = [{"role": "user", "content": prompt}]
        response = None
        for _ in range(MAX_TURNS):
            response = self.client.messages.create(
                model=self.model_settings.model_id,
                messages=messages,
                tools=tools,
                max_tokens=MAX_MODEL_TOKENS,
            )
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                handler = handlers.get(block.name, lambda **kw: "Unknown tool")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(handler(**block.input))[:50000],
                    }
                )
            messages.append({"role": "user", "content": results})

        if response is None:
            return "(subagent failed)"
        return self.extract_text(response.content) or "(no summary)"

    @property
    def tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "bash",
                "description": "Run a shell command.",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read file contents.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "edit_file",
                "description": "Replace exact text in file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
            {
                "name": "TodoWrite",
                "description": "Update task tracking list.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"],
                                    },
                                    "activeForm": {"type": "string"},
                                },
                                "required": ["content", "status", "activeForm"],
                            },
                        }
                    },
                    "required": ["items"],
                },
            },
            {
                "name": "task",
                "description": "Spawn a subagent for isolated exploration or work.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "agent_type": {
                            "type": "string",
                            "enum": ["Explore", "general-purpose"],
                        },
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "load_skill",
                "description": "Load specialized knowledge by name.",
                "input_schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            {
                "name": "compress",
                "description": "Manually compress conversation context.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "background_run",
                "description": "Run command in a background thread.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "check_background",
                "description": "Check background task status.",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                },
            },
            {
                "name": "task_create",
                "description": "Create a persistent file task.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["subject"],
                },
            },
            {
                "name": "task_get",
                "description": "Get task details by ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "integer"}},
                    "required": ["task_id"],
                },
            },
            {
                "name": "task_update",
                "description": "Update task status or dependencies.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "deleted"],
                        },
                        "add_blocked_by": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "add_blocks": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": ["task_id"],
                },
            },
            {
                "name": "task_list",
                "description": "List all tasks.",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def subagent_tool_definitions(self, agent_type: str) -> list[dict[str, Any]]:
        tools = [
            {
                "name": "bash",
                "description": "Run command.",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
            {
                "name": "read_file",
                "description": "Read file.",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        ]
        if agent_type != "Explore":
            tools.extend(
                [
                    {
                        "name": "write_file",
                        "description": "Write file.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["path", "content"],
                        },
                    },
                    {
                        "name": "edit_file",
                        "description": "Edit file.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "old_text": {"type": "string"},
                                "new_text": {"type": "string"},
                            },
                            "required": ["path", "old_text", "new_text"],
                        },
                    },
                ]
            )
        return tools

    @staticmethod
    def extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        parts = []
        if isinstance(content, list):
            for block in content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
        return "\n".join(part.strip() for part in parts if part).strip()

    def extract_last_text(self, messages: list[Message]) -> str:
        for message in reversed(messages):
            if message.get("role") == "assistant":
                return self.extract_text(message.get("content"))
        return ""
