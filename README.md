# OtterCode

OtterCode is a local AI coding agent CLI for repository tasks. The current M1 build includes a working Anthropic-based `chat` and `run` runtime, local task storage, skill loading, context compaction, file tools, and background command support.

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
ottercode run "summarize this repository"
ottercode tasks list
ottercode resume sess_20260315_001
ottercode worktree list
```

## Current Scope

- `chat` and `run` execute the core agent loop
- `tasks list` reads the local `.tasks/` board
- worktree commands are still placeholders for the next milestone
- session persistence and resume are not implemented yet

## Project Layout

```text
otter-code/
  ottercode/
    cli.py
    config.py
    core/
      compact.py
      runtime.py
    tools/
      background.py
      bash.py
      files.py
      skills.py
      tasks.py
      todo.py
  pyproject.toml
  .env.example
  README.md
```
