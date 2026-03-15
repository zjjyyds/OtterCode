# OtterCode

OtterCode is a local AI coding agent CLI for repository tasks. The current M1 build includes an Anthropic-based `chat` and `run` runtime, JSONL session persistence, `resume`, local task storage, skill loading, context compaction, file tools, background command support, and git worktree orchestration.

## Quick Start

```bash
cd /home/jay/otter-code
cp .env.example .env
pip install -e .
ottercode --help
```

## Configure The Model

Set these values in `.env`:

```bash
ANTHROPIC_API_KEY=...
MODEL_ID=claude-sonnet-4-5
# Optional:
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

## Commands

```bash
ottercode chat
ottercode chat --yes
ottercode run "summarize this repository"
ottercode run --yes "apply the requested refactor"
ottercode tasks list
ottercode resume sess_20260315_001_abcdef
ottercode worktree create auth-refactor --task-id 12
ottercode worktree list
ottercode worktree status auth-refactor
ottercode worktree run auth-refactor "pytest tests/auth -q" --yes
ottercode worktree events --limit 20
ottercode worktree remove auth-refactor --force
```

## Session Storage

- Sessions are saved in `.ottercode/sessions/`
- `chat` starts a new session and prints the generated session id
- `run` saves the one-shot interaction as a resumable session
- `resume` reloads the saved JSONL history and continues interactively

## Permission Guard

- Risky shell mutations require approval by default
- `write_file` and `edit_file` require approval by default
- Use `--yes` to auto-approve guarded operations
- Approval records are appended to `.ottercode/logs/approvals.jsonl`

## Worktree Support

- Worktree state is tracked in `.worktrees/index.json`
- Lifecycle events are appended to `.worktrees/events.jsonl`
- `worktree create` can bind a worktree to a task id
- `worktree run` uses the same shell approval guard as the main runtime

## Current Scope

- `chat` and `run` execute the core agent loop
- `resume` restores saved conversation history
- `tasks list` reads the local `.tasks/` board
- `worktree create|list|status|run|remove|events` are implemented

## Project Layout

```text
otter-code/
  ottercode/
    cli.py
    config.py
    core/
      compact.py
      runtime.py
      session.py
    tools/
      background.py
      bash.py
      files.py
      permissions.py
      skills.py
      tasks.py
      todo.py
    worktree/
      events.py
      manager.py
  pyproject.toml
  .env.example
  README.md
```
