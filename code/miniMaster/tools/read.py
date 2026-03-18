from __future__ import annotations

import json

from runtime.filesystem import Filesystem


class ReadTool:
    name = "Read"
    description = "Read a text file."

    def __init__(self, fs: Filesystem) -> None:
        self.fs = fs

    def prompt_block(self) -> str:
        schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"],
            "additionalProperties": False,
        }
        return f"- {self.name}: {self.description}\n  Input schema: {json.dumps(schema, ensure_ascii=False)}"

    def run(self, tool_input: dict) -> dict:
        return self.fs.read_text(str(tool_input["path"]))