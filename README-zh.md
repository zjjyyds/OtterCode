[English](./README.md) | [中文](./README-zh.md)

# OtterCode

OtterCode 是一个面向本地代码仓任务执行的 AI Coding Agent CLI。当前 M1 版本已经包含基于 Anthropic 的 `chat` 和 `run` 运行时、JSONL 会话持久化、`resume`、本地任务存储、技能加载、上下文压缩、文件工具、后台命令支持，以及 git worktree 编排能力。

## 快速开始

```bash
cd /home/jay/otter-code
cp .env.example .env
pip install -e .
ottercode --help
```

## 模型配置

在 `.env` 中配置这些值：

```bash
ANTHROPIC_API_KEY=...
MODEL_ID=claude-sonnet-4-5
# 可选：
# ANTHROPIC_BASE_URL=https://api.anthropic.com
```

## 命令示例

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

## 会话存储

- 会话会保存到 `.ottercode/sessions/`
- `chat` 会创建新会话并打印生成的 session id
- `run` 会把一次性执行保存成可恢复的会话
- `resume` 会重新加载保存的 JSONL 历史并继续交互

## 权限治理

- 默认情况下，存在风险的 shell 变更操作需要审批
- `write_file` 和 `edit_file` 默认需要审批
- 使用 `--yes` 可以自动批准受保护的操作
- 审批记录会追加写入 `.ottercode/logs/approvals.jsonl`

## Worktree 支持

- worktree 状态保存在 `.worktrees/index.json`
- 生命周期事件会追加写入 `.worktrees/events.jsonl`
- `worktree create` 可以把 worktree 绑定到 task id
- `worktree run` 复用了主运行时的 shell 权限审批逻辑

## 当前范围

- `chat` 和 `run` 执行核心 agent loop
- `resume` 恢复保存的会话历史
- `tasks list` 读取本地 `.tasks/` 看板
- `worktree create|list|status|run|remove|events` 已实现

## 项目结构

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
  README-zh.md
```
