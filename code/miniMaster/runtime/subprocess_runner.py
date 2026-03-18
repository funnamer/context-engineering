from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .filesystem import Filesystem


class SubprocessRunner:
    def __init__(self, fs: Filesystem, timeout_sec: int = 20) -> None:
        self.fs = fs
        self.timeout_sec = timeout_sec

    def run(self, command: str, cwd: str | None = None) -> dict:
        workdir = self.fs.project_dir if cwd is None else self.fs.resolve_path(cwd)
        if not workdir.is_dir():
            raise ValueError(f"cwd is not a directory: {workdir}")

        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(Path.home()),
            "PYTHONUNBUFFERED": "1",
        }

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(workdir),
                env=env,
                text=True,
                capture_output=True,
                timeout=self.timeout_sec,
                stdin=subprocess.DEVNULL,
            )
            return {
                "command": command,
                "cwd": str(workdir),
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "cwd": str(workdir),
                "exit_code": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timed_out": True,
            }