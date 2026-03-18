from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    project_dir: Path
    home_dir: Path
    api_base: str
    api_key: str
    model_name: str
    max_steps: int = 12
    bash_timeout_sec: int = 20
    read_max_bytes: int = 120_000

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            project_dir=Path(os.getenv("MCC_PROJECT_DIR", os.getcwd())).resolve(),
            home_dir=Path(os.getenv("MCC_HOME_DIR", str(Path.home()))).expanduser().resolve(),
            api_base=os.getenv("MCC_API_BASE", "https://api.openai.com/v1"),
            api_key=os.getenv("MCC_API_KEY", ""),
            model_name=os.getenv("MCC_MODEL_NAME", "gpt-4.1-mini"),
            max_steps=int(os.getenv("MCC_MAX_STEPS", "8")),
            bash_timeout_sec=int(os.getenv("MCC_BASH_TIMEOUT_SEC", "20")),
            read_max_bytes=int(os.getenv("MCC_READ_MAX_BYTES", "120000")),
        )

    def skill_roots(self) -> list[Path]:
        return [
            self.project_dir / ".claude" / "skills",
            self.project_dir / ".agents" / "skills",
            self.home_dir / ".claude" / "skills",
            self.home_dir / ".agents" / "skills",
        ]

    def allowed_roots(self) -> list[Path]:
        roots = [self.project_dir]
        roots.extend(self.skill_roots())
        out: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root.resolve())
            if key not in seen:
                seen.add(key)
                out.append(root.resolve())
        return out