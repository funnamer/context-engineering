from __future__ import annotations

from skills.catalog import render_skill_catalog
from skills.registry import SkillRegistry
from skills.catalog import render_skill_catalog
from skills.registry import SkillRegistry


def build_system_prompt(registry: SkillRegistry, tools_text: str) -> str:
    parts: list[str] = []

    parts.append(
        (
            "You are a minimal coding agent with Agent Skills support.\n"
            "You must respond with exactly one JSON object and nothing else.\n\n"
            "Allowed output shapes:\n"
            '{"thought": "reasoning about what to do next...", "type":"tool_call","tool":"Read|Bash","input":{...}}\n'
            '{"thought": "ready to answer user...", "type":"final","content":"..."}\n\n'
            "Rules:\n"
            "1. Always use the 'thought' field to explicitly plan your steps before taking action.\n"
            "2. If a task requires multiple steps or skills (e.g., extract PDF then generate PPT), plan the sequence in 'thought'.\n"
            "3. If a task matches a skill description, use the Read tool to load that skill's SKILL.md file first.\n"
            "4. Prefer Read for loading skill files and references.\n"
            "5. Use Bash only when execution is actually needed.\n"
            "6. When a skill references relative paths, resolve them relative to the skill directory.\n"
            "7. Never output markdown outside of JSON. Only output valid JSON."
        )
    )

    parts.append("Available tools:\n" + tools_text)

    catalog = render_skill_catalog(registry)
    if catalog:
        parts.append("Available skills:\n" + catalog)

    return "\n\n".join(parts)