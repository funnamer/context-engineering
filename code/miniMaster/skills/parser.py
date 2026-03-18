from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillParseError(ValueError):
    pass


@dataclass
class ParsedSkill:
    name: str
    description: str
    body: str
    skill_dir: Path
    skill_md_path: Path
    raw_text: str


def parse_skill_file(skill_md_path: Path) -> ParsedSkill:
    skill_md_path = skill_md_path.resolve()

    if skill_md_path.name != "SKILL.md":
        raise SkillParseError(f"not a SKILL.md file: {skill_md_path}")

    raw_text = skill_md_path.read_text(encoding="utf-8", errors="replace")
    match = _FRONTMATTER_RE.match(raw_text)
    if not match:
        raise SkillParseError(f"{skill_md_path} missing YAML frontmatter")

    frontmatter_text, body = match.group(1), match.group(2)

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"invalid YAML frontmatter: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise SkillParseError("frontmatter must be a mapping")

    name = str(frontmatter.get("name", "")).strip()
    description = str(frontmatter.get("description", "")).strip()

    if not name:
        raise SkillParseError("missing required field: name")
    if not description:
        raise SkillParseError("missing required field: description")

    # 极简兼容：只做轻量校验，不阻止加载目录名不一致的 skill
    if not _NAME_RE.match(name):
        raise SkillParseError(
            f"invalid skill name '{name}': only lowercase letters, numbers, and hyphens allowed"
        )

    return ParsedSkill(
        name=name,
        description=description,
        body=body.lstrip("\n"),
        skill_dir=skill_md_path.parent,
        skill_md_path=skill_md_path,
        raw_text=raw_text,
    )