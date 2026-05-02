# SRC 代码地图

根据当前 `src` 目录重新生成，日期：2026-05-01。

## 1. 主 Agent Loop 位置

- 主同步 agent loop：`src/tool_system/agent_loop.py::run_agent_loop`，负责模型调用、工具分发、多轮循环和最终回复。
- 交互式入口：`src/repl/core.py::SocratesREPL.chat`。
- 异步 query pipeline：`src/query/query.py::query`。
- 子 agent loop：`src/agent/run_agent.py::run_agent`。

## 2. 当前清理状态

- 已移除迁移期目录和旧入口：`reference_data`、IDE/bridge/remote/direct 相关模块、旧 `src.main`/porting workspace 文件。
- 当前 `src` 下共有 `262` 个 Python 文件。

## 3. 目录树

```text
src/
|-- agent/
|   |-- __init__.py
|   |-- agent_definitions.py
|   |-- agent_tool_utils.py
|   |-- constants.py
|   |-- conversation.py
|   |-- prompt.py
|   |-- run_agent.py
|   |-- session.py
|   `-- subagent_context.py
|-- auth/
|   |-- __init__.py
|   |-- auth.py
|   |-- aws.py
|   |-- gemini.py
|   `-- oauth.py
|-- bootstrap/
|   |-- __init__.py
|   `-- state.py
|-- command_system/
|   |-- __init__.py
|   |-- argument_substitution.py
|   |-- builtins.py
|   |-- engine.py
|   |-- input_processing.py
|   |-- registry.py
|   |-- skills_integration.py
|   `-- types.py
|-- compact_service/
|   |-- messages.py
|   `-- service.py
|-- context_system/
|   |-- __init__.py
|   |-- builder.py
|   |-- claude_md.py
|   |-- context_analyzer.py
|   |-- git_context.py
|   |-- memory_prefetch.py
|   |-- microcompact.py
|   |-- models.py
|   |-- prompt_assembly.py
|   |-- system_prompt_cache.py
|   `-- workspace_snapshot.py
|   |-- __init__.py
|   |-- config_manager.py
|   |-- exec_agent_hook.py
|   |-- exec_http_hook.py
|   |-- exec_prompt_hook.py
|   |-- hook_executor.py
|   |-- hook_types.py
|   |-- post_sampling_hooks.py
|   |-- registry.py
|   |-- session_hooks.py
|   `-- ssrf_guard.py
|-- models/
|   |-- __init__.py
|   |-- agent_routing.py
|   |-- bedrock.py
|   |-- capabilities.py
|   |-- configs.py
|   |-- context.py
|   |-- model.py
|   `-- validation.py
|-- outputStyles/
|   |-- __init__.py
|   |-- loader.py
|   `-- styles.py
|-- permissions/
|   |-- bash_parser/
|   |   |-- __init__.py
|   |   |-- ast_nodes.py
|   |   |-- commands.py
|   |   |-- parser.py
|   |   `-- shell_quote.py
|   |-- __init__.py
|   |-- bash_security.py
|   |-- check.py
|   |-- dangerous_safety.py
|   |-- filesystem.py
|   |-- handler.py
|   |-- loader.py
|   |-- modes.py
|   |-- rule_parser.py
|   |-- rules.py
|   |-- setup.py
|   `-- types.py
|-- plugins/
|   |-- __init__.py
|   |-- builtin_plugins.py
|   |-- dependency.py
|   |-- loader.py
|   |-- lsp_integration.py
|   |-- marketplace.py
|   |-- mcp_integration.py
|   |-- types.py
|   `-- validator.py
|-- providers/
|   |-- __init__.py
|   |-- anthropic_provider.py
|   |-- base.py
|   |-- deepseek_provider.py
|   |-- glm_provider.py
|   |-- minimax_provider.py
|   |-- openai_compatible.py
|   |-- openai_provider.py
|   `-- openrouter_provider.py
|-- query/
|   |-- __init__.py
|   |-- config.py
|   |-- deps.py
|   |-- engine.py
|   |-- query.py
|   |-- stop_hooks.py
|   |-- streaming.py
|   |-- token_budget.py
|   `-- transitions.py
|-- repl/
|   |-- __init__.py
|   |-- at_file_completer.py
|   |-- core.py
|   `-- live_status.py
|-- services/
|   |-- analytics/
|   |   |-- __init__.py
|   |   |-- events.py
|   |   |-- metadata.py
|   |   `-- sink.py
|   |-- api/
|   |   |-- __init__.py
|   |   |-- claude.py
|   |   |-- errors.py
|   |   |-- logging.py
|   |   |-- provider_config.py
|   |   |-- retry.py
|   |   `-- tool_normalization.py
|   |-- compact/
|   |   |-- __init__.py
|   |   |-- autocompact.py
|   |   |-- compact.py
|   |   |-- compact_warning.py
|   |   |-- context_collapse.py
|   |   |-- grouping.py
|   |   |-- pipeline.py
|   |   |-- post_compact_attachments.py
|   |   |-- post_compact_cleanup.py
|   |   |-- prompt.py
|   |   |-- reactive_compact.py
|   |   |-- session_memory_compact.py
|   |   |-- snip_compact.py
|   |   `-- tool_result_budget.py
|   |-- mcp/
|   |   |-- __init__.py
|   |   |-- auth.py
|   |   |-- channel_permissions.py
|   |   |-- client.py
|   |   |-- config.py
|   |   |-- doctor.py
|   |   |-- elicitation.py
|   |   |-- env_expansion.py
|   |   |-- errors.py
|   |   |-- manager.py
|   |   |-- mcp_string_utils.py
|   |   |-- normalization.py
|   |   |-- tool_wrapper.py
|   |   |-- transport.py
|   |   `-- types.py
|   |-- swarm/
|   |   |-- __init__.py
|   |   |-- helpers.py
|   |   |-- permissions.py
|   |   `-- teammate.py
|   |-- tool_execution/
|   |   |-- __init__.py
|   |   |-- orchestrator.py
|   |   |-- streaming_executor.py
|   |   |-- tool_execution.py
|   |   `-- tool_hooks.py
|   |-- __init__.py
|   |-- cost_tracker.py
|   |-- session_resume.py
|   |-- session_storage.py
|   `-- session_title.py
|-- settings/
|   |-- __init__.py
|   |-- change_detector.py
|   |-- constants.py
|   |-- managed_path.py
|   |-- permission_validation.py
|   |-- settings.py
|   |-- types.py
|   `-- validation.py
|-- skills/
|   |-- __init__.py
|   |-- argument_substitution.py
|   |-- bundled_skills.py
|   |-- create.py
|   |-- frontmatter.py
|   |-- loader.py
|   |-- mcp_skill_builders.py
|   `-- model.py
|-- tool_system/
|   |-- tools/
|   |   |-- bash/
|   |   |   |-- __init__.py
|   |   |   |-- background.py
|   |   |   |-- bash_tool.py
|   |   |   |-- command_semantics.py
|   |   |   |-- destructive_warnings.py
|   |   |   |-- prompt.py
|   |   |   |-- read_only_validation.py
|   |   |   |-- search_classification.py
|   |   |   |-- sleep_detection.py
|   |   |   `-- utils.py
|   |   |-- __init__.py
|   |   |-- agent.py
|   |   |-- ask_user_question.py
|   |   |-- brief.py
|   |   |-- config.py
|   |   |-- cron.py
|   |   |-- edit.py
|   |   |-- glob.py
|   |   |-- grep.py
|   |   |-- lsp.py
|   |   |-- mcp.py
|   |   |-- mcp_resources.py
|   |   |-- misc.py
|   |   |-- notebook_edit.py
|   |   |-- plan_mode.py
|   |   |-- read.py
|   |   |-- send_user_message.py
|   |   |-- skill.py
|   |   |-- sleep.py
|   |   |-- structured_output.py
|   |   |-- task_stop.py
|   |   |-- tasks_v2.py
|   |   |-- team.py
|   |   |-- todo_write.py
|   |   |-- tool_search.py
|   |   |-- web_fetch.py
|   |   |-- web_search.py
|   |   |-- worktree.py
|   |   `-- write.py
|   |-- utils/
|   |   |-- __init__.py
|   |   |-- path_utils.py
|   |   `-- ripgrep.py
|   |-- __init__.py
|   |-- agent_loop.py
|   |-- build_tool.py
|   |-- context.py
|   |-- defaults.py
|   |-- diff_utils.py
|   |-- errors.py
|   |-- loader.py
|   |-- protocol.py
|   |-- registry.py
|   |-- schema_validation.py
|   |-- task_manager.py
|   `-- tool_search.py
|-- types/
|   |-- __init__.py
|   |-- content_blocks.py
|   |-- messages.py
|   `-- stream_events.py
|-- utils/
|   |-- __init__.py
|   |-- abort_controller.py
|   |-- deep_link.py
|   |-- effort.py
|   |-- fast_mode.py
|   |-- file_history.py
|   |-- file_state_cache.py
|   |-- git.py
|   |-- messages.py
|   `-- task_flags.py
|-- __init__.py
|-- cli.py
|-- config.py
|-- cost_tracker.py
|-- history.py
|-- query.py
|-- replLauncher.py
|-- token_estimation.py
`-- transcript.py
```

## 4. 包级地图

### `(top-level)`

顶层入口与横切基础模块。

- `src/__init__.py`：包版本与顶层初始化。
- `src/cli.py`: Socrates CLI entry; parses args, resolves permission mode, and starts the REPL.
- `src/config.py`：全局、项目和本地配置的加载、保存、provider 配置与历史记录。
- `src/cost_tracker.py`：顶层成本统计入口，实际成本逻辑在 services 中。
- `src/history.py`：历史记录辅助。
- `src/query.py`：顶层 query 入口模块。
- `src/replLauncher.py`：REPL 启动辅助入口。
- `src/token_estimation.py`：token 粗估算、消息/token 预算相关基础函数。
- `src/transcript.py`：转录和对话记录辅助。

### `agent`

子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。

- `src/agent/__init__.py`：初始化 `agent` 包并导出公共 API。
- `src/agent/agent_definitions.py`：`agent definitions` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。
- `src/agent/agent_tool_utils.py`：`agent tool utils` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。
- `src/agent/constants.py`：`constants` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。
- `src/agent/conversation.py`：`conversation` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。
- `src/agent/prompt.py`：`prompt` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。
- `src/agent/run_agent.py`：子 agent 的异步运行循环。
- `src/agent/subagent_context.py`：`subagent context` 模块，隶属于 子 agent 定义、Agent 工具提示、子 agent 运行循环与上下文隔离。

### `auth`

各 provider 的认证、OAuth、云服务鉴权辅助。

- `src/auth/__init__.py`：初始化 `auth` 包并导出公共 API。
- `src/auth/auth.py`：`auth` 模块，隶属于 各 provider 的认证、OAuth、云服务鉴权辅助。
- `src/auth/aws.py`：`aws` 模块，隶属于 各 provider 的认证、OAuth、云服务鉴权辅助。
- `src/auth/gemini.py`：`gemini` 模块，隶属于 各 provider 的认证、OAuth、云服务鉴权辅助。
- `src/auth/oauth.py`：`oauth` 模块，隶属于 各 provider 的认证、OAuth、云服务鉴权辅助。

### `bootstrap`

进程级启动状态。

- `src/bootstrap/__init__.py`：初始化 `bootstrap` 包并导出公共 API。
- `src/bootstrap/state.py`：`state` 模块，隶属于 进程级启动状态。

### `command_system`

交互式 slash command 的解析、注册、执行和内置命令。

- `src/command_system/__init__.py`：初始化 `command_system` 包并导出公共 API。
- `src/command_system/argument_substitution.py`：`argument substitution` 模块，隶属于 交互式 slash command 的解析、注册、执行和内置命令。
- `src/command_system/builtins.py`：`builtins` 模块，隶属于 交互式 slash command 的解析、注册、执行和内置命令。
- `src/command_system/engine.py`：`engine` 模块，隶属于 交互式 slash command 的解析、注册、执行和内置命令。
- `src/command_system/input_processing.py`：`input processing` 模块，隶属于 交互式 slash command 的解析、注册、执行和内置命令。
- `src/command_system/registry.py`：注册表：保存、查找、去重、分发对应对象。
- `src/command_system/skills_integration.py`：`skills integration` 模块，隶属于 交互式 slash command 的解析、注册、执行和内置命令。
- `src/command_system/types.py`：该包的数据结构和类型定义。

### `compact_service`

compact 消息边界与摘要包装辅助，当前仍服务于运行时 compact 命令。

- `src/compact_service/messages.py`：`messages` 模块，隶属于 compact 消息边界与摘要包装辅助，当前仍服务于运行时 compact 命令。
- `src/compact_service/service.py`：`service` 模块，隶属于 compact 消息边界与摘要包装辅助，当前仍服务于运行时 compact 命令。

### `context_system`

系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。

- `src/context_system/__init__.py`：初始化 `context_system` 包并导出公共 API。
- `src/context_system/builder.py`：同步构建 runtime context prompt。
- `src/context_system/claude_md.py`：`claude md` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/context_analyzer.py`：`context analyzer` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/git_context.py`：`git context` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/memory_prefetch.py`：`memory prefetch` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/microcompact.py`：图片、文档剥离与工具结果 microcompact。
- `src/context_system/models.py`：`models` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/prompt_assembly.py`：系统提示词各段落构建、缓存和上下文拼装。
- `src/context_system/system_prompt_cache.py`：`system prompt cache` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。
- `src/context_system/workspace_snapshot.py`：`workspace snapshot` 模块，隶属于 系统提示词、CLAUDE.md/规则、git/workspace 上下文与 microcompact。

### `hooks`

hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。

- `src/hooks/__init__.py`：初始化 `hooks` 包并导出公共 API。
- `src/hooks/config_manager.py`：`config manager` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/exec_agent_hook.py`：`exec agent hook` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/exec_http_hook.py`：`exec http hook` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/exec_prompt_hook.py`：`exec prompt hook` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/hook_executor.py`：`hook executor` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/hook_types.py`：`hook types` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/post_sampling_hooks.py`：`post sampling hooks` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/registry.py`：注册表：保存、查找、去重、分发对应对象。
- `src/hooks/session_hooks.py`：`session hooks` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。
- `src/hooks/ssrf_guard.py`：`ssrf guard` 模块，隶属于 hook 注册、执行、SSRF 防护、session/post-sampling/tool hook 支撑。

### `models`

模型能力、配置、Bedrock 映射、模型名校验。

- `src/models/__init__.py`：初始化 `models` 包并导出公共 API。
- `src/models/agent_routing.py`：`agent routing` 模块，隶属于 模型能力、配置、Bedrock 映射、模型名校验。
- `src/models/bedrock.py`：`bedrock` 模块，隶属于 模型能力、配置、Bedrock 映射、模型名校验。
- `src/models/capabilities.py`：`capabilities` 模块，隶属于 模型能力、配置、Bedrock 映射、模型名校验。
- `src/models/configs.py`：已知模型配置表。
- `src/models/context.py`：`context` 模块，隶属于 模型能力、配置、Bedrock 映射、模型名校验。
- `src/models/model.py`：模型名解析与展示名辅助。
- `src/models/validation.py`：模型名和设置合法性校验。

### `outputStyles`

输出风格加载与样式定义。

- `src/outputStyles/__init__.py`：初始化 `outputStyles` 包并导出公共 API。
- `src/outputStyles/loader.py`：按所在包语义加载资源、工具、技能或插件。
- `src/outputStyles/styles.py`：`styles` 模块，隶属于 输出风格加载与样式定义。

### `permissions`

权限模式、规则解析、文件安全、bash 安全分析和权限处理。

- `src/permissions/__init__.py`：初始化 `permissions` 包并导出公共 API。
- `src/permissions/bash_parser/__init__.py`：初始化 `permissions/bash_parser` 包并导出公共 API。
- `src/permissions/bash_parser/ast_nodes.py`：`ast nodes` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/bash_parser/commands.py`：`commands` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/bash_parser/parser.py`：`parser` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/bash_parser/shell_quote.py`：`shell quote` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/bash_security.py`：`bash security` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/check.py`：`check` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/dangerous_safety.py`：`dangerous safety` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/filesystem.py`：自动编辑和读写路径的安全检查。
- `src/permissions/handler.py`：`handler` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/loader.py`：按所在包语义加载资源、工具、技能或插件。
- `src/permissions/modes.py`：`modes` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/rule_parser.py`：权限规则字符串解析与序列化。
- `src/permissions/rules.py`：`rules` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/setup.py`：`setup` 模块，隶属于 权限模式、规则解析、文件安全、bash 安全分析和权限处理。
- `src/permissions/types.py`：该包的数据结构和类型定义。

### `plugins`

插件发现、校验、依赖、marketplace、MCP/LSP 集成。

- `src/plugins/__init__.py`：初始化 `plugins` 包并导出公共 API。
- `src/plugins/builtin_plugins.py`：`builtin plugins` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。
- `src/plugins/dependency.py`：`dependency` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。
- `src/plugins/loader.py`：按所在包语义加载资源、工具、技能或插件。
- `src/plugins/lsp_integration.py`：`lsp integration` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。
- `src/plugins/marketplace.py`：`marketplace` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。
- `src/plugins/mcp_integration.py`：`mcp integration` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。
- `src/plugins/types.py`：该包的数据结构和类型定义。
- `src/plugins/validator.py`：`validator` 模块，隶属于 插件发现、校验、依赖、marketplace、MCP/LSP 集成。

### `providers`

Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。

- `src/providers/__init__.py`：初始化 `providers` 包并导出公共 API。
- `src/providers/anthropic_provider.py`：`anthropic provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/base.py`：`base` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/deepseek_provider.py`：`deepseek provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/glm_provider.py`：`glm provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/minimax_provider.py`：`minimax provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/openai_compatible.py`：`openai compatible` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/openai_provider.py`：`openai provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。
- `src/providers/openrouter_provider.py`：`openrouter provider` 模块，隶属于 Anthropic/OpenAI 兼容 provider 以及 DeepSeek/GLM/Minimax/OpenRouter 接入。

### `query`

异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。

- `src/query/__init__.py`：初始化 `query` 包并导出公共 API。
- `src/query/config.py`：`config` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/deps.py`：`deps` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/engine.py`：`engine` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/query.py`：`query` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/stop_hooks.py`：`stop hooks` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/streaming.py`：`streaming` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/token_budget.py`：`token budget` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。
- `src/query/transitions.py`：`transitions` 模块，隶属于 异步 query pipeline、流式处理、token budget、stop hooks 和状态迁移。

### `repl`

交互式 REPL 主体、@ 文件补全和实时状态栏。

- `src/repl/__init__.py`：初始化 `repl` 包并导出公共 API。
- `src/repl/at_file_completer.py`：`at file completer` 模块，隶属于 交互式 REPL 主体、@ 文件补全和实时状态栏。
- `src/repl/core.py`：`core` 模块，隶属于 交互式 REPL 主体、@ 文件补全和实时状态栏。
- `src/repl/live_status.py`：`live status` 模块，隶属于 交互式 REPL 主体、@ 文件补全和实时状态栏。

### `services`

API、compact、MCP、session、swarm、tool execution 等服务层。

- `src/services/__init__.py`：初始化 `services` 包并导出公共 API。
- `src/services/analytics/__init__.py`：初始化 `services/analytics` 包并导出公共 API。
- `src/services/analytics/events.py`：`events` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/analytics/metadata.py`：`metadata` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/analytics/sink.py`：`sink` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/api/__init__.py`：初始化 `services/api` 包并导出公共 API。
- `src/services/api/claude.py`：`claude` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/api/errors.py`：API 错误类型与错误分类。
- `src/services/api/logging.py`：`logging` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/api/provider_config.py`：`provider config` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/api/retry.py`：API 重试、退避和不可重试错误包装。
- `src/services/api/tool_normalization.py`：`tool normalization` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/__init__.py`：初始化 `services/compact` 包并导出公共 API。
- `src/services/compact/autocompact.py`：`autocompact` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/compact.py`：完整 compact 与 partial compact 的核心实现。
- `src/services/compact/compact_warning.py`：`compact warning` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/context_collapse.py`：`context collapse` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/grouping.py`：`grouping` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/pipeline.py`：五层 compression pipeline 编排。
- `src/services/compact/post_compact_attachments.py`：`post compact attachments` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/post_compact_cleanup.py`：`post compact cleanup` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/prompt.py`：`prompt` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/reactive_compact.py`：`reactive compact` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/session_memory_compact.py`：`session memory compact` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/snip_compact.py`：`snip compact` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/compact/tool_result_budget.py`：`tool result budget` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/cost_tracker.py`：`cost tracker` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/__init__.py`：初始化 `services/mcp` 包并导出公共 API。
- `src/services/mcp/auth.py`：`auth` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/channel_permissions.py`：`channel permissions` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/client.py`：`client` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/config.py`：`config` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/doctor.py`：`doctor` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/elicitation.py`：`elicitation` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/env_expansion.py`：`env expansion` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/errors.py`：API 错误类型与错误分类。
- `src/services/mcp/manager.py`：`manager` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/mcp_string_utils.py`：`mcp string utils` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/normalization.py`：`normalization` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/tool_wrapper.py`：`tool wrapper` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/transport.py`：`transport` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/mcp/types.py`：该包的数据结构和类型定义。
- `src/services/session_resume.py`：`session resume` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/session_storage.py`：`session storage` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/session_title.py`：`session title` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/swarm/__init__.py`：初始化 `services/swarm` 包并导出公共 API。
- `src/services/swarm/helpers.py`：`helpers` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/swarm/permissions.py`：`permissions` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/swarm/teammate.py`：`teammate` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/tool_execution/__init__.py`：初始化 `services/tool_execution` 包并导出公共 API。
- `src/services/tool_execution/orchestrator.py`：`orchestrator` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/tool_execution/streaming_executor.py`：`streaming executor` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/tool_execution/tool_execution.py`：`tool execution` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。
- `src/services/tool_execution/tool_hooks.py`：`tool hooks` 模块，隶属于 API、compact、MCP、session、swarm、tool execution 等服务层。

### `settings`

设置模型、默认值、变更检测和权限设置校验。

- `src/settings/__init__.py`：初始化 `settings` 包并导出公共 API。
- `src/settings/change_detector.py`：`change detector` 模块，隶属于 设置模型、默认值、变更检测和权限设置校验。
- `src/settings/constants.py`：`constants` 模块，隶属于 设置模型、默认值、变更检测和权限设置校验。
- `src/settings/managed_path.py`：`managed path` 模块，隶属于 设置模型、默认值、变更检测和权限设置校验。
- `src/settings/permission_validation.py`：`permission validation` 模块，隶属于 设置模型、默认值、变更检测和权限设置校验。
- `src/settings/settings.py`：`settings` 模块，隶属于 设置模型、默认值、变更检测和权限设置校验。
- `src/settings/types.py`：该包的数据结构和类型定义。
- `src/settings/validation.py`：模型名和设置合法性校验。

### `skills`

SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。

- `src/skills/__init__.py`：初始化 `skills` 包并导出公共 API。
- `src/skills/argument_substitution.py`：`argument substitution` 模块，隶属于 SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。
- `src/skills/bundled_skills.py`：`bundled skills` 模块，隶属于 SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。
- `src/skills/create.py`：`create` 模块，隶属于 SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。
- `src/skills/frontmatter.py`：`frontmatter` 模块，隶属于 SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。
- `src/skills/loader.py`：按所在包语义加载资源、工具、技能或插件。
- `src/skills/mcp_skill_builders.py`：`mcp skill builders` 模块，隶属于 SKILL.md 技能模型、加载、frontmatter、参数替换和内置技能。
- `src/skills/model.py`：模型名解析与展示名辅助。

### `tool_system`

工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。

- `src/tool_system/__init__.py`：初始化 `tool_system` 包并导出公共 API。
- `src/tool_system/agent_loop.py`：主 agent loop：驱动模型调用、工具调用、权限检查和多轮循环。
- `src/tool_system/build_tool.py`：`build tool` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/context.py`：`context` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/defaults.py`：`defaults` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/diff_utils.py`：`diff utils` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/errors.py`：API 错误类型与错误分类。
- `src/tool_system/loader.py`：按所在包语义加载资源、工具、技能或插件。
- `src/tool_system/protocol.py`：`protocol` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/registry.py`：注册表：保存、查找、去重、分发对应对象。
- `src/tool_system/schema_validation.py`：`schema validation` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/task_manager.py`：`task manager` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tool_search.py`：`tool search` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/__init__.py`：初始化 `tool_system/tools` 包并导出公共 API。
- `src/tool_system/tools/agent.py`：Agent 工具定义，启动同步或后台子 agent。
- `src/tool_system/tools/ask_user_question.py`：`ask user question` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/__init__.py`：初始化 `tool_system/tools/bash` 包并导出公共 API。
- `src/tool_system/tools/bash/background.py`：`background` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/bash_tool.py`：Bash 工具执行、超时、后台任务和安全检查入口。
- `src/tool_system/tools/bash/command_semantics.py`：`command semantics` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/destructive_warnings.py`：`destructive warnings` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/prompt.py`：`prompt` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/read_only_validation.py`：`read only validation` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/search_classification.py`：`search classification` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/sleep_detection.py`：`sleep detection` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/bash/utils.py`：`utils` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/brief.py`：`brief` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/config.py`：`config` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/cron.py`：`cron` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/edit.py`：`edit` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/glob.py`：`glob` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/grep.py`：`grep` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/lsp.py`：`lsp` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/mcp.py`：`mcp` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/mcp_resources.py`：`mcp resources` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/misc.py`：`misc` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/notebook_edit.py`：`notebook edit` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/plan_mode.py`：`plan mode` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/read.py`：`read` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/send_user_message.py`：`send user message` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/skill.py`：Skill 工具定义，只执行已注册的 SKILL.md prompt 技能。
- `src/tool_system/tools/sleep.py`：`sleep` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/structured_output.py`：`structured output` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/task_stop.py`：`task stop` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/tasks_v2.py`：`tasks v2` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/team.py`：`team` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/todo_write.py`：`todo write` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/tool_search.py`：`tool search` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/web_fetch.py`：`web fetch` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/web_search.py`：`web search` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/worktree.py`：`worktree` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/tools/write.py`：`write` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/utils/__init__.py`：初始化 `tool_system/utils` 包并导出公共 API。
- `src/tool_system/utils/path_utils.py`：`path utils` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。
- `src/tool_system/utils/ripgrep.py`：`ripgrep` 模块，隶属于 工具协议、注册表、默认工具池、Agent 主循环和所有内置工具。

### `types`

消息、内容块和流事件类型。

- `src/types/__init__.py`：初始化 `types` 包并导出公共 API。
- `src/types/content_blocks.py`：`content blocks` 模块，隶属于 消息、内容块和流事件类型。
- `src/types/messages.py`：`messages` 模块，隶属于 消息、内容块和流事件类型。
- `src/types/stream_events.py`：`stream events` 模块，隶属于 消息、内容块和流事件类型。

### `utils`

通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。

- `src/utils/__init__.py`：初始化 `utils` 包并导出公共 API。
- `src/utils/abort_controller.py`：`abort controller` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/deep_link.py`：`deep link` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/effort.py`：`effort` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/fast_mode.py`：`fast mode` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/file_history.py`：`file history` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/file_state_cache.py`：`file state cache` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/git.py`：`git` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/messages.py`：`messages` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
- `src/utils/task_flags.py`：`task flags` 模块，隶属于 通用工具：中止控制、deep link、effort、文件状态、git、消息处理、任务开关。
