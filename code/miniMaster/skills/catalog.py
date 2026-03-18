from __future__ import annotations

from xml.sax.saxutils import escape

from .registry import SkillRegistry


def render_skill_catalog(registry: SkillRegistry) -> str:
    skills = registry.all()
    if not skills:
        return ""

    lines = ["<available_skills>"]
    for skill in skills:
        lines.extend(
            [
                "  <skill>",
                f"    <name>{escape(skill.name)}</name>",
                f"    <description>{escape(skill.description)}</description>",
                f"    <location>{escape(str(skill.location))}</location>",
                "  </skill>",
            ]
        )
    lines.append("</available_skills>")
    return "\n".join(lines)