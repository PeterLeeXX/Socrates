# Socrates 主 Agent Loop 说明

本文说明交互式 REPL 中进入主 Agent Loop 时，`SocratesREPL.chat()`、`QueryEngineConfig`、`QueryEngine` 和 `query()` 之间的关系与执行逻辑。

## 1. 总览

交互式聊天的主调用链如下：

```text
SocratesREPL.chat(user_input)
    |
    | 1. 处理用户输入、@ 提及、输出风格、历史消息
    v
QueryEngineConfig(...)
    |
    | 2. 打包本次查询需要的运行环境
    v
QueryEngine(engine_config)
    |
    | 3. 构建 system prompt、注入上下文、准备压缩配置
    v
engine.submit_message(user_input)
    |
    | 4. 创建 QueryParams，并调用真正的主循环
    v
query(params)
    |
    | 5. 模型调用 -> 工具执行 -> 工具结果回填 -> 下一轮模型调用
    v
最终 assistant 回复 / max_turns / 中断 / 错误
```

其中，真正执行“模型 -> 工具 -> 模型”多轮循环的是：

```text
src/query/query.py::query()
```

`SocratesREPL.chat()` 是 REPL UI 层入口；`QueryEngineConfig` 是配置容器；`QueryEngine` 是查询编排层；`query()` 才是主 Agent Loop。

## 2. SocratesREPL.chat()

位置：

```text
src/repl/core.py::SocratesREPL.chat
```

`chat()` 是交互式 REPL 中用户输入一条普通消息后的入口函数。它负责把用户输入转换成一次可执行的 agent 查询，并把过程中产生的模型文本、工具调用、工具结果渲染到终端。

它主要做以下事情：

1. 展开用户输入中的 `@file`、`@directory`、`@agent` 提及。
2. 把展开后的内容拼进 `user_input`，作为模型可见上下文。
3. 将用户消息加入当前 session conversation。
4. 判断是否可以走 direct stream 快速文本回复。
5. 如果需要完整 agent loop，则创建 `QueryEngineConfig`。
6. 创建 `QueryEngine`。
7. 调用 `engine.submit_message(user_input)`，消费其异步消息流。
8. 根据消息类型渲染 UI：
   - `AssistantMessage`：显示模型文本或记录工具调用。
   - `SystemMessage`：显示状态，例如达到最大轮数。
   - `UserMessage` 中的 `ToolResultBlock`：显示工具执行结果。
   - `StreamEvent`：显示或统计请求开始等流式事件。

在这层里，`chat()` 不直接负责真正的工具循环。它更像 REPL 的控制器：准备输入，创建查询引擎，消费消息流，更新 UI 和 session 状态。

## 3. QueryEngineConfig

位置：

```text
src/query/engine.py::QueryEngineConfig
```

`QueryEngineConfig` 是一个 dataclass，用来承载本次查询所需的运行配置。

REPL 中创建它的代码大致是：

```python
engine_config = QueryEngineConfig(
    cwd=self.tool_context.workspace_root,
    provider=self.provider,
    tool_registry=self.tool_registry,
    tools=tools,
    tool_context=self.tool_context,
    append_system_prompt=style_prompt,
    max_turns=max_turns,
    initial_messages=prior_messages,
)
```

各字段含义如下：

| 字段 | 作用 |
| --- | --- |
| `cwd` | 当前工作区根目录，用于构建系统提示词、读取项目上下文、处理规则文件等。 |
| `provider` | 当前 LLM provider 实例，最终模型调用会通过它发出。 |
| `tool_registry` | 工具注册表，负责根据工具名真正 dispatch 本地工具。 |
| `tools` | 暴露给模型的工具列表，用于生成 API tool schema。 |
| `tool_context` | 工具运行上下文，包含权限、cwd、workspace、abort controller、文件读取状态、任务状态等。 |
| `append_system_prompt` | 附加到 system prompt 的输出风格提示词。 |
| `max_turns` | 限制本次 agent loop 最大工具循环轮数。 |
| `initial_messages` | 进入本次查询前已有的历史消息。 |

一个重要区别是：

```text
tools           -> 告诉模型可以调用哪些工具
tool_registry   -> 本地真正执行工具
tool_context    -> 工具执行时使用的环境和权限状态
```

## 4. QueryEngine

位置：

```text
src/query/engine.py::QueryEngine
```

`QueryEngine` 是 REPL 和底层 `query()` 主循环之间的编排层。它本身不实现“模型 -> 工具 -> 模型”的循环，而是负责把 REPL 传入的信息整理成 `query()` 所需的 `QueryParams`。

### 4.1 初始化

创建 `QueryEngine` 时，它会保存配置，并初始化可变消息历史：

```python
self._mutable_messages = list(config.initial_messages or [])
self._abort_controller = config.abort_controller or create_abort_controller()
self._session_id = uuid4().hex
```

这里的 `_mutable_messages` 是 `QueryEngine` 维护的对话历史。每次提交新用户输入时，它都会把新消息追加进去。

### 4.2 submit_message()

`QueryEngine` 的核心入口是：

```text
QueryEngine.submit_message(prompt)
```

它的主要步骤是：

1. 创建 `UserMessage(content=prompt)`。
2. 追加到 `_mutable_messages`。
3. 调用 `_build_system_prompt_parts()` 构建完整 system prompt。
4. 使用 `prepend_user_context()` 把用户上下文注入消息列表。
5. 根据 `tool_context.read_file_fingerprints` 构造压缩 pipeline 的 `read_file_state`。
6. 创建 `PipelineConfig`。
7. 创建 `QueryParams`。
8. `async for message in query(params)`，进入真正主循环。
9. 对 `query()` 产出的普通消息写回 `_mutable_messages`。
10. 将消息继续 yield 给 REPL 层渲染。

简化伪代码：

```python
async def submit_message(prompt):
    user_msg = UserMessage(content=prompt)
    self._mutable_messages.append(user_msg)

    system_prompt, user_context, system_context = await self._build_system_prompt_parts()

    messages_for_query = prepend_user_context(
        list(self._mutable_messages),
        user_context,
    )

    params = QueryParams(
        messages=messages_for_query,
        system_prompt=system_prompt,
        tools=self._config.tools,
        tool_registry=self._config.tool_registry,
        tool_use_context=self._config.tool_context,
        provider=self._config.provider,
        abort_controller=self._abort_controller,
        max_turns=self._config.max_turns,
        pipeline_config=pipeline_config,
    )

    async for message in query(params):
        if message should be persisted:
            self._mutable_messages.append(message)
        yield message
```

因此，`QueryEngine` 的职责是“准备”和“维护”，而不是“循环执行”。

## 5. query()

位置：

```text
src/query/query.py::query
```

`query()` 是交互式 REPL 当前真正的主 Agent Loop。它是一个异步生成器，会不断 yield 中间消息给上层 UI。

它的核心结构是：

```python
while True:
    yield StreamEvent(type="stream_request_start")

    if pipeline_config:
        run_compression_pipeline(...)

    assistant_messages, tool_use_blocks = await _call_model_sync(...)

    yield assistant_messages

    if no tool_use_blocks:
        return

    yield tool progress messages

    tool_results = await _run_tools_partitioned(...)

    yield tool_results

    if max_turns exceeded:
        yield max_turns message
        return

    state = QueryState(
        messages=[*messages, *assistant_messages, *tool_results],
        transition=Transition(reason="next_turn"),
    )
```

### 5.1 每轮开始

每轮 loop 会读取当前 `QueryState`：

```text
messages
tool_use_context
turn_count
max_output_tokens_override
transition
```

然后 yield：

```python
StreamEvent(type="stream_request_start")
```

REPL 可以用这个事件更新“正在请求模型”的状态。

### 5.2 压缩上下文

如果 `pipeline_config` 存在，`query()` 会先运行压缩 pipeline：

```python
run_compression_pipeline(...)
```

这一步用于处理上下文过长、工具结果太大、文件内容需要压缩等情况。压缩后得到的新 `messages` 会用于本轮模型调用。

### 5.3 调模型

模型调用通过 `_call_model_sync()` 完成。

它会：

1. 将内部 `Message` 转为 provider API 格式。
2. 根据 `tools` 构造 tool schema。
3. 根据 provider 类型决定 system prompt 的放置方式：
   - Anthropic / Minimax：作为 `system` 参数。
   - OpenAI-compatible：插入为第一条 system message。
4. 优先调用 `provider.chat_stream_response()`。
5. 如果 provider 不支持 structured streaming，则 fallback 到 `provider.chat()`。
6. 把返回文本包装成 `TextBlock`。
7. 把返回工具调用包装成 `ToolUseBlock`。
8. 返回：

```python
list[AssistantMessage], list[ToolUseBlock]
```

### 5.4 无工具调用时结束

如果模型没有返回工具调用：

```python
if not needs_follow_up:
    return
```

这表示 agent 本轮已经给出最终回复，主循环结束。

### 5.5 有工具调用时执行工具

如果模型返回了工具调用，`query()` 会先 yield 工具进度：

```python
SystemMessage(
    content=f"Running tool: {block.name}",
    subtype="tool_use_progress",
)
```

然后调用：

```python
_run_tools_partitioned(...)
```

工具执行逻辑如下：

1. `_partition_tool_calls()` 按工具是否并发安全分批。
2. 并发安全工具可以并行执行，例如 Read、Grep、Glob 等。
3. 非并发安全工具按顺序独占执行，例如 Edit、Write、Bash 等。
4. 单个工具通过 `_dispatch_single_tool()` 执行。
5. `_dispatch_single_tool()` 内部调用：

```python
tool_registry.dispatch(call, tool_use_context)
```

工具结果会被包装成 `UserMessage(content=[ToolResultBlock(...)])`。

### 5.6 工具结果回填并进入下一轮

工具执行完成后，`query()` 会 yield 所有工具结果给 REPL：

```python
for result_msg in tool_results:
    yield result_msg
```

然后它把当前轮的消息拼接为下一轮输入：

```python
state = QueryState(
    messages=[*messages, *assistant_messages, *tool_results],
    turn_count=next_turn_count,
    transition=Transition(reason="next_turn"),
)
```

这就是 agent loop 的关键：工具结果不会只显示给用户，还会作为下一轮模型输入，让模型基于工具结果继续推理。

## 6. 四者关系

可以这样理解：

| 层级 | 对象 | 职责 |
| --- | --- | --- |
| UI 入口层 | `SocratesREPL.chat()` | 接收用户输入，处理 @ 提及，创建 QueryEngine，渲染消息流。 |
| 配置层 | `QueryEngineConfig` | 打包 provider、tools、tool registry、tool context、历史消息、max_turns 等。 |
| 编排层 | `QueryEngine` | 构建 system prompt，注入上下文，准备压缩配置，创建 QueryParams，维护消息历史。 |
| 主循环层 | `query()` | 执行真正的模型调用、工具调用、多轮状态转移和终止判断。 |

更短地说：

```text
chat() 负责“从 REPL 进来”
QueryEngineConfig 负责“带上运行配置”
QueryEngine 负责“整理成 query 能跑的参数”
query() 负责“真正跑 agent loop”
```

## 7. 一次用户请求的完整时序

假设用户在 REPL 中输入：

```text
解释 src/query/query.py 的主循环
```

执行过程可以按层级理解：

```text
REPL 输入层
├─ 1. REPL 读到用户输入
└─ 2. 调用 SocratesREPL.chat(user_input)

SocratesREPL.chat()：UI 入口与查询准备
├─ 3. 展开 @ 提及，如果有 @file、@directory、@agent
├─ 4. 把展开后的用户消息加入 session conversation
├─ 5. 读取 output style，得到 style_prompt
├─ 6. 读取 prior_messages，作为本次查询的历史上下文
├─ 7. 创建 QueryEngineConfig
│  ├─ cwd
│  ├─ provider
│  ├─ tool_registry
│  ├─ tools
│  ├─ tool_context
│  ├─ append_system_prompt
│  ├─ max_turns
│  └─ initial_messages
├─ 8. 创建 QueryEngine(engine_config)
└─ 9. 调用 engine.submit_message(user_input)

QueryEngine.submit_message()：上下文编排与 QueryParams 构造
├─ 10. 追加 UserMessage 到 _mutable_messages
├─ 11. 构建 system prompt
│  ├─ 默认系统提示词
│  ├─ 工具使用规则
│  ├─ 工作区/环境上下文
│  ├─ CLAUDE.md / user context
│  └─ append_system_prompt，也就是 style_prompt
├─ 12. 注入 user context 到 messages_for_query
├─ 13. 根据 read_file_fingerprints 创建 PipelineConfig
├─ 14. 创建 QueryParams
│  ├─ messages
│  ├─ system_prompt
│  ├─ tools
│  ├─ tool_registry
│  ├─ tool_use_context
│  ├─ provider
│  ├─ abort_controller
│  ├─ max_turns
│  └─ pipeline_config
└─ 15. 调用 query(params)，并把 query() yield 的消息继续交给 REPL

query(params)：真正的主 Agent Loop
└─ 16. 进入 while True 多轮循环
   ├─ 17. 每轮开始 yield StreamEvent(stream_request_start)
   ├─ 18. 如果启用了 pipeline_config，先压缩上下文
   ├─ 19. 调用模型 _call_model_sync()
   │  ├─ 组装 provider API messages
   │  ├─ 组装 tool schemas
   │  ├─ 调用 provider.chat_stream_response() 或 provider.chat()
   │  └─ 得到 AssistantMessage 和 ToolUseBlock
   ├─ 20. yield AssistantMessage 给 REPL 渲染
   ├─ 21. 判断模型是否请求工具调用
   │  ├─ 没有工具调用
   │  │  └─ query() return，本次 agent loop 结束
   │  └─ 有工具调用
   │     ├─ yield tool_use_progress 给 REPL
   │     ├─ 调用 _run_tools_partitioned() 执行工具
   │     │  ├─ 并发安全工具可并行执行
   │     │  └─ 非并发安全工具顺序执行
   │     ├─ 每个工具内部通过 tool_registry.dispatch() 执行
   │     ├─ 工具结果包装成 ToolResultBlock
   │     └─ yield ToolResultBlock 给 REPL 渲染
   ├─ 22. 把 assistant_messages 和 tool_results 回填到 messages
   ├─ 23. 更新 QueryState，transition = next_turn
   └─ 24. 进入下一轮模型调用

终止条件
├─ 模型不再返回工具调用
├─ 达到 max_turns
├─ 用户中断 / abort_controller 被触发
└─ 模型调用或工具调用发生不可恢复错误
```

## 8. 和旧 run_agent_loop 的区别

仓库里还有旧的同步 loop：

```text
src/tool_system/agent_loop.py::run_agent_loop
```

它的逻辑也是：

```text
模型 -> 工具 -> 模型
```

但当前交互式 REPL 的 `chat()` 已经通过 `QueryEngine` 使用新的异步 `query()` 状态机。

旧 `run_agent_loop()` 目前主要仍被 headless 入口使用：

```text
src/entrypoints/headless.py::run_headless
```

因此，在理解当前 REPL 主 Agent Loop 时，应以：

```text
src/query/query.py::query()
```

为核心。
