from __future__ import annotations

from pathlib import Path


class FilesystemError(ValueError):
    pass


class Filesystem:
    def __init__(self, project_dir: Path, allowed_roots: list[Path], read_max_bytes: int = 120_000) -> None:
        self.project_dir = project_dir.resolve()
        self.allowed_roots = [p.resolve() for p in allowed_roots]
        self.read_max_bytes = read_max_bytes

    def _is_allowed(self, path: Path) -> bool:
        path = path.resolve()
        for root in self.allowed_roots:
            if path == root or root in path.parents:
                return True
        return False

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = (self.project_dir / path).resolve()
        else:
            path = path.resolve()

        if not self._is_allowed(path):
            raise FilesystemError(f"path not allowed: {path}")

        return path

    def read_text(self, raw_path: str) -> dict:
        path = self.resolve_path(raw_path)
        if not path.exists():
            raise FilesystemError(f"file not found: {path}")
        if not path.is_file():
            raise FilesystemError(f"not a file: {path}")

        raw = path.read_bytes()
        truncated = len(raw) > self.read_max_bytes
        if truncated:
            raw = raw[: self.read_max_bytes]

        return {
            "path": str(path),
            "content": raw.decode("utf-8", errors="replace"),
            "truncated": truncated,
        }