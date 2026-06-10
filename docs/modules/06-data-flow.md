# 模块六：数据流与事件追踪

## 数据流总览

项目中的三种独立数据流：

| 数据流 | 方向 | 存储 | 用途 |
|--------|------|------|------|
| **事件流** | AgentScope → console + trace | 终端实时 + `agentscope_events.jsonl` | 用户可见的交互记录 |
| **追踪流** | 装饰器 → trace recorder | `.agentscope_traces/*.jsonl` + `*.summary.json` | 开发调试与性能分析 |
| **文件操作流** | 工具函数 → 文件系统 | 原始 Markdown 文件 | Agent 的实际工作成果 |

---

## 6.1 AgentScope 事件流（`agentscope_events.jsonl`）

### 记录路径

由 `StreamConsoleRenderer` 的 `_write_event_log()` 产生，写入项目根目录的 `agentscope_events.jsonl`。

### 事件分类

#### Source: `agentscope`（AgentScope SDK 原生事件）

| 事件类 | 触发时机 | 关键字段 | 渲染表现 |
|--------|---------|---------|---------|
| `TextBlockDeltaEvent` | LLM 文本输出流 | `delta` (文本片段) | `🤖 Assistant: ...` |
| `ToolCallStartEvent` | Agent 决定调用工具 | `tool_call_id`, `tool_call_name` | `🔧 [1/2] tool_name` |
| `ToolCallDeltaEvent` | 工具参数实时流入 | `tool_call_id`, `delta` | 面板中实时显示 args |
| `ToolCallEndEvent` | 参数收集完成 | `tool_call_id` | status: ready |
| `RequireUserConfirmEvent` | 需要用户确认 | `tool_calls` 列表 | `⚠️ waiting approval` |
| `ToolResultStartEvent` | 工具开始执行 | `tool_call_id` | status: running |
| `ToolResultTextDeltaEvent` | 工具输出流 | `tool_call_id`, `delta` | output: 区域 |
| `ToolResultDataDeltaEvent` | 工具数据输出 | `media_type`, `data`, `url` | data: text/plain |
| `ToolResultEndEvent` | 工具执行完毕 | `tool_call_id`, `state` | status: finished |

#### Source: `local`（项目自定义事件）

| 事件名 | 触发时机 | 关键字段 |
|--------|---------|---------|
| `permission_decision` | 用户确认决定 | `tool_call_id`, `confirmed` |
| `user_confirm_result` | 确认结果发回 AgentScope | `reply_id`, `confirm_results[]` |
| `external_execution_blocked` | 外部工具无法执行 | `tool_names` |
| `task_continuation` | 自动触发任务延续 | `task_ids` |
| `unresolved_tool_call` | 本轮回合未执行的调用 | `tool_call_id`, `tool_name` |
| `turn_error` | 轮次中出现异常 | `error_type`, `message` |

### 事件记录格式

```json
{
  "seq": 42,
  "renderer_id": "a1b2c3d4e5f6...",
  "ts": "2026-06-08T08:17:05.123456+00:00",
  "source": "agentscope",
  "event_class": "ToolCallStartEvent",
  "event_type": null,
  "reply_id": "...",
  "tool_call_id": "resp123_0_markdown_outline",
  "tool_call_name": "markdown_outline"
}
```

### 事件序号

- 从 1 开始自增
- 每个 renderer 实例独立计数
- `renderer_id` 用于区分不同会话/实例

---

## 6.2 追踪记录流（Trace）

### 每次运行产生的文件

```
.agentscope_traces/
├── 20260608-081705-<run_id_prefix>.jsonl          ← 完整事件流
└── 20260608-081705-<run_id_prefix>.summary.json   ← 运行摘要
```

### JSONL 记录类型

`TraceRecorder._write()` 产生的结构化事件：

| 事件 | seq 前缀 | 关键字段 | 用途 |
|------|---------|---------|------|
| `run_start` | ✅ | `cwd`, `jsonl_path` | 运行开始标记 |
| `turn_start` | ✅ | `turn_index`, `user_input` | 新对话轮次 |
| `assistant_text_delta` | ✅ | `delta`, `delta_len` | 文本增量记录 |
| `tool_call_start` | ✅ | `reply_id`, `tool_call_id`, `tool_name` | 工具调用注册 |
| `tool_call_ready` | ✅ | `tool_call_id`, `args` (已解析) | 工具参数完整 |
| `agent_event` | ✅ | `event_class`, `fields` | AgentScope 原生事件转发 |
| `confirmation_request` | ✅ | `tool_calls[]`, `tool_call_count` | 确认请求记录 |
| `tool_execution_start` | ✅ | `execution_id`, `candidate_paths` | 执行开始 + 文件快照 |
| `tool_execution_end` | ✅ | `status`, `result`, `file_changes` | 执行结束 + diff |
| `turn_end` | ✅ | `assistant_text`, `file_changes` | 轮次摘要 |
| `run_end` | ✅ | `turn_count` | 运行结束 |

### 运行摘要格式（summary.json）

```json
{
  "schema_version": 1,
  "run_id": "a1b2c3d4e5f6...",
  "started_at": "2026-06-08T08:17:05+00:00",
  "ended_at": "2026-06-08T08:18:12+00:00",
  "jsonl_path": ".agentscope_traces/20260608-081705-xxx.jsonl",
  "turn_count": 3,
  "turns": [
    {
      "turn_id": "...",
      "turn_index": 1,
      "assistant_text": "你好，我是你的 Agent 助手...",
      "assistant_text_len": 1250,
      "file_changes": [/* 文件 diff 记录 */],
      "unmatched_tool_calls": []
    }
  ]
}
```

---

## 6.3 文件变更追踪（Diff 流程）

```
工具执行前 (begin_tool_execution)
  │
  ├── 扫描候选路径:
  │   ├── args.get("path") 中的路径
  │   └── 特定工具（memory）的固定路径
  │
  └── 对每个路径创建 FileSnapshot:
      ├── exists: bool
      ├── sha256: str | None
      └── text: str | None (仅 UTF-8 文件)
    
工具执行中 (实际函数运行)

工具执行后 (end_tool_execution)
  │
  ├── 重新扫描相同路径
  ├── 对比 before/after:
  │   ├── created    → 新建文件
  │   ├── deleted    → 删除文件
  │   ├── modified   → sha256 不一致
  │   └── unchanged  → 无变化
  │
  └── 对 changed 文件生成 unified diff
      └── 截断保护: MAX_DIFF_CHARS (30000)
```

### 工具 vs 候选路径映射

| 工具名称 | 追踪路径来源 |
|----------|------------|
| `markdown_outline` | `args.path` |
| `markdown_get_section` | `args.path` |
| `markdown_replace_section` | `args.path` |
| `markdown_insert_after_heading` | `args.path` |
| `markdown_update_task_status` | `args.path` |
| `markdown_format_file` | `args.path` |
| `user_memory_save_preference` | `args.path` + 固定路径 |
| `user_memory_delete_preference` | 固定路径 |
| `user_memory_clear_preferences` | 固定路径 |

### Diff 输出示例

```json
{
  "path": "/Users/allen/workspace/.../Test.md",
  "relative_path": "Test.md",
  "change_type": "modified",
  "before_sha256": "abc123...",
  "after_sha256": "def456...",
  "before_size": 2807,
  "after_size": 3621,
  "line_delta": 15,
  "unified_diff": "--- a/Test.md\n+++ b/Test.md\n@@ -1,6 +1,8 @@\n+# 新内容\n...",
  "diff_truncated": false
}
```

---

## 6.4 工具调用匹配机制

trace 中的工具调用跟踪需要 Bridge **两个事件流**：

1. AgentScope **流事件**（`record_tool_call_start` → `record_tool_call_ready`）
2. 工具包装器**实际执行**（`begin_tool_execution` → `end_tool_execution`）

### 匹配算法

```python
def _match_tool_call(self, tool_name, args):
    # 1. 精确匹配: 工具名相同 + 参数字典完全相同
    # 2. 回退匹配: 工具名相同（无论参数）
    # 3. 无匹配: 返回 None（可能是未跟踪的调用）
    for call in self._pending_tool_calls:
        if call.matched or call.tool_name != tool_name:
            continue
        parsed = json.loads(call.args_text)
        if json.dumps(parsed, sort_keys=True) == json.dumps(args, sort_keys=True):
            return call.tool_call_id  # 精确匹配
    # 回退: 第一个未匹配的同名调用
    return fallback.tool_call_id
```

未匹配的调用会在 `turn_end` 的 `unmatched_tool_calls` 中记录。

---

## 6.5 错误处理与恢复

### CLI 层级

```python
try:
    await reply_until_done(...)
except Exception as exc:
    trace_recorder.record_local_event("turn_error", ...)
    raise  # 重新抛出，不静默
```

### 追踪层级

```python
try:
    result = func(**kwargs)
except Exception as exc:
    recorder.end_tool_execution(execution, status="error", error=exc)
    raise  # 重新抛出
```

### 事件日志层级

```python
try:
    with log_file.open("a") as f:
        f.write(...)
except OSError:
    self._event_log_failed = True  # 静默降级
```

### 键盘中断

```python
except (KeyboardInterrupt, EOFError):
    print("\n👋 再见！")
finally:
    trace_recorder.close()  # 确保日志完整写入
```

---

## 6.6 三种日志的数据对比

| 特性 | agentscope_events.jsonl | .agentscope_traces/*.jsonl | .agentscope_traces/*.summary.json |
|------|------------------------|---------------------------|-----------------------------------|
| **粒度** | 事件级别 | 事件级别 + 工具执行 | 轮次摘要 |
| **包含内容** | AgentScope 事件 + 本地事件 | 全部 + 文件快照 + diff | 运行层级摘要 |
| **大小** | 累积增长（单文件） | 每次运行独立 | 每次运行独立 |
| **主要用途** | UI 渲染调试 | 开发调试、性能分析 | 快速查看运行结果 |
| **截断** | 单字段 1000 字符 | 文本 20000 / diff 30000 | 已预聚合 |
| **写入方式** | 所有事件全量写入 | 按事件类型结构化 | 运行结束时一次写入 |
