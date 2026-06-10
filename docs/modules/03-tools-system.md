# 模块三：工具系统 — `agentscope_tools/`

## 包概览

- **路径**: `src/agentscope_tools/`
- **总文件数**: 15 个 Python 文件（含 `__pycache__` 和 `__init__`）
- **职责**: 将普通 Python 函数包装为 Agent 可理解的工具，供 LLM 自主调用

```
agentscope_tools/
├── __init__.py                        # 统一导出（兼容层 + 顶层 API）
├── agentscope_wrapper.py              # AgentScope FunctionTool 注册中心
│
├── editor.py                          # 兼容重导出 → ori_tools/editor.py
├── formatter.py                       # 兼容重导出 → ori_tools/formatter.py
├── parser.py                          # 兼容重导出 → ori_tools/parser.py (注意：指向 cli.py，存在死引用)
├── memory.py                          # 兼容重导出 → ori_tools/memory.py
├── markdown.py                        # 兼容重导出 → ori_tools/cli.py (可能不存在)
│
└── ori_tools/                         # 工具原始实现（9 个工具）
    ├── __init__.py                    # 统一导出
    ├── scanner.py                     # 📂 目录扫描
    ├── parser.py                      # 📋 Markdown 解析（大纲/章节/任务）
    ├── editor.py                      # ✏️  Markdown 编辑（替换/插入/更新）
    ├── formatter.py                   # 🎨 Markdown 格式化（mdformat）
    └── memory.py                      # 🧠 用户偏好记忆（JSON 文件）
```

---

## 3.1 `__init__.py` — 顶层导出

- **依赖**: `agentscope_tools.ori_tools.*` + `agentscope_wrapper`

统一导出所有工具函数加上 `create_markdown_toolkit` 和 `init_user_memory`。提供了完整的 `__all__` 列表供外部导入。

**关键导出**:

```python
__all__ = [
    "init_user_memory",
    "iter_outline", "markdown_get_section", "markdown_list_tasks",
    "markdown_outline", "markdown_scan_directory",
    "markdown_insert_after_heading", "markdown_replace_section",
    "markdown_update_task_status",
    "markdown_check_format", "markdown_format_file",
    "user_memory_*",  # 6 个记忆工具
    "create_markdown_toolkit",
]
```

---

## 3.2 `agentscope_wrapper.py` — 工具注册中心

- **行数**: 219 行
- **依赖**: `agentscope.tool.*` + `ori_tools.*` + `trace.py`

### 职责

将普通 Python 函数包装为 AgentScope 的 `FunctionTool`，并组织成工具组（`ToolGroup`）注册到 `Toolkit` 中。

### 架构

```
create_markdown_toolkit()
  └── Toolkit(
        skills_or_loaders=SKILLS_ROOTS,   ← 技能文件路径
        tool_groups=[                      ← 4 个工具组
          ToolGroup("markdown_read",    ← 📖 只读工具
            tools=[markdown_scan_directory, markdown_outline,
                   markdown_get_section, markdown_check_format]
          ),
          ToolGroup("markdown_write",   ← ✏️ 写操作工具
            tools=[markdown_replace_section,
                   markdown_insert_after_heading,
                   markdown_format_file]
          ),
          ToolGroup("memory",           ← 🧠 用户偏好
            tools=[user_memory_outline, user_memory_save_preference,
                   user_memory_get_preference, user_memory_list_preferences,
                   user_memory_delete_preference, user_memory_clear_preferences]
          ),
          ToolGroup("task_management",  ← 📋 内部任务规划
            tools=[TaskCreate, TaskGet, TaskList, TaskUpdate]
          ),
        ],
      )
```

### 工具分组策略

| 工具组 | 工具数 | 只读? | 用途 | 安全要求 |
|--------|--------|-------|------|---------|
| `markdown_read` | 4 | ✅ | 扫描、大纲、读取章节、检查格式 | 无风险，自动放行 |
| `markdown_write` | 3 | ❌ | 替换章节、插入内容、格式化 | 写操作需感知 |
| `memory` | 6 | 混合 | 偏好 CRUD + 浏览 | 写入需感知 |
| `task_management` | 4 | ❌ | Agent 内部任务规划 | Agent 内部控制 |

### 工具包装流程

```python
# 1. 原始 Python 函数 → FunctionTool
_function_tool(markdown_outline, is_read_only=True)

# 2. FunctionTool 内部：
#    a. 自动提取函数的 __name__, __doc__, 类型注解
#    b. 生成 Agent 可理解的 name/description/input_schema

# 3. 追踪装饰器（_wrap_tool_result）
#    a. 函数执行前：recorder.begin_tool_execution() → 快照文件
#    b. 函数执行后：recorder.end_tool_execution() → diff + 记录
#    c. 异常 → 记录错误状态
```

### 追踪装饰器 `_wrap_tool_result`

```python
@wraps(func)
def wrapped(**kwargs):
    recorder = current_trace_recorder()
    if recorder:
        execution = recorder.begin_tool_execution(func.__name__, kwargs)
    try:
        result = func(**kwargs)
    except Exception as exc:
        # 记录错误 → 重新抛出
        recorder.end_tool_execution(execution, status="error", error=exc)
        raise
    recorder.end_tool_execution(execution, status="success", result=result)
    return ToolChunk(content=[TextBlock(text=json.dumps(result))])
```

### 内存初始化

`init_user_memory()` 在 Agent 启动时被调用，将记忆信息注入初始对话上下文：

```python
def init_user_memory():
    return [
        TextBlock(text='User Memory outline:'),
        TextBlock(text=_format_tool_result(user_memory_outline())),
        TextBlock(text='User Hard Memories:'),
        TextBlock(text=_format_tool_result(hard_user_memories())),
    ]
```

### 技能文件路径

```python
SKILLS_ROOTS = [
    "项目根/.skills/markdown-workspace",
    "项目根/.skills/plan-mode-task-management",
    "项目根/.skills/user-memory-preferences",
]
```

---

## 3.3 兼容重导出文件

以下文件仅做向后兼容导出，所有真正的实现已迁移到 `ori_tools/`：

| 文件 | 原始位置 → 新位置 | 导出的关键内容 |
|------|-------------------|----------------|
| `editor.py` | → `ori_tools/editor.py` | 所有编辑工具 + 内部函数 |
| `formatter.py` | → `ori_tools/formatter.py` | `markdown_format_file`, `markdown_check_format` |
| `parser.py` | → `ori_tools/parser.py` | 解析工具 + `_containing_section`, `_read_markdown` |
| `memory.py` | → `ori_tools/memory.py` | 所有记忆工具 + `MEMORY_DIR`, `USER_PREFERENCES_PATH` |
| `markdown.py` | → `ori_tools/cli.py` （不存在） | `main`, `markdown_get_section`, `markdown_outline` |

> ⚠️ **注意**: `markdown.py` 引用了 `ori_tools/cli.py`，但该文件当前不存在。这是一个死引用，但不会影响正常运行，因为 `markdown.py` 本身没有被任何运行时路径导入。

---

## 3.4 `ori_tools/scanner.py` — 目录扫描器

- **行数**: 89 行
- **依赖**: 仅标准库（`pathlib`, `typing`）

### 工具接口

```python
markdown_scan_directory(
    path: str | None = None,     # 扫描路径，默认 WORKSPACE_ROOT
    recursive: bool = True,      # 是否递归子目录
    include_hidden: bool = False # 是否包含隐藏文件
) -> dict[str, Any]
```

### 返回值结构

```json
{
  "root": "/Users/.../02_agentscope",
  "workspace": "/Users/.../02_agentscope",
  "recursive": true,
  "include_hidden": false,
  "extensions": [".md", ".markdown"],
  "count": 3,
  "files": [
    {"path": "/abs/path/Test.md", "relative_path": "Test.md", "name": "Test.md", "size_bytes": 2807},
    {"path": "/abs/path/task_demo.md", "relative_path": "task_demo.md", "name": "task_demo.md", "size_bytes": 5179}
  ]
}
```

### 关键设计

| 设计点 | 实现 | 理由 |
|--------|------|------|
| 隐藏文件过滤 | `path.parts` 检查 `.` 开头组件 | 避免扫描 `.git`、`.venv` 等 |
| 后缀过滤 | `{".md", ".markdown"}` | 只处理 Markdown 文件 |
| 绝对路径 | 返回 `Path.resolve()` | 下游工具直接使用，无需关心 CWD |
| 排序 | 按 `relative_path` 排序 | 输出确定性，方便定位 |
| 常量 | `WORKSPACE_ROOT = Path.cwd().resolve()` | 启动时锁定，防止后续 `chdir` 改变语义 |

---

## 3.5 `ori_tools/parser.py` — Markdown 解析器

- **行数**: 241 行
- **依赖**: `markdown-it-py`（MarkdownIt 解析器）

### 工具接口

| 工具 | 参数 | 返回值 | 关键算法 |
|------|------|--------|---------|
| `markdown_outline(path)` | `path` | `list[dict]` 嵌套标题树 | MarkdownIt token 解析 → 栈构建树 |
| `iter_outline(outline)` | `outline` | `list[dict]` 扁平标题列表 | 深度优先遍历（递归） |
| `markdown_get_section(path, heading, occurrence=1)` | `path, heading, occurrence` | `dict` 章节内容 | 定位标题行号 → 范围切片 |
| `markdown_list_tasks(path)` | `path` | `list[dict]` 任务列表 | 正则匹配 `[x]` / `[ ]` |

### `markdown_outline` 算法详解

```
输入: Markdown 文件路径
  │
  ▼
第一步: MarkdownIt 解析 token 流
  │
  ▼
提取 heading_open token:
  - level = tag 中的 h1-h6
  - title = 下一个 inline token 的 content
  - line_start = token.map[0] + 1 (1-based)
  - line_end = token.map[1] (1-based)
  - section_start = line_start
  - section_end = len(lines) (默认全文)
  │
  ▼
计算 section_end:
  每个章节在其后第一个同级或更高级标题前结束
  例如:
    ## A (section: 1-10)
      ### A.1 (section: 3-7)
        #### A.1.1 (section: 5-7)
      ## B → 闭合 A 的 section 到 B-1
  │
  ▼
第二步: 栈构建父子树
  遍历 flat_headings，用栈维护层级嵌套关系
  │
  ▼
输出: [{level, title, line_start, line_end, section_start, section_end, children}]
```

### `markdown_list_tasks` 正则表达式

```python
TASK_RE = re.compile(
    r"^(?P<indent>\s*)"          # 缩进空格
    r"(?P<marker>[-*+])"         # 列表标记 (- * +)
    r"\s+\[(?P<state>[ xX])\]"  # 复选框 [ ] [x] [X]
    r"\s+(?P<text>.*)$"          # 任务文本
)
```

### 查询的章节的关系

`markdown_get_section` 的 `occurrence` 参数支持标题重名：

```python
# Test.md 中有两个 "## 背景"
section = markdown_get_section("Test.md", "背景", occurrence=2)  # 取第二个
```

### `iter_outline` 递归展平

```python
def iter_outline(outline):
    headings = []
    for heading in outline:
        headings.append(heading)
        headings.extend(iter_outline(heading["children"]))
    return headings
```

---

## 3.6 `ori_tools/editor.py` — Markdown 编辑器

- **行数**: 183 行
- **依赖**: `parser.py`（获取章节位置信息）

### 工具接口

| 工具 | 参数 | 底层操作 |
|------|------|---------|
| `markdown_replace_section(path, heading, content, occurrence=1)` | 章节标题 + 替换内容 | 行号范围切片替换 |
| `markdown_insert_after_heading(path, heading, content, occurrence=1)` | 插入点标题 + 内容 | 标题行后插入行 |
| `markdown_update_task_status(path, task_index, done)` | 任务索引 + 新状态 | 字符串替换 `[ ]` / `[x]` |

### 核心设计原则

#### 行号操作（非全文正则替换）

所有编辑器都基于解析器提供的**行号信息**进行操作：

```python
# 替换章节：精确的行号范围切片
lines[old_start - 1 : old_end] = replacement

# 插入内容：精确的行号插入点
lines[insert_at:insert_at] = insertion

# 更新任务状态：精确的行号定位
lines[line_index] = old_line.replace("[x]", "[ ]", 1)
```

#### 最小修改原则

每次修改只改动目标范围，文件其他部分完全不动。

#### `markdown_replace_section` 算法

```
1. markdown_get_section → 获取 section_start, section_end
2. _read_lines → 行列表（保留换行符）
3. _content_lines → 确保内容以 \n 结束
4. lines[old_start-1:old_end] = replacement
5. _write_lines → 写回文件
6. 返回 old_range / new_range / line_delta
```

#### `markdown_update_task_status` 算法

```
1. markdown_list_tasks → 获取任务列表（含 line, done, text）
2. 按 task_index 定位目标行 line_index
3. 字符串替换：
   [x] → [ ] (标记为未完成)
   [ ] → [x] (标记为完成)
4. 只替换 checkbox 区域，不涉及其他文本
```

---

## 3.7 `ori_tools/formatter.py` — Markdown 格式化器

- **行数**: 70 行
- **依赖**: `mdformat`, `mdformat-gfm`

### 工具接口

| 工具 | 参数 | 行为 |
|------|------|------|
| `markdown_format_file(path, extensions=["gfm"])` | 文件路径 + 扩展名 | 用 mdformat 原地格式化，返回 changed 状态 |
| `markdown_check_format(path, extensions=["gfm"])` | 文件路径 + 扩展名 | 只检查不写入，返回 formatted 布尔值 |

### 为什么独立成单独的包

`mdformat` 可能重写整篇文档的多方面内容：
- 空白和缩进
- 表格对齐
- 列表间距
- 标题前后空行

这些全局性操作不应和 `parser/editor` 的局部读写逻辑混在一起。

### 技术细节

```python
# 格式化（原地写文件）
mdformat.file(str(markdown_path), extensions=selected_extensions)

# 检查（内存操作，不写文件）
formatted = mdformat.text(text, extensions=selected_extensions)
```

默认使用 `gfm`（GitHub Flavored Markdown）扩展，确保表格和任务列表格式一致。

---

## 3.8 `ori_tools/memory.py` — 用户偏好记忆

- **行数**: 336 行
- **依赖**: 仅标准库（`json`, `pathlib`, `datetime`）

### 存储方式

JSON 文件，路径为 `.agentscope_memory/user_preferences.json`。

### 文件结构

```json
{
  "version": 1,
  "kind": "user_preferences",
  "updated_at": "2026-06-08T12:34:56+00:00",
  "preferences": {
    "language": {
      "key": "language",
      "value": "zh-CN",
      "category": "general",
      "source": "user",
      "created_at": "...",
      "updated_at": "...",
      "hard": false
    }
  }
}
```

### 工具接口

| 工具 | 参数 | 类型 | 说明 |
|------|------|------|------|
| `user_memory_outline(category, include_preview)` | 可选分类 + 预览开关 | 📖 只读 | 偏好概览（默认不加载完整值） |
| `user_memory_save_preference(key, value, category, source, hard)` | 键值 + 元数据 | ✏️ 写操作 | 保存偏好 |
| `user_memory_get_preference(key)` | 键名 | 📖 只读 | 读取单条 |
| `user_memory_list_preferences(category)` | 可选分类 | 📖 只读 | 列出全部 |
| `user_memory_delete_preference(key)` | 键名 | ✏️ 写操作 | 删除单条 |
| `user_memory_clear_preferences(confirm)` | 确认开关 | ✏️ 写操作（危险！） | 清空全部 |
| `hard_user_memories()` | 无参数 | 📖 只读 | 获取 hard 规则 |

### 安全设计

#### 1. 清空防误操作

```python
def user_memory_clear_preferences(confirm=False):
    if not confirm:
        raise ValueError("confirm must be true to clear user preference memory")
```

#### 2. 原子写入

```python
def _save_store(store):
    temp_path = USER_PREFERENCES_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(...))      # 先写临时文件
    temp_path.replace(USER_PREFERENCES_PATH)   # 原子替换（POSIX rename）
```

#### 3. 隐私保护

`outline` 模式默认不返回完整值，只显示 `key`、`category`、时间戳等元数据。

```python
def _memory_outline_entry(memory, include_preview):
    entry = {"key": memory.get("key"), ...}
    if include_preview:
        entry["preview"] = value[:80]  # 仅预览 80 字符
    return entry
```

### 硬性规则记忆（hard flag）

`hard: True` 的记忆表示这是用户明确要求必须记住的规则。`hard_user_memories()` 单独提取这类记忆供 Agent 启动时注入：

```python
def hard_user_memories():
    store = _load_store()
    return [m for m in store["preferences"].values() if m.get('hard')]
```
