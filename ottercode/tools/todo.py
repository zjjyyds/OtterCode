from __future__ import annotations


class TodoManager:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def update(self, items: list[dict[str, str]]) -> str:
        validated: list[dict[str, str]] = []
        in_progress = 0
        for index, item in enumerate(items):
            content = str(item.get("content", "")).strip()
            status = str(item.get("status", "pending")).lower()
            active_form = str(item.get("activeForm", "")).strip()
            if not content:
                raise ValueError(f"Item {index}: content required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {index}: invalid status '{status}'")
            if not active_form:
                raise ValueError(f"Item {index}: activeForm required")
            if status == "in_progress":
                in_progress += 1
            validated.append(
                {
                    "content": content,
                    "status": status,
                    "activeForm": active_form,
                }
            )
        if len(validated) > 20:
            raise ValueError("Max 20 todos")
        if in_progress > 1:
            raise ValueError("Only one in_progress allowed")
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            marker = {
                "completed": "[x]",
                "in_progress": "[>]",
                "pending": "[ ]",
            }.get(item["status"], "[?]")
            suffix = f" <- {item['activeForm']}" if item["status"] == "in_progress" else ""
            lines.append(f"{marker} {item['content']}{suffix}")
        done = sum(1 for item in self.items if item["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)

    def has_open_items(self) -> bool:
        return any(item.get("status") != "completed" for item in self.items)
