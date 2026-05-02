# Session 管理解析

本文基于当前代码阅读结果，重点解释 Socrates 的 session 生命周期：什么时候落盘、落盘成什么文件、跨对话如何管理、异常中断如何处理、持久化与恢复链路如何运作。

## 1. 总体结构

当前 session 管理由三层组成：

1. **REPL 运行时 session**
   - 定义在 `src/repl/core.py` 的 `RuntimeSession`。
   - 字段包括 `session_id`、`provider`、`model`、`conversation`。
   - 这是交互过程中使用的内存态。

2. **Conversation 内存消息列表**
   - 定义在 `src/agent/conversation.py`。
   - 核心字段是 `messages: list[Message]` 和 `max_history=100`。
   - REPL 通过 `_append_conversation_message()` 手动维护这个列表，超过 `max_history` 会丢弃最早消息。

3. **SessionStorage 持久化层**
   - 定义在 `src/services/session_storage.py`。
   - 负责把消息写入 JSONL transcript，并维护 metadata。
   - 默认根目录是：

```text
~/.socrates/sessions/
```

每个 session 独占一个目录：

```text
~/.socrates/sessions/<session_id>/
  metadata.json
  transcript.jsonl
  content/
    <ref_id>.txt
```

其中：

- `metadata.json` 是 session 元信息。
- `transcript.jsonl` 是完整对话转录，每行一条消息 JSON。
- `content/*.txt` 用于存储超大的 tool_result 文本。

## 2. Session 创建

REPL 初始化时创建 `SessionStorage`：

```python
self.session_storage = SessionStorage(
    session_id=resume_session_id,
    sessions_dir=sessions_dir,
)
```

如果没有传入 `resume_session_id`，`SessionStorage` 会生成一个新的 UUID 作为 `session_id`。随后 REPL 创建内存态 `RuntimeSession`，并把 `session_storage.session_id` 填进去。

新 session 会立即初始化 `metadata.json`：

```python
self.session_storage.init_metadata(
    model=self.provider.model,
    cwd=str(Path.cwd()),
    title="",
)
```

metadata 字段包括：

- `session_id`
- `start_time`
- `model`
- `cwd`
- `title`
- `total_cost`
- `message_count`
- `last_updated`

这里的 `metadata.json` 使用原子写入：先写临时文件，再 `os.replace()` 替换目标文件。因此 metadata 单文件更新相对抗中断。

## 3. 什么时候落盘

### 3.1 消息不是立即写到文件，而是先进入 buffer

REPL 每记录一条消息，会调用：

```python
def _persist_message(self, message: Message) -> None:
    self.session_storage.write_message(message)
```

`write_message()` 会：

1. 将 `Message` 转为 dict。
2. 对大 tool_result 做内容替换。
3. 追加到 `_write_buffer`。
4. 当 buffer 长度达到 `MAX_FLUSH_BATCH = 50` 时自动 `flush()`。

所以，单条消息记录时只是进入内存 buffer，不一定马上写入 `transcript.jsonl`。

### 3.2 正常对话回合结束时 flush

在 `SocratesREPL.chat()` 中：

1. 用户输入先被 `_record_user_input()` 记录。
2. assistant 消息由 `_record_assistant_message()` 记录。
3. 工具结果等 query 内部 user message 由 `_record_query_user_message()` 记录。
4. 回合结束后执行：

```python
self._flush_session_storage()
```

`_flush_session_storage()` 调用 `SessionStorage.flush()`，把 buffer 里的所有消息追加写入 `transcript.jsonl`。

也就是说，常规路径下的落盘粒度是“回合结束”，不是“每条消息立刻 fsync”。

### 3.3 direct stream 路径也会 flush

如果走直接流式回复路径，assistant 完整回复拼接后调用：

```python
self._record_assistant_message(AssistantMessage(content=full_response))
```

然后在 direct response 成功时：

```python
self._flush_session_storage()
return
```

因此 direct stream 成功完成后也会落盘。

### 3.4 异常路径会尝试 flush

`chat()` 外层 `except Exception` 中也会调用：

```python
self._flush_session_storage()
```

所以如果 query 或渲染过程中抛出异常，已经进入 buffer 的消息会被尽力写入磁盘。

但注意：如果进程直接崩溃、被 kill、断电，且 buffer 尚未 flush，那么这些 buffered 消息可能丢失。

## 4. 落盘文件形式

### 4.1 metadata.json

`metadata.json` 是格式化 JSON，典型结构：

```json
{
  "session_id": "...",
  "start_time": 1710000000.0,
  "model": "glm-4.5",
  "cwd": "C:\\Users\\Chenx\\Documents\\socrates",
  "title": "用户首条消息生成的标题",
  "total_cost": 0.0,
  "message_count": 3,
  "last_updated": 1710000001.0
}
```

`title` 初始为空；第一条用户输入记录后，如果 title 为空，会通过 `auto_title_from_message(text)` 自动生成并更新 metadata。

`message_count` 在 `flush()` 时按本次 flush 的消息数量累加。

### 4.2 transcript.jsonl

`transcript.jsonl` 每行是一条消息 JSON。写入时使用：

```python
json.dumps(entry, ensure_ascii=False) + "\n"
```

不会整体重写 transcript，而是 append。

消息字段来自 `src/types/messages.py:message_to_dict()`，基础字段包括：

- `role`
- `content`
- `type`
- `uuid`
- `timestamp`
- `isMeta`
- `isVirtual`
- `isCompactSummary`

assistant/system/user 的额外字段会按需写入，例如：

- `stop_reason`
- `model`
- `usage`
- `apiError`
- `error`
- `toolUseResult`
- `permissionMode`
- `origin`
- `attachments`

### 4.3 content/<ref_id>.txt

如果消息里有 `tool_result` block，且其 `content` 是字符串并超过 `LARGE_CONTENT_THRESHOLD = 10_000` 字符，`SessionStorage` 会把完整内容写到：

```text
<session_dir>/content/<ref_id>.txt
```

然后 transcript 中的 block 会变成：

```json
{
  "type": "tool_result",
  "tool_use_id": "...",
  "content": "[content stored: <ref_id>]",
  "_content_ref": "<ref_id>"
}
```

当前有 `load_content(ref_id)` 可以读取这个外置内容。

一个重要边界：恢复时 `message_from_dict()` 会把 tool_result 还原为 `ToolResultBlock`，但不会自动根据 `_content_ref` 反查并恢复原始大文本；模型后续看到的是占位字符串，而不是完整外置内容。`_content_ref` 也不是 `ToolResultBlock` 的字段，会在类型化转换中丢失。

## 5. 内存 conversation 与持久 transcript 的关系

当前实现是“双写”：

```python
self._append_conversation_message(msg)
self._persist_message(msg)
```

也就是说：

- `conversation.messages` 是当前运行中的上下文视图。
- `transcript.jsonl` 是持久化转录。
- `_engine_messages` 是 QueryEngine 下次调用时使用的历史输入。

一次普通用户输入会先写入 REPL 的内存 conversation 和 storage buffer。随后 QueryEngine 也会在内部把同一用户输入 append 到自己的 `_mutable_messages`。由于 REPL 创建 QueryEngine 时传入的是旧的 `_engine_messages`，所以这不会造成 engine 内部重复用户消息；REPL 只是提前把用户输入写入自己的 UI conversation 和持久化 buffer。

回合结束后：

```python
self._engine_messages = engine.get_messages()
```

下一个回合会用这份 engine messages 作为历史。

## 6. 跨对话如何管理

“跨对话”在当前代码里主要靠不同 `session_id` 的目录隔离：

```text
~/.socrates/sessions/<session_id>/
```

每个 session 有自己的：

- `metadata.json`
- `transcript.jsonl`
- `content/`

`SessionStorage.list_sessions()` 会扫描 sessions 根目录下的子目录，读取存在 `metadata.json` 的目录，并按 `last_updated` 倒序返回，默认最多 50 个。

`SessionStorage.cleanup_sessions()` 会按 retention 删除旧 session，默认保留 `DEFAULT_RETENTION_DAYS = 30` 天。判断依据优先使用 `metadata.json` 里的 `last_updated`；没有 metadata 时退回目录 mtime。

当前 REPL 内置命令里有：

```text
/load <session-id>
```

它会调用 `load_session(session_id)`，切换当前 REPL 到另一个 session。

但 CLI 主入口目前没有暴露 `--resume <session-id>` 参数。虽然 `SocratesREPL.__init__()` 支持 `resume_session_id`，普通 `socrates` 启动路径并没有把命令行参数传进去。因此当前用户可见的恢复入口主要是 REPL 内的 `/load <session-id>`，以及测试或代码层直接构造 `SocratesREPL(..., resume_session_id=...)`。

## 7. Session 恢复流程

恢复入口是：

```python
resume_session(session_id, sessions_dir=None, current_cwd=None)
```

流程如下：

1. 构造 `SessionStorage(session_id=session_id)`。
2. 读取 `metadata.json`。
3. 如果 metadata 不存在，返回 `success=False`。
4. 读取 `transcript.jsonl`。
5. 每行 JSON 转换成 typed `Message`。
6. 对孤儿 tool_use 做修复。
7. 处理 compact/snip boundary。
8. 返回 `ResumeResult(messages, metadata, warnings, success=True)`。

REPL 的 `_resume_runtime_session()` 会把恢复结果写回运行态：

```python
self.session.conversation.messages = list(result.messages)
self._engine_messages = list(result.messages)
```

因此恢复后的 conversation 和下一轮 QueryEngine 历史都会来自 transcript。

### 7.1 malformed JSONL 行

`read_transcript()` 逐行读取 JSONL。某行 JSON 解析失败时：

- 记录 warning 日志。
- 跳过该行。
- 继续读取后面的行。

这意味着 transcript 部分损坏时，恢复不是全盘失败，而是尽可能恢复有效行。

### 7.2 typed message 转换失败

如果某个 entry 无法 `message_from_dict()`，`resume_session()` 会跳过该 entry，并把 warning 写入 `ResumeResult.warnings`。

### 7.3 孤儿 tool_use 修复

如果 assistant message 里存在 `tool_use`，但整个消息列表中找不到对应的 `tool_result`，恢复逻辑会插入一个 synthetic user message：

```text
[Tool result missing due to internal error]
```

这样做是为了修复模型 API 所需的 tool_use/tool_result 配对，避免后续对话因为历史消息协议不完整而失败。

注意这里 synthetic result 的 `is_error=False`。而 API normalize 层的 `ensure_tool_result_pairing()` 也有一套配对修复逻辑，会在 API 消息格式层面对缺失工具结果插入 `is_error=True` 的 synthetic result。两者位置不同：

- `resume_session()` 修 typed Message 历史。
- `normalize_messages_for_api()` 修最终发给模型的 API 消息。

### 7.4 compact/snip boundary 处理

`_handle_snip_boundaries()` 会查找最后一个 `isCompactSummary=True` 的消息。如果存在，则只保留：

```text
最后一个 compact summary 及其之后的消息
```

这意味着恢复时不会简单重放 transcript 的全部历史，而是会根据 compact summary 截断早期消息。

## 8. 异常中断怎么处理

当前代码里有几类中断/异常路径。

### 8.1 用户按 ESC 或触发 engine interrupt

REPL 的 LiveStatus cancel 会调用：

```python
engine.interrupt()
```

QueryEngine 内部把 abort reason 设为 `user_interrupt`。

Query loop 内部会根据 abort controller 终止后续执行，并生成必要的中断消息或工具错误结果。REPL 只负责接收 QueryEngine yield 出来的 `AssistantMessage` / `UserMessage` 并记录。

已经 yield 给 REPL 的消息会进入 session buffer，并在回合结束或异常路径 flush。尚未 yield 的中间状态不会持久化。

### 8.2 工具调用半途异常

主 query loop 会尽量保证 assistant 的 `tool_use` 有对应 `tool_result`。如果模型已经产生 tool_use，但后续工具执行、模型调用或中断导致无法正常完成，会生成错误形式的 tool_result，以保持消息协议完整。

恢复阶段还会二次兜底：如果 transcript 里仍存在孤儿 tool_use，则插入 synthetic tool_result。

### 8.3 Python 异常

`SocratesREPL.chat()` 的外层 `except` 会先调用 `_flush_session_storage()`，再展示错误。`_flush_session_storage()` 自身也捕获异常，如果落盘失败，只打印 warning：

```text
Warning: failed to persist session: ...
```

因此常规异常下，已进入 buffer 的消息会被尽力保存；但如果 flush 本身失败，当前代码不会重试、不会写备用文件。

### 8.4 进程级崩溃或强杀

这是当前持久化最薄弱的地方：

- `write_message()` 只是写内存 buffer。
- `transcript.jsonl` 只有 `flush()` 时才追加写。
- transcript append 不是原子替换，也没有显式 fsync。

所以如果进程在 flush 前被强杀，buffer 内消息会丢失。如果进程在写 JSONL 某一行时被强杀，有可能留下半行；恢复时该 malformed 行会被跳过，后续有效行仍可恢复。

metadata 因为使用 `_atomic_write()`，单次 metadata 更新更安全。

## 9. `/clear`、`/compact` 与持久化的关系

这一块需要特别注意，因为当前内存态和持久态并不是完全同步的快照模型。

### 9.1 `/clear`

`/clear` 会：

```python
self.session.conversation.clear()
self._engine_messages = []
```

但它不会清空 `transcript.jsonl`，也不会写入一个 clear marker。也就是说：

- 当前运行内存上下文被清空。
- 持久 transcript 仍保留历史。
- 如果之后用 `/load <same-session-id>` 恢复，历史会从 transcript 回来。

### 9.2 `/compact`

`/compact` 通过 command context 修改 `context.conversation.messages`，即 REPL 的内存 conversation。compact service 会把 conversation 改成 boundary + summary + 保留消息。

但当前 `/compact` 路径没有把 compact 后的新 conversation 作为 transcript 快照重写或追加，也没有同步更新 `_engine_messages` 的明确代码路径。后续普通对话结束时，`_engine_messages` 会被 QueryEngine 的结果覆盖；但如果刚 compact 完就恢复 session，恢复逻辑仍主要依赖旧 transcript 中已有的 compact summary 标记。

换句话说：当前 session storage 更像“append-only 原始转录”，不是“每次内存 conversation 变更后的权威快照”。

## 10. 当前持久化能力总结

当前实现已经具备：

- 每个 session 独立目录。
- metadata 原子写入。
- transcript JSONL append。
- 大 tool_result 外置到 content 文件。
- session 列表与过期清理。
- `/load <session-id>` 恢复。
- malformed JSONL 行跳过。
- 孤儿 tool_use 恢复修复。
- compact boundary 恢复截断。
- 常规异常时尽力 flush。

当前实现的限制：

- transcript 写入是 buffer + 回合末 flush，不是每条消息立刻落盘。
- 进程强杀可能丢失未 flush buffer。
- JSONL append 不是原子事务，半行损坏靠恢复时跳过。
- 大 tool_result 外置后，resume 不会自动 rehydrate 原始内容。
- `/clear` 不影响持久 transcript。
- `/compact` 对持久 transcript 的同步不完整，storage 不是权威快照。
- CLI 没有暴露 `--resume`，用户入口主要是 `/load`。
- `SessionStorage.cleanup_sessions()` 存在但未看到 CLI/REPL 自动调用。

## 11. 一句话结论

当前 Session 管理的核心模型是：

> REPL 维护内存 conversation；SessionStorage 以 append-only JSONL transcript 形式持久化消息；回合结束和异常路径触发 flush；恢复时读取 metadata + transcript，跳过坏行、补齐孤儿工具结果，并根据 compact summary 截断历史。

它已经能覆盖普通跨对话恢复和大多数异常恢复，但还不是严格事务型、快照型的 session 系统。
