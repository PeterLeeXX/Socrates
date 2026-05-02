# Socrates Agent Loop 完整流程说明

本文档说明 Socrates 在交互式 REPL 中执行一次用户请求时，完整 agent loop 是如何运行的。整体调用链可以概括为：

```text
SocratesREPL.chat(user_input)
    -> QueryEngineConfig
    -> QueryEngine.submit_message(user_input)
    -> query(QueryParams)
    -> 模型调用
    -> 工具执行
    -> 工具结果回填
    -> 下一轮模型调用或结束
```

其中 `SocratesREPL.chat()` 是 REPL 入口，`QueryEngine` 是查询编排层，`query()` 是真正执行“模型 -> 工具 -> 模型”多轮循环的主 agent loop。

## 1. 总体时序

```text
用户在 REPL 输入消息
    |
    v
SocratesREPL.chat()
    | 处理 @file/@directory/@agent 提及
    | 记录用户消息到 session conversation
    | 尝试 direct stream，若不适用则进入完整 agent loop
    v
QueryEngineConfig
    | 打包 provider、tools、tool_registry、tool_context、历史消息、max_turns 等
    v
QueryEngine
    | 追加 UserMessage 到内部消息历史
    | 构建 system prompt
    | 注入 user context/system context
    | 构造压缩管线配置 PipelineConfig
    | 创建 QueryParams
    v
query(params)
    | 每轮开始时可先压缩上下文
    | 调用模型
    | 若模型没有请求工具，返回最终 assistant 消息并结束
    | 若模型请求工具，执行工具并 yield 工具结果
    | 将 assistant 消息和工具结果写回 messages
    | 进入下一轮
    v
最终回复 / max_turns / abort / API 错误
```

## 2. `SocratesREPL.chat()`：REPL 入口与 UI 编排

位置：`src/repl/core.py::SocratesREPL.chat`

### 功能描述

`chat()` 是用户在 REPL 中输入普通消息后的入口函数。它负责把用户输入转换成一次可执行的查询，并消费底层 agent loop yield 出来的消息流，最终把 assistant 文本、工具调用、工具结果和状态事件渲染到终端。

### 代码逻辑

`chat()` 的核心逻辑如下：

1. 解析用户输入中的 `@` 提及。
   - `expand_at_mentions()` 展开 `@file`、`@directory` 等路径上下文。
   - `expand_agent_mentions()` 展开 `@agent`，生成提醒模型调用 Agent 工具的上下文。
   - `format_at_mention_attachments()` 把附件内容拼入用户输入。
2. 将最终用户输入写入 `self.session.conversation`。
3. 如果 `_should_try_direct_stream(user_input)` 为真，优先走直接文本流。
   - direct stream 适合无工具的快速回复。
   - direct stream 成功时不会进入完整 `QueryEngine` loop。
4. 解析输出风格 `resolve_output_style()`，得到 `style_prompt`。
5. 从 `tool_registry` 获取本轮暴露给模型的工具列表。
6. 用 `self._engine_messages` 作为 agent loop 的历史消息。
7. 创建 `QueryEngineConfig`。
8. 创建 `QueryEngine`。
9. 调用 `engine.submit_message(user_input)` 并异步消费其输出。
10. 按消息类型渲染：
    - `StreamEvent`：请求开始等事件。
    - `AssistantMessage`：assistant 文本和工具调用块。
    - `SystemMessage`：例如 max turns 提示。
    - `UserMessage` 中的 `ToolResultBlock`：工具执行结果。
11. 查询结束后，用 `engine.get_messages()` 回写 `self._engine_messages`，作为下一次用户请求的历史上下文。

### 整体流程中的作用

`chat()` 不直接执行模型-工具循环。它的作用是：

- 把 REPL 输入整理成 agent 能理解的消息。
- 构造查询引擎需要的配置。
- 消费 agent loop 的消息流并渲染 UI。
- 维护终端展示层和 session conversation。

它是 UI 入口，不是主循环本体。

## 3. `QueryEngineConfig`：一次查询的运行配置

位置：`src/query/engine.py::QueryEngineConfig`

### 功能描述

`QueryEngineConfig` 是一个 dataclass，用于承载一次 query 所需要的所有运行时依赖。

### 代码逻辑

主要字段如下：

| 字段 | 含义 |
| --- | --- |
| `cwd` | 当前工作区根目录。 |
| `provider` | LLM provider，最终模型调用通过它发出。 |
| `tool_registry` | 本地工具注册表，负责真正 dispatch 工具。 |
| `tools` | 暴露给模型的工具定义，用于生成 tool schema。 |
| `tool_context` | 工具执行上下文，包含 cwd、权限、abort controller、文件读取状态等。 |
| `abort_controller` | 中断控制器。未提供时由 `QueryEngine` 创建。 |
| `system_prompt` | 若显式提供，则直接使用该完整 system prompt。 |
| `custom_system_prompt` | 自定义 system prompt。 |
| `append_system_prompt` | 附加 system prompt，例如输出风格。 |
| `max_turns` | 最大工具循环轮数。 |
| `initial_messages` | 进入本次 query 前已有的消息历史。 |
| `query_source` | 查询来源，默认是 `repl_main_thread`。 |
| `user_context` | 用户上下文。 |
| `system_context` | 系统上下文。 |

### 整体流程中的作用

`QueryEngineConfig` 是 REPL 层和 query 层之间的配置包。它把 UI 层已经持有的 provider、工具、上下文和历史消息统一交给 `QueryEngine`。

## 4. `QueryEngine.__init__()`：初始化查询引擎状态

位置：`src/query/engine.py::QueryEngine.__init__`

### 功能描述

初始化查询引擎，保存配置，并建立本次查询引擎维护的可变消息历史。

### 代码逻辑

```python
self._config = config
self._mutable_messages = list(config.initial_messages or [])
self._abort_controller = config.abort_controller or create_abort_controller()
self._total_usage = {"input_tokens": 0, "output_tokens": 0}
self._session_id = uuid4().hex
```

### 整体流程中的作用

`QueryEngine` 在一次 REPL 请求中维护 agent loop 的消息历史。`query()` 每 yield 出一条普通消息，`QueryEngine.submit_message()` 会把它追加到 `_mutable_messages`，结束后再交还给 REPL 保存。

## 5. `QueryEngine._build_system_prompt_parts()`：构建 system prompt

位置：`src/query/engine.py::QueryEngine._build_system_prompt_parts`

### 功能描述

构建传给模型的完整 system prompt，并返回 user context 和 system context。

### 代码逻辑

1. 如果配置中已经提供 `system_prompt`，直接返回该 prompt，以及配置中的 context。
2. 否则调用 `fetch_system_prompt_parts()` 获取系统提示词片段。
3. 如果存在 `custom_system_prompt`：
   - 使用自定义 prompt。
   - 追加 `append_system_prompt`。
4. 如果不存在自定义 prompt：
   - 调用 `build_full_system_prompt()` 构建默认完整 system prompt。
   - 默认 prompt 中包含身份、环境、工具使用规则等。
   - 注意：单个工具自己的 prompt 不拼入 system prompt，而是通过 API 的 `tools` 参数发给模型。
5. 调用 `append_system_context()` 把 system context 追加进 prompt。
6. 如果上述流程异常，则 fallback 到 `build_context_prompt()`。

### 整体流程中的作用

这一步决定模型每一轮看到的系统级规则、环境信息和输出风格。它发生在进入 `query()` 之前，因此 `query()` 只接收最终的 `system_prompt` 字符串。

## 6. `QueryEngine.submit_message()`：构造 `QueryParams` 并进入主循环

位置：`src/query/engine.py::QueryEngine.submit_message`

### 功能描述

`submit_message()` 是 `QueryEngine` 的核心入口。它把用户 prompt 转换成 `UserMessage`，构造 system prompt、上下文、压缩配置和 `QueryParams`，然后调用真正的 agent loop：`query(params)`。

### 代码逻辑

核心步骤：

1. 创建 `UserMessage(content=prompt)`。
2. 追加到 `_mutable_messages`。
3. 调用 `_build_system_prompt_parts()`。
4. 调用 `prepend_user_context()`，将 user context 作为 `<system-reminder>` 注入消息列表。
5. 从 `tool_context.read_file_fingerprints` 构造 `read_file_state`。
   - 这让自动压缩后可以恢复近期读过的文件附件上下文。
6. 创建 `PipelineConfig`。
   - 传入 `provider`、`model`、`read_file_state` 等。
7. 创建 `QueryParams`。
8. `async for message in query(params)` 消费主循环输出。
9. 对 `StreamEvent` 和 `SystemMessage`：直接向上 yield，不写入 `_mutable_messages`。
10. 对普通消息：写入 `_mutable_messages` 后再 yield 给 REPL。

### 整体流程中的作用

`submit_message()` 是“查询编排层”。它负责把高层上下文整理成 `query()` 所需的标准输入，但不直接决定模型是否继续调用工具。这个决策发生在 `query()` 内部。

## 7. `QueryParams`：主循环输入参数

位置：`src/query/query.py::QueryParams`

### 功能描述

`QueryParams` 是传入 `query()` 的完整参数对象。

### 代码逻辑

主要字段：

| 字段 | 含义 |
| --- | --- |
| `messages` | 当前要发给模型的历史消息。 |
| `system_prompt` | 完整 system prompt。 |
| `tools` | 暴露给模型的工具定义。 |
| `tool_registry` | 本地工具注册表。 |
| `tool_use_context` | 工具执行上下文。 |
| `provider` | 模型 provider。 |
| `abort_controller` | 中断控制器。 |
| `query_source` | 查询来源。 |
| `max_output_tokens_override` | 临时覆盖最大输出 token。 |
| `max_turns` | 最大工具循环轮数。 |
| `user_context` | 用户上下文。 |
| `system_context` | 系统上下文。 |
| `pipeline_config` | 压缩管线配置。 |

### 整体流程中的作用

`QueryParams` 是 `query()` 主循环的输入边界。`query()` 不需要知道 REPL 如何生成这些配置，只按这个参数对象执行循环。

## 8. `QueryState` / `Transition` / `Terminal`：主循环状态模型

位置：`src/query/transitions.py`

### 功能描述

这些 dataclass 描述 `query()` loop 内部的状态、状态转移原因和终止信息。

### 代码逻辑

`QueryState` 关键字段：

| 字段 | 含义 |
| --- | --- |
| `messages` | 当前轮模型调用使用的消息。 |
| `tool_use_context` | 当前工具执行上下文。 |
| `auto_compact_tracking` | 自动压缩跟踪状态。 |
| `max_output_tokens_recovery_count` | 输出 token 超限后的恢复次数。 |
| `has_attempted_reactive_compact` | 是否尝试过响应式压缩。 |
| `max_output_tokens_override` | 当前轮是否临时放大输出 token。 |
| `stop_hook_active` | stop hook 状态。 |
| `turn_count` | 当前工具循环轮数。 |
| `transition` | 上一次进入本轮的原因。 |

`Transition.reason` 可表示：

- `next_turn`
- `max_output_tokens_recovery`
- `max_output_tokens_escalate`
- `reactive_compact_retry`
- `collapse_drain_retry`
- `stop_hook_blocking`
- `token_budget_continuation`

当前 `query.py` 中实际使用了 `next_turn`、`max_output_tokens_recovery` 和 `max_output_tokens_escalate`。

### 整体流程中的作用

`QueryState` 是 `query()` 的循环状态。每当工具结果需要回填给模型，或输出 token 超限需要恢复时，`query()` 都会创建新的 `QueryState` 并 `continue` 到下一轮。

## 9. `query()`：真正的主 Agent Loop

位置：`src/query/query.py::query`

### 功能描述

`query()` 是真正执行 agent loop 的异步生成器。它反复执行：

```text
压缩上下文 -> 调用模型 -> yield assistant 消息 -> 执行工具 -> yield 工具结果 -> 回填消息 -> 下一轮
```

直到模型不再请求工具、达到最大轮数、用户中断或发生不可恢复错误。

### 代码逻辑

#### 9.1 初始化状态

```python
state = QueryState(
    messages=list(params.messages),
    tool_use_context=params.tool_use_context,
    max_output_tokens_override=params.max_output_tokens_override,
)
```

每次进入 `query()`，都会把 `params.messages` 拷贝进 `QueryState`。之后主循环通过不断替换 `state` 来推进。

#### 9.2 每轮开始

每轮 `while True` 开始时，从 `state` 取出当前消息、工具上下文、恢复计数、turn count 等。

随后 yield：

```python
StreamEvent(type="stream_request_start")
```

上层 REPL 用它统计或展示一次新的模型请求开始。

#### 9.3 Phase 0：压缩管线

如果 `params.pipeline_config` 不为空，先估算当前消息 token：

```python
est_input_tokens = rough_token_count_estimation_for_messages(messages)
```

然后调用：

```python
run_compression_pipeline(
    messages,
    input_token_count=est_input_tokens,
    config=params.pipeline_config,
)
```

如果压缩节省了 token，本轮模型调用使用压缩后的 `messages`。

压缩异常不会终止 agent loop，只会记录 warning 并继续使用原始消息。

#### 9.4 调用模型

调用：

```python
returned_assistants, returned_tool_blocks = await _call_model_sync(...)
```

返回值：

- `assistant_messages`：模型输出的 assistant 消息。
- `tool_use_blocks`：模型请求的工具调用块。

如果 `tool_use_blocks` 非空，说明需要执行工具并进入 follow-up 轮次。

#### 9.5 yield assistant 消息

模型返回的 assistant 消息会 yield 给上层，供 REPL 展示。

但如果消息是 `_api_error == "max_output_tokens"`，当前代码会先 withheld，不立即展示，因为后面会尝试自动恢复。

#### 9.6 模型调用异常处理

如果 `_call_model_sync()` 抛出异常：

1. 调用 `_yield_missing_tool_result_blocks()`，为已经产生但未返回结果的工具调用补错误结果。
2. yield `_create_assistant_api_error_message(content=error_message)`。
3. `return` 结束主循环。

#### 9.7 abort 检查

模型调用后检查：

```python
if params.abort_controller.signal.aborted:
```

若已中断：

- 为未完成工具调用补错误结果。
- 如果不是普通 interrupt，yield 用户中断消息。
- 结束。

#### 9.8 无工具调用时的结束与输出 token 恢复

如果 `needs_follow_up` 为假，说明模型没有请求工具，通常可以结束。

但结束前先检查最后一条消息是否为 `max_output_tokens`：

1. 第一次遇到输出 token 超限，且还没有 override：
   - 设置 `max_output_tokens_override = ESCALATED_MAX_TOKENS`。
   - transition 设为 `max_output_tokens_escalate`。
   - `continue` 重新调用模型。
2. 如果仍然超限，且恢复次数小于 `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT`：
   - 追加一条 meta user message，要求模型直接续写、缩小剩余工作。
   - transition 设为 `max_output_tokens_recovery`。
   - `continue`。
3. 如果恢复次数耗尽：
   - yield 最后一条消息。

如果最后消息是 API error，则结束。

否则正常 `return`，agent loop 结束。

#### 9.9 有工具调用时：先 yield 工具进度

模型请求工具时，`query()` 会先为每个工具调用 yield：

```python
SystemMessage(
    content=f"Running tool: {block.name}",
    subtype="tool_use_progress",
)
```

这让上层 UI 可以展示“正在运行工具”。

#### 9.10 执行工具

调用：

```python
tool_results = await _run_tools_partitioned(
    tool_use_blocks,
    params.tool_registry,
    tool_use_context,
    params.tools,
)
```

工具执行完成后，逐条 yield `tool_results`。

#### 9.11 工具后 abort 检查

工具执行后再次检查 abort。

如果此时用户中断，并且 reason 不是 `interrupt`，yield 工具阶段的用户中断消息：

```python
_create_user_interruption_message(tool_use=True)
```

然后结束。

#### 9.12 max turns 检查

```python
next_turn_count = turn_count + 1

if params.max_turns and next_turn_count > params.max_turns:
    yield _create_max_turns_attachment(params.max_turns, next_turn_count)
    return
```

注意这里的 turn count 是工具回填后的下一轮计数。达到上限时，主循环不再把工具结果送回模型继续推理。

#### 9.13 回填消息并进入下一轮

如果还没有结束，构造下一轮状态：

```python
state = QueryState(
    messages=[*messages, *assistant_messages, *tool_results],
    tool_use_context=tool_use_context,
    turn_count=next_turn_count,
    max_output_tokens_recovery_count=0,
    has_attempted_reactive_compact=False,
    max_output_tokens_override=None,
    transition=Transition(reason="next_turn"),
)
```

关键点是：工具结果被追加进 `messages`，下一轮模型调用可以看到工具执行结果，并基于结果继续回答或继续请求工具。

### 整体流程中的作用

`query()` 是整个 agent loop 的核心。它负责：

- 控制多轮模型调用。
- 执行模型请求的工具。
- 将工具结果回填给模型。
- 处理中断、错误、max turns 和 max output tokens 恢复。
- 以异步流形式把中间状态交给上层 UI。

## 10. `_call_model_sync()`：模型调用与工具调用块解析

位置：`src/query/query.py::_call_model_sync`

### 功能描述

把内部消息格式转换成 provider API 请求，调用模型，并把响应转换回内部 `AssistantMessage` 和 `ToolUseBlock`。

### 代码逻辑

1. 调用 `normalize_messages_for_api(messages)` 转换消息格式。
2. 遍历 `tools`，构造 tool schema：

```python
{
    "name": tool.name,
    "description": tool.prompt(),
    "input_schema": dict(tool.input_schema),
}
```

3. 根据 provider 类型决定 system prompt 放置方式：
   - `AnthropicProvider` / `MinimaxProvider`：通过 `system` 参数传入。
   - 其他 provider：作为第一条 system message 插入。
4. 如果 `max_output_tokens_override` 不为空，写入 `call_kwargs["max_tokens"]`。
5. 优先调用 `provider.chat_stream_response()`。
6. 若 provider 不支持 structured streaming，fallback 到 `provider.chat()`。
7. 捕获特殊错误：
   - prompt too long -> 返回 `_api_error = "prompt_too_long"`。
   - max output tokens -> 返回 `_api_error = "max_output_tokens"`。
8. 将 `response.content` 包装成 `TextBlock`。
9. 将 `response.tool_uses` 包装成 `ToolUseBlock`。
10. 创建 `AssistantMessage`。
11. 如果 `stop_reason == "max_tokens"`，给 assistant message 标记 `_api_error = "max_output_tokens"`。
12. 返回：

```python
([assistant_msg], tool_use_blocks)
```

### 整体流程中的作用

`_call_model_sync()` 是 agent loop 中“模型”这一半的适配层。它隔离了不同 provider 的 API 差异，并统一产出 `AssistantMessage` 与 `ToolUseBlock`，供 `query()` 后续判断是否需要执行工具。

## 11. `_partition_tool_calls()`：工具调用分批

位置：`src/query/query.py::_partition_tool_calls`

### 功能描述

把同一轮模型返回的多个工具调用按并发安全性分成批次。

### 代码逻辑

1. 遍历每个 `ToolUseBlock`。
2. 根据工具名调用 `find_tool_by_name(tools, block.name)` 找到工具定义。
3. 调用：

```python
tool.is_concurrency_safe(block.input)
```

判断该工具在当前输入下是否并发安全。

4. 连续的并发安全工具会合并到同一个 batch。
5. 非并发安全工具每个单独成 batch，并顺序执行。

### 整体流程中的作用

这个函数决定工具执行阶段的并发策略。它让只读类工具可以并发运行，同时避免写文件、改状态、跑命令等工具互相踩踏。

## 12. `_dispatch_single_tool()`：执行单个工具

位置：`src/query/query.py::_dispatch_single_tool`

### 功能描述

把一个 `ToolUseBlock` 转换成 `ToolCall`，通过 `tool_registry` 执行，并将结果包装成模型可读的 `ToolResultBlock`。

### 代码逻辑

1. 创建 `ToolCall`：

```python
ToolCall(
    name=block.name,
    input=block.input,
    tool_use_id=block.id,
)
```

2. 调用：

```python
result = tool_registry.dispatch(call, tool_use_context)
```

3. 如果找到工具定义，调用工具自己的：

```python
tool.map_result_to_api(result.output, block.id)
```

将结构化结果转成 API 可用文本。

4. 如果没有工具定义，则按输出类型转字符串或 JSON。
5. 如果工具原始输出是 dict，将其放入 metadata，方便 REPL 渲染富预览。
6. 返回：

```python
UserMessage(
    content=[
        ToolResultBlock(
            tool_use_id=block.id,
            content=content_str,
            is_error=result.is_error,
            metadata=metadata,
        )
    ]
)
```

7. 如果执行异常，返回 `is_error=True` 的 `ToolResultBlock`。

### 整体流程中的作用

这是工具执行的最小单元。它把“模型要求调用某工具”变成本地真实工具执行，并把执行结果转回消息格式，供下一轮模型读取。

## 13. `_run_tools_partitioned()`：按批次执行工具

位置：`src/query/query.py::_run_tools_partitioned`

### 功能描述

根据 `_partition_tool_calls()` 的分批结果执行工具。并发安全的工具并行执行，非并发安全工具顺序执行。

### 代码逻辑

1. 调用 `_partition_tool_calls(tool_use_blocks, tools)`。
2. 对每个 batch：
   - 如果 batch 并发安全且包含多个工具：
     - 使用 `asyncio.to_thread()` 把同步工具 dispatch 放到线程中执行。
     - 使用 `asyncio.gather()` 并发等待。
     - 并发上限由 `SOCRATES_MAX_TOOL_USE_CONCURRENCY` 控制，默认 10。
   - 否则逐个工具顺序执行。
3. 汇总并返回所有 `UserMessage` 工具结果。

### 整体流程中的作用

它是 agent loop 中“工具”这一半的调度器。`query()` 不关心每个工具怎么并发或顺序执行，只等待这里返回完整工具结果。

## 14. `_yield_missing_tool_result_blocks()`：补齐缺失工具结果

位置：`src/query/query.py::_yield_missing_tool_result_blocks`

### 功能描述

当模型已经产生工具调用，但后续模型调用异常或用户中断时，为这些工具调用补上错误形式的工具结果。

### 代码逻辑

1. 遍历 `assistant_messages`。
2. 找到其中的 `ToolUseBlock`。
3. 为每个工具调用创建：

```python
ToolResultBlock(
    tool_use_id=block.id,
    content=error_message,
    is_error=True,
)
```

4. 包装成 `UserMessage` 返回。

### 整体流程中的作用

它保证消息协议完整：如果 assistant 产生了 tool_use，就应当有对应 tool_result。即使异常或中断，也用 error result 补齐，避免后续消息历史不一致。

## 15. `_is_withheld_max_output_tokens()`：识别输出 token 超限消息

位置：`src/query/query.py::_is_withheld_max_output_tokens`

### 功能描述

判断某条 assistant 消息是否表示模型输出 hit max tokens。

### 代码逻辑

该函数只对 `AssistantMessage` 生效，并检查：

```python
getattr(msg, "_api_error", None) == "max_output_tokens"
```

### 整体流程中的作用

它服务于 `query()` 的自动恢复逻辑。输出 token 超限时，主循环会先 withheld 这条不完整消息，然后尝试提高 token 上限或要求模型续写。

## 16. `CompressionPipeline.run()`：上下文压缩流程

位置：`src/services/compact/pipeline.py::CompressionPipeline.run`

### 功能描述

在每轮模型调用前压缩消息历史，减少输入 token，避免上下文过长。

### 代码逻辑

压缩管线按从便宜到昂贵的顺序执行 5 层：

| 层级 | 名称 | 作用 |
| --- | --- | --- |
| Layer 1 | `tool_result_budget` | 将大型工具结果持久化到磁盘或缩短。 |
| Layer 2 | `snip_compact` | 裁剪较旧的工具结果。 |
| Layer 3 | `microcompact` | 压缩中间工具调用，默认在主线程关闭。 |
| Layer 4 | `context_collapse` | 对上下文做投影视图。 |
| Layer 5 | `autocompact` | 最后手段，使用 LLM 做完整总结压缩。 |

每层如果节省了 token，会记录 `tokens_saved` 和 `layers_applied`。如果早期层节省量达到 `early_exit_tokens`，后续更昂贵层会跳过。

### 整体流程中的作用

压缩管线是每轮模型调用前的 Phase 0。它不改变 agent loop 的基本结构，但会改变本轮实际发给模型的 `messages`，让长上下文对话仍能继续运行。

## 17. 终止条件汇总

`query()` 会在以下情况下结束：

| 终止条件 | 触发位置 | 行为 |
| --- | --- | --- |
| 模型没有返回工具调用 | 模型调用后 | 返回最终 assistant 消息，结束。 |
| 模型返回 API error | 无工具调用分支 | 结束。 |
| 模型调用异常 | `except Exception` | yield API error message，结束。 |
| 用户在模型调用后中断 | abort 检查 | 补齐工具错误结果，结束。 |
| 用户在工具执行后中断 | 工具后 abort 检查 | yield 中断消息，结束。 |
| 达到 `max_turns` | 工具执行后 | yield `max_turns_reached` system message，结束。 |
| 输出 token 恢复耗尽 | 无工具调用分支 | yield 最后一条超限消息或结束。 |

## 18. 一次工具调用轮次的消息形态

一次典型的工具调用轮次中，消息会这样增长：

```text
原始 messages
    +
AssistantMessage([
    TextBlock(...可选解释文本...),
    ToolUseBlock(id="toolu_1", name="Read", input={...}),
])
    +
UserMessage([
    ToolResultBlock(tool_use_id="toolu_1", content="...", is_error=False)
])
```

下一轮模型调用时，上述 assistant tool_use 和 user tool_result 都在 `messages` 中。因此模型可以看到工具返回内容，并继续生成最终答案或请求更多工具。

## 19. 四层职责边界

| 层级 | 对象 | 职责 |
| --- | --- | --- |
| REPL/UI 层 | `SocratesREPL.chat()` | 处理用户输入、上下文附件、渲染消息流、维护 session conversation。 |
| 配置层 | `QueryEngineConfig` / `QueryParams` | 打包 provider、tools、tool registry、tool context、history、max turns、pipeline config。 |
| 编排层 | `QueryEngine` | 构建 system prompt，注入上下文，创建压缩配置，维护 mutable messages。 |
| 主循环层 | `query()` | 执行模型调用、工具调用、工具结果回填、多轮状态推进和终止判断。 |

## 20. 核心结论

Socrates 的 agent loop 不是单次模型请求，而是一个状态机式的异步生成器：

```text
state.messages
    -> compression
    -> _call_model_sync()
    -> assistant_messages + tool_use_blocks
    -> 如果无工具：结束
    -> 如果有工具：_run_tools_partitioned()
    -> tool_results
    -> state.messages = messages + assistant_messages + tool_results
    -> 下一轮
```

模型负责决定“是否需要工具”和“调用哪些工具”；本地 runtime 负责安全地执行工具、把结果写回消息历史，并继续把结果交给模型推理。这个闭环就是当前 Socrates REPL 中完整的 agent loop。
