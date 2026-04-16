# miniMaster

本项目是一个极简的实例，着重实现维护agent长期运行稳定的方法，快速体验harness的核心理念

## 1. Tool 设计

### 1.1 基础系统工具 (Base Tools)

`base_tool` 目录提供 Agent 与系统交互的基础能力：

* **Bash Tool**：执行命令，支持超时控制，并根据当前系统选择合适的底层 shell。
* **Read Tool**：读取文件内容，支持按行范围读取，适合做局部代码检查。
* **Write Tool**：写入文件内容，支持覆盖、追加、新建等常见写入方式。
* **Edit Tool**：在已有文件上做精确替换，适合小范围修改代码或文档。

### 1.2 搜索检索工具 (Search Tools)

`search_tool` 目录提供文件和文本检索能力：

* **Glob Tool**：按通配符查找文件，支持递归搜索。
* **Grep Tool**：按正则表达式搜索文本，支持目录递归和结果结构化返回。

### 1.3 工具核心层 (Tool Core)

`tools/core/` 是工具系统的管理框架，负责统一发现、登记、实例化和执行工具。具体工具只需要关心自己的业务逻辑，而公共问题（工具注册、实例复用、执行入口、Prompt 渲染）则交给核心层处理。

* **BaseTool**：所有工具的基类，负责参数校验、路径解析和统一执行包装。
* **ToolSpec / ToolContext / ToolResult**：分别定义工具的静态元信息、运行时上下文和返回结果格式。
* **ToolCatalog**：保存所有已注册工具的元数据与构造器映射。
* **discover_tools**：自动扫描 `tools/` 目录并注册符合约定的工具类。
* **ToolService**：为上层提供稳定入口，统一完成工具发现、Prompt 渲染和工具执行。

这种分层设计使新增工具时无需重复实现注册、错误处理、Prompt 描述等通用逻辑，也让主循环可以只依赖一个稳定的工具服务入口。

### 1.4 统一的接口设计

所有工具遵循一致的接口规范：

* **结构化元信息**：通过 `ToolSpec` 声明工具名称、说明、分类和输入 schema。
* **统一执行上下文**：所有工具共享 `ToolContext`，统一理解工作目录与运行环境。
* **标准化执行流程**：业务逻辑封装在 `run()` 方法中，对外统一通过 `execute()` 调用。
* **统一服务入口**：主程序通过 `ToolService` 使用工具系统，不再手写分散的注册与调度逻辑。
* **控制动作分流**：像 `init_tasks`、`respond_to_user`、`validate_tool` 这类动作由主循环处理，真实文件/搜索/命令能力才进入工具执行链。

---

## 2. Prompt 设计与动作协议 (Prompting)

在 miniMaster 里，Prompt 已经不再是散落在主循环里的长字符串，而是被拆到 `prompting/` 模块中统一管理。这样做的核心目的，是让**角色职责、动作边界、输出协议**三件事保持一致，避免“Prompt 里写一套、代码里校验另一套”。

### 2.1 Prompt 构造层

`builders.py` 负责构造不同阶段的 Prompt：

* **`build_plan_prompt()`**：为 Plan-Agent 生成调度提示词，让它决定是直接回复用户，还是初始化任务、推进已有任务。
* **`build_generator_prompt()`**：为 Generator-Agent 生成执行提示词，把当前任务、工作记忆、工具说明和动作限制组合起来。
* **`build_validate_prompt()`**：为 Validate-Agent 生成验证提示词，要求它独立判断结论是否真的成立。
* **`build_summary_prompt()`**：为记忆压缩流程生成摘要提示词，用于在长任务中合并旧记忆。
* **`build_execution_context_block()`**：把工作目录、系统类型和底层命令 shell 组织成统一的 system prompt 上下文，让模型更稳定地理解“当前目录”“这里”“本项目”这类说法。

### 2.2 动作策略层

`policies.py` 负责定义每一类 Agent 可以做什么，不同角色拥有不同的动作边界：

* **Plan-Agent**：只开放 `init_tasks`、`add_task`、`update_task_status`、`subagent_tool`、`respond_to_user` 这类高层动作。
* **Generator-Agent**：开放 `bash`、`read`、`write`、`edit`、`glob`、`grep` 等执行能力，并允许通过 `update_task_conclusion` 提交任务结论。
* **Validate-Agent**：保留 `bash`、`read`、`glob`、`grep` 等验证能力，并强制通过 `validate_tool` 输出最终判断。

这种设计的好处很直接：Plan 不越权去改文件，Validate 不偷偷完成任务，Generator 也不能跳过验证层直接宣布全局结束。

### 2.3 原生 function call 协议

这里不再依赖手写 XML 标签或自由格式文本，而是改为调用模型的原生 function call 能力。`protocol.py` 负责完成三件事：

* 把结构化动作策略转换成 OpenAI `tools` 定义；
* 解析模型返回的 function call；
* 根据 policy 和 schema 校验动作是否合法。

这意味着模型输出的不是一段“看起来像工具调用”的文本，而是真正可被程序直接解析、验证和执行的结构化动作。这样不仅减少了格式漂移，也让主循环逻辑更清晰。

### 2.4 统一的模型调用入口

`app/agent_runner.py` 把“发起模型请求 -> 拿到 function call -> 校验动作合法性”这一整套流程统一封装为 `request_agent_action()`。主循环只需要在不同阶段准备好 Prompt、policy 和 tool schema，就能得到一个合法的 `AgentAction`。

从教学角度看，这一步非常关键。因为它把“调用模型”从“编排逻辑”里拆了出来，使学生在阅读 `orchestration.py` 时，可以更专注地理解 Agent 的协作过程，而不是被 API 细节分散注意力。

---

## 3. 状态管理与动态工作记忆 (State Management)

在 harness 的设计中，状态和记忆管理十分重要，让 agent 知道各个任务的状态，也让它记得自己曾经采取过什么样的行动，从而更稳定地做出下一步决策。
任何一个需要持续工作的 Agent，都面临一个核心技术挑战：**如何平衡不断增长的执行记录与 LLM 有限的上下文窗口(Token 限制)?** 如果像"金鱼"一样只有短暂记忆，Agent 就会陷入死循环；但如果把所有历史都毫无保留地塞进 Prompt，不仅会导致 Token 溢出，还会让模型越来越难抓住重点。

为了解决这个问题，在当前架构中，状态管理被清晰地拆成了"宏观"和"微观"两层。宏观层面由 `ToDoList` 负责，维护整张任务看板；微观层面由 `WorkingMemory` 负责，维护每个 Agent 在执行阶段和验证阶段看到的近期轨迹。

在这套实现里，系统额外加入了**记忆结果压缩**。也就是说，不只是“旧记忆整体做摘要”，连单次工具输出在进入工作记忆前，也会先被裁剪成更适合继续喂给模型的大小。下面是核心思路：

```python
class WorkingMemory:
    def __init__(self, keep_latest_n: int = 3, max_chars: int = DEFAULT_WORKING_MEMORY_MAX_CHARS):
        self.memories = []
        self.keep_latest_n = keep_latest_n
        self.max_chars = max_chars
        self.summary = ""

    def add_memory(self, step: int, tool_name: str, parameters: dict, result):
        self.memories.append(
            MemoryEntry(
                step=step,
                tool_call=MemoryToolCall(
                    tool_name=tool_name,
                    parameters=compact_for_memory(parameters),
                ),
                result=prepare_memory_result(tool_name, result),
            )
        )

    def check_needs_summary(self) -> bool:
        current_length = len(self.get_prompt_context())
        return current_length > self.max_chars and len(self.memories) > self.keep_latest_n

    def commit_summary(self, new_summary: str):
        self.summary = new_summary
        self.memories = self.memories[-self.keep_latest_n:]
```

### 3.1 记忆控制策略

1. **单次结果先压缩**
   `compact_for_memory()` 和 `prepare_memory_result()` 会先把超长的 `stdout`、`content`、匹配列表等结果压缩成适合放进 Prompt 的预览结构，避免单次工具输出直接撑爆上下文。
2. **超过阈值再做摘要**
   当 `WorkingMemory` 的整体长度超过 `max_chars`，系统才会触发摘要流程，把较早的执行记录交给 Summary-Agent 压缩。
3. **始终保留最近几步完整轨迹**
   通过 `keep_latest_n`，系统会强制保留最近若干步的详细记录，保证 Agent 在当前任务里仍然拥有连续的局部上下文。

### 3.2 任务状态管理

`runtime/todo.py` 中的 `ToDoList` 不再只是一个简单列表，而是整个流程中的状态看板：

* 负责初始化任务列表；
* 负责维护 `PENDING / DONE / FAILED` 等状态；
* 负责记录每个任务最终的结论；
* 负责把任务对象转换成 Prompt 可直接使用的 payload。

这种设计的价值在于：Plan-Agent、Generator-Agent、Validate-Agent 虽然职责不同，但都围绕同一份任务状态展开工作，不会各自维护一套互相漂移的任务视图。

---

## 4. 多智能体编排 (multi-agent Orchestration)

miniMaster 采用的是**"规划-执行-验证"三层嵌套循环 (Plan-Generate-Validate)** 的多智能体协作架构。各个 Agent 遵循 ReAct 风格的“观察-决策-行动”模式，但又通过结构化动作协议和状态管理保证行为边界。相对于只做 plan & solve 的方式，这里额外补上了 validate 和重复动作防护，从而让系统在长期任务中更稳定。

### 4.1 Plan-Agent (全局调度)

Plan-Agent 是整个系统的大脑。它不直接读写文件，也不直接执行搜索，而是判断用户输入属于哪一类，再决定下一步动作：

* 如果只是问候、闲聊、咨询能力，就直接 `respond_to_user`；
* 如果是明确任务，就通过 `init_tasks` 或 `add_task` 维护任务列表；
* 如果当前已经有未完成任务，就优先通过 `subagent_tool` 推进已有任务。

这种设计让顶层循环不仅能处理复杂任务，也能自然处理简单问答，不必把所有输入都硬塞进任务系统。

### 4.2 Generator-Agent (执行者)

当 `subagent_tool` 被触发后，系统进入 Generator 内层循环。它是真正执行任务的角色，会反复在“选动作 -> 执行工具 -> 把结果写入工作记忆”之间循环。

在这套实现里，Generator 除了能调用基础工具和搜索工具，还多了两层稳定性设计：

* **工具结果缓存**：`glob`、`grep`、`read` 等只读工具支持按参数缓存，减少重复调用；
* **重复动作拦截**：如果 Generator 连续发出完全相同的动作，系统会把反馈写回 `system_feedback`，强制它换一种推进方式。

当 Generator 认为任务已经完成时，它不能直接把任务标记为 done，而是必须通过 `update_task_conclusion` 提交结论，再交给验证层判断。

### 4.3 Validate-Agent (评估者)

Validate-Agent 的职责不是继续做任务，而是检查“当前结论是否真的被现有证据支持”。它会读取当前任务结论、执行历史和验证阶段工作记忆，必要时再调用 `read`、`grep`、`glob`、`bash` 做补充核查，最后必须通过 `validate_tool` 输出 `有效` 或 `无效`。

如果判定为 `无效`，系统不会简单报错结束，而是把失败原因转换成新的 `system_feedback` 注入 Generator 的工作记忆中。随后流程重新回到 Generator，让它基于这条具体反馈继续修正。

这就形成了一个真正的**纠错闭环（Feedback Loop）**：

* Generator 先尝试完成任务；
* Validate 检查结论是否成立；
* 如果不成立，把具体原因反馈回去；
* Generator 必须直接回应这条失败原因，而不是机械重复之前的动作。

### 4.4 编排细节

在 `app/orchestration.py` 中，除了三层循环本身，当前实现还补充了几项很关键的工程细节：

* **共享 stage context**：把 system prompt、可用工具 schema、工具说明文本统一提前构造，减少循环内重复组装。
* **任务级记忆重置**：每次新任务开始时，Generator 和 Validate 都会重新初始化自己的工作记忆。
* **重复验证收口**：Validate 如果已经具备足够证据，就必须尽快 `validate_tool` 收口，不能反复做相同验证。
* **运行时工具与控制动作分离**：控制动作由主循环处理，真实工具才进入 `ToolService.execute()`。

从教学角度看，这些细节比“能跑起来”更重要。因为一个真正可长期运行的 Agent 系统，问题往往不在于有没有工具，而在于**工具、Prompt、状态和循环编排能不能彼此对齐**。miniMaster 做的，就是把这些关键拼图组织成一套尽可能清晰、可扩展、可讲解的最小实现。
