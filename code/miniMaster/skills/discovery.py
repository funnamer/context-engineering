from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscoveredSkill:
    skill_dir: Path
    skill_md_path: Path
    source_root: Path


def discover_skills(skill_roots: list[Path]) -> list[DiscoveredSkill]:
    found: list[DiscoveredSkill] = []

    for root in skill_roots:
        root = root.resolve()
        if not root.exists() or not root.is_dir():
            continue

        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            skill_md = child / "SKILL.md"
            if skill_md.is_file():
                found.append(
                    DiscoveredSkill(
                        skill_dir=child.resolve(),
                        skill_md_path=skill_md.resolve(),
                        source_root=root,
                    )
                )

    return found