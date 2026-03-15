from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

Message = dict[str, Any]


def estimate_tokens(messages: list[Message]) -> int:
    return len(json.dumps(messages, default=str)) // 4


def microcompact(messages: list[Message]) -> None:
    results = []
    for message in messages:
        if message.get("role") == "user" and isinstance(message.get("content"), list):
            for part in message["content"]:
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    results.append(part)
    if len(results) <= 3:
        return
    for part in results[:-3]:
        if isinstance(part.get("content"), str) and len(part["content"]) > 100:
            part["content"] = "[cleared]"


def auto_compact(
    messages: list[Message],
    *,
    client: Any,
    model: str,
    transcripts_dir: Path,
) -> list[Message]:
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcripts_dir / f"transcript_{int(time.time())}.jsonl"
    with transcript_path.open("w", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(message, default=str) + "\n")

    conversation = json.dumps(messages, default=str)[:80000]
    response = client.messages.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": f"Summarize for continuity:\n{conversation}",
            }
        ],
        max_tokens=2000,
    )
    summary = "".join(
        getattr(block, "text", "") for block in response.content if hasattr(block, "text")
    ).strip() or "(summary unavailable)"
    return [
        {
            "role": "user",
            "content": f"[Compressed. Transcript: {transcript_path}]\n{summary}",
        },
        {
            "role": "assistant",
            "content": "Understood. Continuing with summary context.",
        },
    ]
