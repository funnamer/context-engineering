from __future__ import annotations

import json

from runtime.subprocess_runner import SubprocessRunner


class BashTool:
    name = "Bash"
    description = "Run a shell command."

    def __init__(self, runner: SubprocessRunner) -> None:
        self.runner = runner

    def prompt_block(self) -> str:
        schema = {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["command"],
            "additionalProperties": False,
        }
        return f"- {self.name}: {self.description}\n  Input schema: {json.dumps(schema, ensure_ascii=False)}"

    def run(self, tool_input: dict) -> dict:
        return self.runner.run(
            command=str(tool_input["command"]),
            cwd=str(tool_input["cwd"]) if "cwd" in tool_input and tool_input["cwd"] else None,
        )