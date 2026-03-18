from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from agent.loop import AgentLoop
from agent.prompts import build_system_prompt
from config import AppConfig
from runtime.filesystem import Filesystem
from runtime.subprocess_runner import SubprocessRunner
from skills.discovery import discover_skills
from skills.registry import SkillRegistry
from tools.bash import BashTool
from tools.read import ReadTool


class OpenAICompatibleModelClient:
    def __init__(self, api_base: str, api_key: str, model_name: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name

    import time  # 记得在 app.py 顶部导入 time 模块

    def complete(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "temperature": 0,
            "max_tokens": 8192,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
        }

        # ====== 新增：增加 3 次自动重试机制 ======
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=300,
                )
                resp.raise_for_status()
                data = resp.json()
                break  # 如果成功了，就跳出循环
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    # 如果最后一次还是失败，再向上抛出异常
                    raise ValueError(f"API 请求失败，已重试 {max_retries} 次。最后错误: {e}")

                print(f"⚠️  [网络波动] API 连接断开 ({e})，正在进行第 {attempt + 1} 次重试...")
                time.sleep(2)  # 停顿 2 秒再试
        # ==========================================

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
            return "".join(chunks).strip()

        raise ValueError(f"unexpected model content: {content!r}")


@dataclass
class MiniApp:
    loop: AgentLoop
    loaded_skills: list[str]
    warnings: list[str]


def build_app(config: AppConfig) -> MiniApp:
    discovered = discover_skills(config.skill_roots())
    registry = SkillRegistry.build(discovered)

    fs = Filesystem(
        project_dir=config.project_dir,
        allowed_roots=config.allowed_roots(),
        read_max_bytes=config.read_max_bytes,
    )
    runner = SubprocessRunner(fs, timeout_sec=config.bash_timeout_sec)

    tools = {
        "Read": ReadTool(fs),
        "Bash": BashTool(runner),
    }

    tools_text = "\n".join(tool.prompt_block() for tool in tools.values())
    system_prompt = build_system_prompt(registry, tools_text)

    model_client = OpenAICompatibleModelClient(
        api_base=config.api_base,
        api_key=config.api_key,
        model_name=config.model_name,
    )

    loop = AgentLoop(
        model_client=model_client,
        registry=registry,
        tools=tools,
        system_prompt=system_prompt,
        max_steps=config.max_steps,
    )

    return MiniApp(
        loop=loop,
        loaded_skills=registry.names(),
        warnings=registry.warnings,
    )