# 当前上下文压缩机制说明

本文从 `src/query/query.py` 入手，说明当前项目里的上下文压缩机制。这里的“上下文压缩”不是单一函数，而是一组在模型调用前、手动 `/compact` 时、以及摘要生成失败时用于缩减消息体积的机制。

## 1. 总体入口

### `src/query/query.py`

#### `QueryParams`

位置：`src/query/query.py`

功能：承载一次查询所需的所有参数。

和压缩相关的字段是：

- `messages`: 当前要发送给模型的消息列表。
- `provider`: 当前模型 provider，用于普通对话，也可被压缩管线用于摘要。
- `pipeline_config`: 可选的 `PipelineConfig`。只有它不为 `None` 时，`query()` 才会运行压缩管线。

也就是说，`query.py` 本身不会无条件压缩上下文，而是通过 `pipeline_config` 这个开关接入压缩系统。

#### `query(params: QueryParams)`

位置：`src/query/query.py`

功能：主查询循环。它负责：

1. 接收当前消息。
2. 在模型调用前运行压缩管线。
3. 调用模型。
4. 如果模型要求工具调用，则执行工具并进入下一轮。

压缩发生在每一轮模型调用前的这段逻辑中：

```python
if params.pipeline_config is not None:
    est_input_tokens = rough_token_count_estimation_for_messages(messages)
    pipeline_result = await run_compression_pipeline(
        messages,
        input_token_count=est_input_tokens,
        config=params.pipeline_config,
    )
    if pipeline_result.tokens_saved > 0:
        messages = pipeline_result.messages
```

这里有几个关键点：

- `rough_token_count_estimation_for_messages()` 会先粗略估算当前消息 token 数。
- `run_compression_pipeline()` 会按固定顺序尝试多层压缩。
- 只有 `pipeline_result.tokens_saved > 0` 时，`query()` 才把本轮要发送给模型的 `messages` 替换为压缩后的消息。
- 压缩失败不会中断对话；异常会被记录，然后继续使用原始消息。

#### `_call_model_sync(...)`

位置：`src/query/query.py`

功能：真正调用 provider 的函数。

它本身不执行压缩，但会处理两类和上下文相关的错误：

- 如果 provider 抛出 `"prompt is too long"` 或 `"prompt_too_long"`，会返回一个带 `_api_error = "prompt_too_long"` 的 assistant 错误消息。
- 如果遇到输出 token 限制相关错误，会返回 `_api_error = "max_output_tokens"`。

当前主循环里，对 `prompt_too_long` 的处理是展示错误并结束；代码里虽然存在 reactive compact 模块，但 `query.py` 当前没有在 prompt-too-long 后调用 `reactive_compact()` 自动重试。

#### `max_output_tokens` 恢复机制

位置：`src/query/query.py`

相关函数：

- `_is_withheld_max_output_tokens(msg)`
- `_create_user_message(...)`

如果 assistant 响应因为 `max_output_tokens` 被截断，`query()` 会先把 `max_output_tokens_override` 提升到 `ESCALATED_MAX_TOKENS = 64_000` 重试一次；如果还不够，则最多追加 3 次 meta 用户消息，让模型“直接续写，不道歉，不复述”。这不是上下文压缩，但属于上下文长度/输出长度恢复机制。

## 2. 压缩管线如何接入

### `src/query/engine.py`

#### `QueryEngine.submit_message(...)`

功能：用户提交消息时，构造系统提示、用户上下文，并创建 `PipelineConfig`。

关键逻辑：

```python
pipeline_config = PipelineConfig(
    provider=self._config.provider,
    model=getattr(self._config.provider, 'model', '') or '',
    read_file_state=read_file_state or None,
)
```

说明：

- 主线程查询默认会传入 `PipelineConfig`，因此会启用 `query.py` 中的 “Phase 0: Compression Pipeline”。
- `read_file_state` 来自 `tool_context.read_file_fingerprints`，用于压缩后把最近读过的文件重新注入上下文。
- 这里没有显式设置 `mc_enabled`，所以主线程默认不启用第 3 层 typed microcompact。

## 3. 五层压缩管线

### `src/services/compact/pipeline.py`

#### `PipelineConfig`

功能：配置压缩管线。

主要字段：

- `budget_dir`: 大型工具结果落盘目录。
- `max_result_tokens`: 单个工具结果超过多少 token 后落盘，默认 `8_000`。
- `snip_keep_recent`: snip compact 保留最近多少条，默认 `10`。
- `mc_enabled`: 是否启用 typed microcompact，默认 `False`。
- `mc_keep_recent`: microcompact 保留最近多少个工具结果，默认 `5`。
- `collapse_store`: context collapse 的存储。
- `context_window`: 模型上下文窗口，默认 `200_000`。
- `autocompact_tracking`: 自动压缩状态追踪器。
- `provider` / `model`: 第 5 层 LLM 摘要压缩需要。
- `read_file_state` / `plan_file_path` / `memory_paths`: 压缩后恢复文件、计划、记忆上下文用。
- `early_exit_tokens`: 前面几层累计节省超过该值后提前退出，默认 `20_000`。

#### `CompressionPipeline.run(messages, input_token_count)`

功能：按“便宜到昂贵”的顺序运行 5 层压缩。

执行顺序：

1. `apply_tool_result_budget`
2. `snip_compact`
3. `microcompact_typed_messages`
4. `ContextCollapseStore.project_view`
5. `auto_compact_if_needed`

设计思想是：先尝试不需要 LLM 的便宜压缩，如果已经节省足够 token，就不进入后续昂贵步骤。

#### `run_compression_pipeline(...)`

功能：便捷包装函数。

`query.py` 调用的是这个函数，它内部创建 `CompressionPipeline(config)` 并执行 `pipeline.run(...)`。

## 4. Layer 1：工具结果预算落盘

### `src/services/compact/tool_result_budget.py`

#### `apply_tool_result_budget(messages, budget_dir=None, max_result_tokens=8000)`

功能：把过大的 `tool_result` 内容写入磁盘，并在消息中替换为短引用。

工作方式：

1. 遍历所有 user 消息。
2. 找到其中的 `ToolResultBlock` 或原始 dict 形式的 `tool_result`。
3. 估算该工具结果 token 数。
4. 如果超过 `max_result_tokens`，把原始内容写入文件。
5. 用类似 `[Tool result stored at: path]` 的短文本替换原工具结果。
6. 在 `budget_manifest.json` 记录落盘结果，避免重复处理。

优点：

- 不需要 LLM。
- 对非常大的工具输出最有效。
- 能保留“结果曾经存在且存储在哪里”的引用。

风险：

- 模型后续如果需要原始工具结果，需要根据路径重新读取。
- 默认目录在 `/tmp/socrates_budget/<pid>`，在 Windows 环境下这个路径是否符合预期需要留意。

## 5. Layer 2：Snip Compact

### `src/services/compact/snip_compact.py`

#### `snip_compact(messages, keep_recent=10)`

功能：理论上用于裁剪过旧的工具结果。

当前实现：

```python
return list(messages), 0
```

也就是说，这一层目前是占位实现，不会实际压缩。文件注释说明这是为了匹配 TS 版本的 stub 行为，避免过度删除模型之后可能还要引用的工具结果。

## 6. Layer 3：Microcompact

### `src/context_system/microcompact.py`

Microcompact 是轻量级压缩，核心思路是：保留消息结构，但清空较旧、可压缩工具结果的正文。

#### `microcompact_typed_messages(messages, keep_recent=5, time_config=None, force=False)`

功能：处理 typed `Message` 对象。

工作方式：

1. 收集 assistant 消息里的可压缩工具调用 ID。
2. 默认可压缩工具包括 `Read`, `Bash`, `Shell`, `Grep`, `Glob`, `WebSearch`, `WebFetch`, `Edit`, `Write`。
3. 保留最近 `keep_recent` 个工具结果。
4. 更早的工具结果会被替换为：

```text
[Old tool result content cleared]
```

当前主查询路径中的状态：

- `PipelineConfig.mc_enabled` 默认是 `False`。
- `QueryEngine.submit_message()` 没有把它设为 `True`。
- 所以主线程的 5 层管线默认不会执行这一层。

#### `microcompact_api_messages(messages, keep_recent=3)`

功能：处理 API dict 格式消息。

它主要在 LLM 摘要压缩前使用，用来缩小“发给摘要模型的历史内容”。也就是说，即使主线程 typed microcompact 默认关闭，手动 `/compact` 和自动 LLM 摘要内部仍会使用 API 格式 microcompact。

#### `strip_images_from_messages(messages)`

功能：把 API 消息里的图片、文档块替换为文本标记：

- `[image]`
- `[document]`

用途：在摘要压缩前减少多模态内容 token 开销。

## 7. Layer 4：Context Collapse

### `src/services/compact/context_collapse.py`

#### `ContextCollapseStore`

功能：保存一组 collapse commit。每个 commit 记录：

- 被归档的消息 UUID 列表。
- 替代这些消息的 summary 文本。

#### `ContextCollapseStore.project_view(messages)`

功能：生成一个“投影视图”。

它不会原地修改原始 `messages`，而是在发送模型前把被归档的消息段替换成一个虚拟 user 消息：

```text
[Collapsed context]
...
```

当前主路径状态：

- 如果 `PipelineConfig.collapse_store` 存在，或全局 `get_context_collapse_state()` 返回可用 store，并且 store 有 commits，则会生效。
- 如果没有设置 store 或 commits 为空，则不会做任何事。

## 8. Layer 5：自动 LLM 摘要压缩

### `src/services/compact/autocompact.py`

#### `AutoCompactTracking`

功能：追踪自动压缩状态。

字段包括：

- `consecutive_failures`: 连续失败次数。
- `last_failure_time`: 最近失败时间。
- `last_compact_time`: 最近成功压缩时间。
- `total_compactions`: 总压缩次数。
- `compacted`: 是否发生过压缩。
- `turn_counter`: 轮次计数。

#### `get_effective_context_window_size(context_window, max_output_tokens=None)`

功能：计算自动压缩可用的有效上下文窗口。

它会从模型上下文窗口中扣除摘要输出预留空间，默认最多预留 `20_000` token，并支持环境变量：

- `CLAUDE_CODE_AUTO_COMPACT_WINDOW`

#### `get_auto_compact_threshold(context_window, max_output_tokens=None)`

功能：计算自动压缩触发阈值。

公式大致是：

```text
threshold = effective_context_window - AUTOCOMPACT_BUFFER_TOKENS
```

其中：

- `AUTOCOMPACT_BUFFER_TOKENS = 13_000`
- 默认 `context_window = 200_000`
- 默认摘要输出预留 `20_000`

因此默认情况下，自动压缩阈值约为：

```text
200000 - 20000 - 13000 = 167000 tokens
```

环境变量 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 可以用百分比方式降低阈值，方便测试。

#### `is_auto_compact_enabled()`

功能：判断自动压缩是否启用。

如果设置了这些环境变量，则禁用：

- `DISABLE_COMPACT`
- `DISABLE_AUTO_COMPACT`

#### `should_auto_compact(input_token_count, context_window, ...)`

功能：判断本轮是否应该自动压缩。

触发条件：

1. 自动压缩未被环境变量禁用。
2. `input_token_count >= MIN_INPUT_TOKENS_FOR_AUTOCOMPACT`，其中最小值是 `10_000`。
3. 如果传入了 `AutoCompactTracking`，连续失败次数必须小于 `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`。
4. `input_token_count` 必须达到自动压缩阈值。

#### `auto_compact_if_needed(...)`

功能：如果达到阈值，则构造 `CompactContext(trigger="auto")` 并调用 LLM 摘要压缩：

```python
result = await compact_conversation(ctx)
```

成功后会更新 tracking；失败后会增加 `consecutive_failures` 并返回 `None`。失败不会让主查询失败。

当前主路径注意点：

- `PipelineConfig` 支持 `autocompact_tracking`。
- 但 `QueryEngine.submit_message()` 当前创建 `PipelineConfig` 时没有传入 tracking。
- `query.py` 的 `QueryState` 虽然有 `auto_compact_tracking` 字段，但没有把它注入 `PipelineConfig`。
- 因此自动压缩仍可按阈值触发，但连续失败断路器在主路径里可能没有跨轮状态。

## 9. LLM 摘要压缩核心

### `src/services/compact/compact.py`

#### `CompactContext`

功能：描述一次压缩所需上下文。

字段包括：

- `provider`
- `model`
- `messages`
- `custom_instructions`
- `trigger`: `manual`、`auto`、`reactive` 等。
- `read_file_state`
- `plan_file_path`
- `memory_paths`

#### `CompactionResult`

功能：描述压缩结果。

重要字段：

- `boundary_marker`: 压缩边界消息。
- `summary_messages`: 压缩摘要消息。
- `messages_to_keep`: 部分压缩时保留的消息。
- `attachments`: 压缩后恢复的文件/计划附件。
- `pre_compact_token_count`
- `post_compact_token_count`
- `tokens_saved`
- `trigger`

#### `compact_conversation(context)`

功能：完整压缩会话历史。

详细流程：

1. 调用 `get_messages_after_boundary(messages)`，只压缩最后一个 compact boundary 之后的消息，避免重复总结已经总结过的内容。
2. 如果可压缩消息少于 2 条，抛出 `ERROR_MESSAGE_NOT_ENOUGH_MESSAGES`。
3. 用 `normalize_messages_for_api()` 转为 API 消息。
4. 用 `count_messages_tokens()` 统计压缩前 token。
5. 调用 `strip_images_from_messages()` 去除图片/文档。
6. 调用 `microcompact_api_messages()` 清理较旧工具结果。
7. 用 `get_compact_prompt(custom_instructions)` 构造摘要提示。
8. 调用 `provider.chat_async(...)` 生成摘要，最大输出 token 为 `COMPACT_MAX_OUTPUT_TOKENS = 8192`。
9. 如果摘要调用遇到 prompt too long，则进入最多 3 次 retry。
10. 生成失败时会尝试 sync `provider.chat(...)` fallback；仍失败则用 `_fallback_summary()` 做简单文本摘要。
11. 调用 `format_compact_summary()` 清理 `<analysis>`，提取 `<summary>`。
12. 创建 compact boundary。
13. 创建 summary message。
14. 创建 post-compact attachments。
15. 计算 `tokens_saved` 并返回 `CompactionResult`。

#### `parse_prompt_too_long_token_gap(error_str)`

功能：从类似 `prompt is too long: 137500 tokens > 135000 maximum` 的错误中解析超出的 token 数。

用途：让 retry 时能按真实 token gap 删除足量旧消息，而不是盲目砍半。

#### `truncate_head_for_ptl_retry(messages, token_gap=None)`

功能：当摘要模型自己也吃不下待总结历史时，删除最旧的 API round。

它不是简单按消息数切分，而是调用 `group_messages_by_api_round()`，尽量保持 user/assistant/tool_result 的 API 结构合法。

如果裁剪后第一条是 assistant 消息，会插入一个 meta user marker：

```text
[earlier conversation truncated for compaction retry]
```

#### `_fallback_summary(messages)`

功能：当 LLM 摘要失败时，生成一个非常简略的本地摘要。

它会提取：

- 会话消息数量。
- 使用过的工具名。
- 最近的用户消息片段。
- 最近的 assistant 消息片段。

这是兜底方案，信息保真度远低于正常 LLM 摘要。

#### `partial_compact_conversation(context, pivot_index, direction="earlier")`

功能：部分压缩。

支持：

- `earlier` / `up_to`: 总结前缀，保留后缀。
- `later` / `from`: 保留前缀，总结后缀。

它会调用 `annotate_boundary_with_preserved_segment()`，在 boundary 上记录被保留消息段的 relink 信息，方便恢复消息链。

当前从 `query.py` 主路径看，常规自动压缩调用的是完整 `compact_conversation()`，不是 partial compact。

## 10. Compact Boundary 和 Summary Message

### `src/compact_service/messages.py`

#### `create_compact_boundary_message(...)`

功能：创建压缩边界消息。

边界消息是 `SystemMessage`，带有：

- `subtype="compact_boundary"`
- `isMeta=True`
- `_compact_boundary_meta`

元数据包括：

- `trigger`
- `pre_compact_token_count`
- `last_message_uuid`
- `messages_summarized`
- `pre_compact_discovered_tools`
- `preserved_segment`

这条消息用于标记“这里发生过压缩”。之后再次压缩时，系统会只压缩最后一个 boundary 之后的消息。

#### `is_compact_boundary_message(msg)`

功能：判断消息是否是 compact boundary。

当前判断条件很宽：

```python
return getattr(msg, "isMeta", False) and msg.role == "system"
```

这意味着任何 `isMeta=True` 的 system 消息都会被视为 compact boundary。若项目里还有其他 meta system 消息，这里可能存在误判风险。

#### `get_messages_after_boundary(messages)`

功能：返回最后一个 compact boundary 之后的消息。

这可以避免重复总结旧摘要，但也意味着 boundary 识别的准确性很重要。

#### `create_compact_summary_message(summary_text, ...)`

功能：创建压缩后的用户消息。

它会把摘要包装成类似：

```text
This session is being continued from a previous conversation.

...
```

摘要消息使用 `UserMessage`，目的是让后续模型把它当成继续会话的上下文。

## 11. 手动 `/compact` 路径

### `src/command_system/builtins.py`

#### `_compact_async(args, context)`

功能：异步执行 `/compact`。

流程：

1. 检查 conversation 是否存在。
2. 检查消息数量是否至少 2 条。
3. 从 command context 中取 `provider` 和 `model`。
4. 把命令参数作为 `custom_instructions`。
5. 调用 `compact_service.service.compact_conversation(...)`。
6. 返回 `LocalCommandResult(type="compact", ...)`。

#### `compact_command_call(args, context)`

功能：`/compact` 命令入口。

如果当前没有 running event loop，则使用 `asyncio.run(_compact_async(...))`。如果已经在 async 环境里，会走 `_sync_compact_fallback(context)`。

#### `_sync_compact_fallback(context)`

功能：同步兜底压缩。

这个路径不会调用 LLM 生成高质量摘要，而是创建一个非常简单的 summary，例如：

```text
Conversation had N messages (X tokens).
```

如果兜底也失败，最后会在消息超过 10 条时只保留最后 10 条。

### `src/compact_service/service.py`

#### `compact_conversation(conversation, provider, model, ...)`

功能：面向命令处理器的包装层，会原地修改 live `Conversation`。

它内部调用：

```python
_pipeline_compact(context)
```

也就是 `src/services/compact/compact.py` 里的 `compact_conversation()`。

之后它会重建 `conversation.messages`：

1. 保留最后一个 compact boundary 之前的内容。
2. 添加新的 boundary。
3. 添加 summary message。
4. 添加 `messages_to_keep`。
5. 添加 post-compact attachments。

这就是手动 `/compact` 真正改变会话历史的地方。

## 12. 压缩后附件恢复

### `src/services/compact/post_compact_attachments.py`

#### `create_post_compact_file_attachments(...)`

功能：压缩后恢复最近读过的文件内容。

默认限制：

- 最多恢复 `5` 个文件。
- 总预算 `50_000` token。
- 单文件最多 `5_000` token。

它会排除：

- plan 文件。
- memory / `CLAUDE.md` 文件。
- 已经在保留消息里通过 `Read` 工具出现过的文件。

生成的附件是 `UserMessage(isMeta=True)`，内容格式类似：

```text
[Post-compact file restore: path]

file content...
```

#### `create_plan_attachment_if_needed(plan_file_path)`

功能：如果 plan 文件存在且非空，则压缩后重新注入 plan 内容。

## 13. Token 估算与统计

### `src/token_estimation.py`

#### `rough_token_count_estimation_for_messages(messages)`

功能：粗略估算 typed message 列表 token。

`query.py` 在运行压缩管线前使用它估算 `input_token_count`，自动压缩阈值判断依赖这个值。

#### `count_messages_tokens(messages)`

功能：统计 API dict 格式消息 token。

它会计算：

- role token。
- text 内容。
- tool_use 名称和输入。
- tool_result 内容。
- image/document 固定按约 `2000` token 估算。

`compact_conversation()` 用它计算压缩前后 token，从而得到 `tokens_saved`。

## 14. Reactive Compact 当前状态

### `src/services/compact/reactive_compact.py`

#### `reactive_compact(messages, error, provider, model, ...)`

功能：理论上用于当普通模型调用发生 prompt-too-long 错误后，立刻尝试压缩并重试。

它的策略是：

1. 判断错误是否是 prompt-too-long。
2. 先尝试正常 `compact_conversation(trigger="reactive")`。
3. 如果 LLM 压缩失败，则执行 emergency drop，按比例丢弃最旧消息。

但从当前 `src/query/query.py` 看，主查询循环没有调用这个函数。`_call_model_sync()` 捕获 prompt-too-long 后只返回 API 错误消息，`query()` 随后结束。因此 reactive compact 模块目前更像是备用能力，而不是主路径已启用能力。

## 15. 当前机制的实际运行顺序

普通用户消息进入后，实际顺序大致如下：

1. `QueryEngine.submit_message()` 添加 user message。
2. 构建 system prompt 和 user context。
3. 创建 `PipelineConfig(provider, model, read_file_state)`。
4. 调用 `query(params)`。
5. `query()` 每轮开始先估算 token。
6. `run_compression_pipeline()` 运行 5 层压缩。
7. 如果节省了 token，则本轮模型调用使用压缩后的 `messages`。
8. `_call_model_sync()` 调用模型。
9. 如果模型产生工具调用，执行工具并进入下一轮。
10. 下一轮再次从第 5 步开始检查是否需要压缩。

手动 `/compact` 的顺序则是：

1. `compact_command_call()`。
2. `_compact_async()`。
3. `compact_service.service.compact_conversation()`。
4. `services.compact.compact.compact_conversation()` 生成摘要。
5. 重写 live `conversation.messages`。
6. 返回压缩结果给命令系统。

## 16. 当前实现的几个重要观察

1. `query.py` 中的压缩是“发送前投影/替换”，不是直接修改 `QueryEngine._mutable_messages`。真正原地改会话的是手动 `/compact` 的 service wrapper。

2. Layer 1 是当前最确定会生效的便宜压缩层：大工具结果会被落盘替换。

3. Layer 2 当前是 no-op。

4. Layer 3 在主查询管线默认关闭，但在 LLM 摘要前仍会对 API 消息执行 microcompact。

5. Layer 4 依赖 collapse store 是否被设置；默认没有 commits 时不会生效。

6. Layer 5 自动摘要压缩依赖 token 阈值、provider、model。`QueryEngine` 默认传入 provider 和 model，因此具备触发条件。

7. 自动压缩失败不会终止对话；它只会记录 warning 并继续使用未压缩消息。

8. `prompt_too_long` 的 reactive compact 当前没有接入 `query.py` 主循环。上下文真的超过 provider 限制时，用户仍可能看到“请使用 /compact”的错误。

9. `is_compact_boundary_message()` 判断条件较宽，可能把其他 meta system 消息误识别为 compact boundary。

10. post-compact restore 会尝试把最近读过的文件重新注入，这能减少压缩后模型“忘记刚读过文件”的问题。

## 17. 关键函数速查表

| 文件 | 函数 / 类 | 功能 |
|---|---|---|
| `src/query/query.py` | `query()` | 主查询循环；模型调用前运行压缩管线 |
| `src/query/query.py` | `_call_model_sync()` | 调用 provider；识别 prompt-too-long 和 max-output-token 错误 |
| `src/query/engine.py` | `QueryEngine.submit_message()` | 构造 `PipelineConfig` 并传入 `query()` |
| `src/services/compact/pipeline.py` | `PipelineConfig` | 五层压缩管线配置 |
| `src/services/compact/pipeline.py` | `CompressionPipeline.run()` | 按顺序执行五层压缩 |
| `src/services/compact/pipeline.py` | `run_compression_pipeline()` | `query.py` 使用的管线入口 |
| `src/services/compact/tool_result_budget.py` | `apply_tool_result_budget()` | 大工具结果落盘并替换为引用 |
| `src/services/compact/snip_compact.py` | `snip_compact()` | 当前 no-op，占位 |
| `src/context_system/microcompact.py` | `microcompact_typed_messages()` | 清空较旧 typed 工具结果 |
| `src/context_system/microcompact.py` | `microcompact_api_messages()` | 清空较旧 API 格式工具结果，主要用于摘要前 |
| `src/context_system/microcompact.py` | `strip_images_from_messages()` | 摘要前将图片/文档替换为文本标记 |
| `src/services/compact/context_collapse.py` | `ContextCollapseStore.project_view()` | 把已 collapse 的消息段替换成 summary |
| `src/services/compact/autocompact.py` | `should_auto_compact()` | 判断是否达到自动压缩阈值 |
| `src/services/compact/autocompact.py` | `auto_compact_if_needed()` | 达到阈值时触发 LLM 摘要压缩 |
| `src/services/compact/compact.py` | `compact_conversation()` | LLM 摘要压缩核心 |
| `src/services/compact/compact.py` | `partial_compact_conversation()` | 部分压缩，支持保留前缀或后缀 |
| `src/services/compact/compact.py` | `truncate_head_for_ptl_retry()` | 摘要模型 prompt-too-long 时删除旧 API round |
| `src/compact_service/messages.py` | `create_compact_boundary_message()` | 创建压缩边界 system meta 消息 |
| `src/compact_service/messages.py` | `create_compact_summary_message()` | 创建压缩摘要 user 消息 |
| `src/compact_service/messages.py` | `get_messages_after_boundary()` | 只取最后一个 boundary 后的消息 |
| `src/command_system/builtins.py` | `compact_command_call()` | `/compact` 命令入口 |
| `src/compact_service/service.py` | `compact_conversation()` | 手动 `/compact` 的 conversation-mutating 包装层 |
| `src/token_estimation.py` | `rough_token_count_estimation_for_messages()` | 查询前粗略估算 token |
| `src/token_estimation.py` | `count_messages_tokens()` | API 消息 token 统计 |

