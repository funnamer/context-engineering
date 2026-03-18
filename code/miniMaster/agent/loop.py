from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from skills.registry import SkillRecord, SkillRegistry


class ModelClient(Protocol):
    def complete(self, system_prompt: str, messages: list[dict[str, str]]) -> str: ...


class Tool(Protocol):
    name: str
    def run(self, tool_input: dict) -> dict: ...


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class AgentLoop:
    def __init__(
        self,
        model_client: ModelClient,
        registry: SkillRegistry,
        tools: dict[str, Tool],
        system_prompt: str,
        max_steps: int = 8,
    ) -> None:
        self.model_client = model_client
        self.registry = registry
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.messages: list[dict[str, str]] = []

    def run_turn(self, user_text: str) -> str:
        # 1. 拦截并解析所有的 /skill 命令
        activated_skills, rest = self._intercept_slash_skills(user_text)

        # 2. 将所有匹配到的技能内容注入 System Prompt
        for skill in activated_skills:
            skill_text = Path(skill.location).read_text(encoding="utf-8", errors="replace")
            self.messages.append(
                {
                    "role": "system",
                    "content": (
                        f"<activated_skill name=\"{skill.name}\">\n"
                        f"{skill_text}\n"
                        f"</activated_skill>"
                    ),
                }
            )

        # 如果只有 / 命令，没有正文，则直接返回已激活的技能名称
        if activated_skills and not rest:
            names = ", ".join(s.name for s in activated_skills)
            return f"Activated skills: {names}"

        if rest:
            self.messages.append({"role": "user", "content": rest})

        for _ in range(self.max_steps):
            raw = self.model_client.complete(self.system_prompt, self.messages)
            action = self._parse_json(raw)

            # ====== 新增：打印 Agent 的思考和动作 ======
            print("-" * 40)
            if "thought" in action:
                print(f"🤔 [思考]: {action['thought']}")
            # ============================================

            if action["type"] == "final":
                answer = str(action["content"])
                self.messages.append({"role": "assistant", "content": answer})
                return answer

            if action["type"] != "tool_call":
                raise ValueError(f"unknown action type: {action['type']}")

            tool_name = str(action["tool"])
            tool_input = action.get("input", {})

            # ====== 新增：打印工具调用状态 ======
            print(f"🛠️  [调用工具]: {tool_name}")
            print(f"📦 [工具参数]: {json.dumps(tool_input, ensure_ascii=False)}")
            # ====================================

            if tool_name not in self.tools:
                result = {"ok": False, "error": f"unknown tool: {tool_name}"}
            else:
                try:
                    tool_result = self.tools[tool_name].run(tool_input)
                    result = {"ok": True, "result": tool_result}
                except Exception as exc:  # noqa: BLE001
                    result = {"ok": False, "error": str(exc)}

            self.messages.append({"role": "assistant", "content": raw})
            self.messages.append(
                {
                    "role": "user",
                    "content": (
                        f"<tool_result name=\"{tool_name}\">\n"
                        f"{json.dumps(result, ensure_ascii=False, indent=2)}\n"
                        f"</tool_result>\n"
                        "Continue."
                    ),
                }
            )

        raise RuntimeError("max_steps exceeded")

    def _intercept_slash_skills(self, text: str) -> tuple[list[SkillRecord], str]:
        """解析文本开头所有的 /skill 命令，直到遇到不是 / 开头的词汇"""
        words = text.strip().split()
        skills_found: list[SkillRecord] = []
        rest_words: list[str] = []

        parsing_skills = True
        for word in words:
            if parsing_skills and word.startswith("/"):
                name = word[1:].strip()
                skill = self.registry.get(name)
                if skill:
                    skills_found.append(skill)
                else:
                    # 如果找不到对应的技能，则把它当成普通文本，停止解析命令
                    rest_words.append(word)
                    parsing_skills = False
            else:
                rest_words.append(word)
                parsing_skills = False

        return skills_found, " ".join(rest_words)

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_RE.search(text)
            if not match:
                raise ValueError(f"model did not return valid JSON: {text}")
            return json.loads(match.group(0))