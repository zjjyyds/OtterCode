from __future__ import annotations

import re
from pathlib import Path


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills: dict[str, dict[str, str | dict[str, str]]] = {}
        if not skills_dir.exists():
            return
        for file in sorted(skills_dir.rglob("SKILL.md")):
            text = file.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
            metadata: dict[str, str] = {}
            body = text
            if match:
                for line in match.group(1).strip().splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()
                body = match.group(2).strip()
            name = metadata.get("name", file.parent.name)
            self.skills[name] = {"meta": metadata, "body": body}

    def descriptions(self) -> str:
        if not self.skills:
            return "(no skills)"
        return "\n".join(
            f"  - {name}: {skill['meta'].get('description', '-')}"
            for name, skill in self.skills.items()
        )

    def load(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            available = ", ".join(self.skills.keys())
            return f"Error: Unknown skill '{name}'. Available: {available}"
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
