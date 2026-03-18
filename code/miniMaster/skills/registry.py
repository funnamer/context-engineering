from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .discovery import DiscoveredSkill
from .parser import SkillParseError, parse_skill_file


@dataclass
class SkillRecord:
    name: str
    description: str
    location: Path
    skill_dir: Path


class SkillRegistry:
    def __init__(self, skills: dict[str, SkillRecord], warnings: list[str]) -> None:
        self._skills = skills
        self.warnings = warnings

    @classmethod
    def build(cls, discovered: list[DiscoveredSkill]) -> "SkillRegistry":
        skills: dict[str, SkillRecord] = {}
        warnings: list[str] = []

        for item in discovered:
            try:
                parsed = parse_skill_file(item.skill_md_path)
            except SkillParseError as exc:
                warnings.append(f"skip {item.skill_md_path}: {exc}")
                continue

            record = SkillRecord(
                name=parsed.name,
                description=parsed.description,
                location=parsed.skill_md_path,
                skill_dir=parsed.skill_dir,
            )

            # 极简冲突规则：后发现的忽略
            if record.name in skills:
                warnings.append(
                    f"duplicate skill name '{record.name}', ignore {record.location}"
                )
                continue

            skills[record.name] = record

        return cls(skills, warnings)

    def get(self, name: str) -> SkillRecord | None:
        return self._skills.get(name)

    def all(self) -> list[SkillRecord]:
        return sorted(self._skills.values(), key=lambda x: x.name)

    def names(self) -> list[str]:
        return [s.name for s in self.all()]