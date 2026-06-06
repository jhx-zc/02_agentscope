# AgentScope 2.0 Memory 调研与问题清单

> 调研日期：2026-06-06
>
> 目标：确认 AgentScope 2.0 官方原生 memory/context 实现方式，并把当前项目中和 memory 接入相关的问题落盘。

## 结论

AgentScope 2.0 当前官方方案里，传统 `agentscope.memory` 模块已经不再是推荐入口。2.0 把短期记忆和上下文管理放进 `AgentState.context`、`AgentState.summary`、`ContextConfig`、`Offloader/Workspace` 等机制中，由 `Agent` 在 `reply_stream` / ReAct 流程里自动维护。

本项目当前的 memory 实现属于“自定义 JSON 长期偏好存储 + memory tools + 启动时手动注入 context”，可以继续用于课程演示，但它不是 AgentScope 2.0 原生 memory backend。

## 官方 2.0 方案

### 1. 上下文就是 2.0 的主要短期 memory

AgentScope 2.0 的 `Agent` 构造函数接收 `state`、`context_config`、`offloader`，而不是旧版文档中的 `memory=` 参数。本地依赖版本确认如下：

- 本地包版本：`agentscope==2.0.0`
- `Agent(...)` 参数包含：`toolkit`、`state`、`offloader`、`context_config`、`react_config`
- 本地包中没有 `agentscope.memory` 模块

短期会话历史由 `AgentState.context` 保存，压缩摘要由 `AgentState.summary` 保存。Agent 在处理用户输入时会把合法的 `Msg` 追加到 `state.context`，并在上下文过长时通过 `compress_context()` 生成 summary，再保留较新的 context。

### 2. ContextConfig 负责上下文压缩策略

2.0 的原生上下文管理重点在 `ContextConfig`：

- `trigger_ratio`：达到模型上下文窗口比例后触发压缩。
- `reserve_ratio`：压缩时保留最近上下文的比例。
- `compression_prompt`：用于要求模型生成 continuation summary。
- `summary_template` / `summary_schema`：控制压缩摘要结构。
- `tool_result_limit`：限制 tool result 注入上下文的长度。

这意味着长期偏好、项目规则、用户规则如果直接塞进 `state.context`，可能会被当作普通对话一起压缩和摘要，而不是稳定的可检索长期 memory。

### 3. Offloader / Workspace 承担大上下文外置

2.0 支持 `offloader`。当上下文压缩时，旧 context 可以被 offload 到 workspace/storage，并在 summary 中保留引用。这更像是 AgentScope 2.0 原生的“大上下文存储和恢复”机制。

它解决的是“上下文太长”的问题，不等价于“用户偏好长期记忆检索”。如果要做用户偏好长期记忆，仍然需要自定义 store 或外部系统，但应该通过清晰的 adapter/tool 暴露，而不是伪装成普通 user message。

### 4. 旧 memory 文档不适合直接照搬到本项目

官方旧文档里还能看到 `InMemoryMemory`、`LongTermMemoryBase`、`ReActAgent(memory=...)` 等写法。但该页面属于旧版/Stable(v1.0) 文档，不匹配当前项目安装的 `agentscope==2.0.0` API。

当前项目如果按旧文档迁移，会遇到：

- `import agentscope.memory` 失败。
- `Agent(..., memory=...)` 参数不存在。
- `ReActAgent` 和当前项目使用的 `agentscope.agent.Agent` 构造契约不一致。

## 本项目现状

### 1. 自定义 JSON 长期偏好

位置：

- `src/agentscope_tools/ori_tools/memory.py`

当前结构：

```json
{
  "version": 1,
  "kind": "user_preferences",
  "updated_at": "...",
  "preferences": {
    "key": {
      "key": "...",
      "value": "...",
      "category": "general",
      "source": "user",
      "created_at": "...",
      "updated_at": "...",
      "hard": false
    }
  }
}
```

判断：

- 适合作为“课程演示级长期偏好 store”。
- 不属于 AgentScope 2.0 原生 memory。
- 目前没有 `session_id`、`user_id`、`agent_id` 隔离。
- 目前没有并发写保护。

### 2. Memory tools 暴露给 AgentScope Toolkit

位置：

- `src/agentscope_tools/agentscope_wrapper.py`

已注册工具：

- `user_memory_outline`
- `user_memory_save_preference`
- `user_memory_get_preference`
- `user_memory_list_preferences`
- `user_memory_delete_preference`
- `user_memory_clear_preferences`

判断：

- 作为 AgentScope tool 暴露是合理的。
- 这让 AgentScope/LLM 能自动选择是否读取或写入偏好。
- 但这不是框架自动 memory 管理，而是“由 Agent 自动调度 memory tools”。

### 3. 启动时手动注入 memory 到 context

位置：

- `src/agentscope_course/agent.py`

当前逻辑：

```python
agent.state.context.append(UserMsg(name="user", content=init_user_memory()))
```

判断：

- 消息格式上兼容 AgentScope 2.0 的 `state.context`。
- 语义上不够合理：它把 memory outline / hard memories 伪装成普通 user message。
- 后续压缩时，这些内容会作为普通会话历史被总结，可能重复、丢失或污染上下文。

## 已落盘问题

### P0-1：旧版 memory 文档和当前 2.0 API 不匹配

- 位置：项目整体依赖与调研资料
- 问题：旧文档里的 `agentscope.memory`、`InMemoryMemory`、`LongTermMemoryBase`、`ReActAgent(memory=...)` 在当前本地 `agentscope==2.0.0` 中不可用。
- 影响：如果按旧文档改造，会直接出现 import 或构造参数错误。
- 最小方案：以 `docs.agentscope.io/v2/...` 文档和本地 API 为准，把 memory 迁移目标定义为 `AgentState.context + ContextConfig + Offloader + 自定义长期偏好 tool adapter`。

### P0-2：当前 memory 没有会话/用户/Agent 隔离

- 位置：`src/agentscope_tools/ori_tools/memory.py`
- 问题：所有偏好写入同一个 `.agentscope_memory/user_preferences.json`。
- 影响：多用户、多会话、多 Agent 时会串数据，AgentScope 自动调度 memory tools 时无法判断作用域。
- 最小方案：在 memory record 或文件路径中加入 `user_id`、`agent_id`、`session_id` 中至少一种作用域；课程演示可以先固定 `agent_id` 或 `profile_id`。

### P0-3：memory 初始化绕开了 2.0 context 语义

- 位置：`src/agentscope_course/agent.py`
- 问题：用 `UserMsg(name="user", content=init_user_memory())` 手动把 memory 注入 `state.context`。
- 影响：AgentScope 会把它视为普通用户消息；压缩、摘要和上下文保留策略无法区分 memory 与用户输入。
- 最小方案：不要作为普通 user message 注入。短期可以改成带 metadata 的初始化 context block；更稳妥的是只注入 hard memories 的 system/context hint，普通偏好通过 memory tools 按需读取。

### P0-4：memory 写入没有并发保护

- 位置：`src/agentscope_tools/ori_tools/memory.py`
- 问题：`_save_store()` 用临时文件 replace，但没有进程内或进程间锁。
- 影响：AgentScope 如果并发调度多个 memory 写工具，可能出现后写覆盖先写。
- 最小方案：memory mutable tools 标记 `is_concurrency_safe=False`；同时给 `_load_store` + `_save_store` 增加写锁。

### P1-1：memory list tool 容易 bulk-load 全量偏好

- 位置：`user_memory_list_preferences`
- 问题：该 tool 返回完整 memory records，包括完整 `value`。
- 影响：AgentScope 自动调用后会把大量长期偏好塞入上下文，违背 progressive retrieval。
- 最小方案：默认返回 outline，不返回 full value；保留 `user_memory_get_preference(key)` 作为精确读取入口。

### P1-2：memory result 作为 JSON 文本返回，结构语义较弱

- 位置：`src/agentscope_tools/agentscope_wrapper.py`
- 问题：所有 dict/list 都被 `json.dumps` 放进 `TextBlock`。
- 影响：LLM 能读，但框架层无法稳定区分 `ok/data/error` 等结构。
- 最小方案：统一 memory tool 返回 envelope，例如 `{"ok": true, "data": ..., "error": null}`；后续再评估是否使用 AgentScope `DataBlock`。

### P1-3：hard memory 类型标注不准确

- 位置：`hard_user_memories`
- 问题：函数标注为 `dict[str, Any]`，实际返回 list。
- 影响：如果未来注册为 tool 或用于 schema 生成，会误导框架和维护者。
- 最小方案：改为 `list[dict[str, Any]]`，补 docstring。

### P2-1：缺少长期 memory adapter

- 位置：`src/agentscope_tools/ori_tools/memory.py`
- 问题：JSON 文件读写和 tool 语义混在一起。
- 影响：后续切换 SQLite、向量库、Redis 或远端服务时，需要修改 tool 业务逻辑。
- 最小方案：抽 `PreferenceMemoryStore`，tool 只负责 schema、权限和调用 store。

### P2-2：没有区分 session context 和 long-term preferences

- 位置：`agent.py`、`memory.py`
- 问题：硬偏好、普通偏好、当前会话上下文都可能进入 `state.context`。
- 影响：AgentScope 的 context compression 会把不同生命周期的信息混在一起处理。
- 最小方案：明确三层：
  - session context：交给 AgentScope `state.context`。
  - compressed context：交给 `ContextConfig` / `summary`。
  - long-term preferences：保留在 memory tool adapter 中，按需读取。

## 最小迁移建议

1. 不要引入旧版 `agentscope.memory` API。
2. 保留现有 memory tools，但把它们明确命名为 long-term preference tools。
3. 改掉启动时普通 `UserMsg` 注入 memory 的做法。
4. 只把 hard memories 作为稳定 system/context hint 注入；普通 memories 让 AgentScope 通过 tool 自动读取。
5. 给 memory store 增加作用域字段和并发保护。
6. 配置 `ContextConfig`，显式控制 summary 和 tool result 长度。
7. 如果后续需要持久化完整 Agent 会话状态，优先保存/恢复 `AgentState`，而不是自己维护聊天 history。

## 参考资料

- AgentScope 2.0 Context 官方文档：<https://docs.agentscope.io/v2/building-blocks/context>
- AgentScope 2.0 Agent 官方文档：<https://docs.agentscope.io/v2/building-blocks/agent>
- AgentScope 2.0 Workspace / Offloader 官方文档：<https://docs.agentscope.io/v2/building-blocks/workspace>
- AgentScope 2.0 Change Log：<https://docs.agentscope.io/v2/change-log>
- 旧版 Memory 文档，仅用于辨别 API 差异：<https://doc.agentscope.io/tutorial/task_memory.html>
