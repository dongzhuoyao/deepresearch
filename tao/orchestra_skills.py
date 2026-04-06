"""Orchestra external skills integration."""
from __future__ import annotations
from pathlib import Path
from typing import Any


def scan_skills(skills_dir: str, max_skills: int = 15) -> list[dict]:
    """Scan external skills directory and build index."""
    skills_path = Path(skills_dir).expanduser()
    if not skills_path.is_dir():
        return []

    skills = []
    for skill_file in sorted(skills_path.glob("*.md")):
        name = skill_file.stem
        # Read first line for description
        content = skill_file.read_text(encoding="utf-8")
        first_line = content.split("\n")[0].strip().lstrip("#").strip()
        skills.append({"name": name, "description": first_line, "path": str(skill_file)})
        if len(skills) >= max_skills:
            break

    return skills


def format_skills_index(skills: list[dict]) -> str:
    """Format skills as a markdown index for injection into prompts."""
    if not skills:
        return ""
    lines = ["## Available Technical Skills\n"]
    lines.append("You may invoke these skills when needed:\n")
    for skill in skills:
        lines.append(f"- **{skill['name']}**: {skill['description']}")
    return "\n".join(lines)


def build_skills_section(skills_dir: str, max_skills: int = 15) -> str:
    """Scan and format skills in one call."""
    skills = scan_skills(skills_dir, max_skills)
    return format_skills_index(skills)
