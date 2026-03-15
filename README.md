# OtterCode

OtterCode is a local AI coding agent CLI for repository tasks. The current M1 build includes an Anthropic-based `chat` and `run` runtime, JSONL session persistence, `resume`, local task storage, skill loading, context compaction, file tools, and background command support.

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
ottercode worktree list
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

## Current Scope

- `chat` and `run` execute the core agent loop
- `resume` restores saved conversation history
- `tasks list` reads the local `.tasks/` board
- worktree commands are still placeholders for the next milestone

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
  pyproject.toml
  .env.example
  README.md
```
