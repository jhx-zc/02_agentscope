# AgentScope Markdown 工具设计

本文整理面向 AgentScope 的 Markdown 操作工具抽象。这里列出的
`markdown_*` 和 `course_*` 名称不是第三方库自带 API，而是建议封装给
AgentScope 调用的工具名。

## 依赖分工

| 依赖 | 主要用途 | 适合承担的能力 |
| --- | --- | --- |
| `markdown-it-py` | Markdown 解析和 HTML 渲染 | 解析 token、提取标题、定位章节、提取代码块、渲染预览 |
| `mdit-py-plugins` | `markdown-it-py` 插件集合 | task list、frontmatter 识别、word count、anchors、admonitions 等 |
| `mdformat` | Markdown 格式化 | 格式化文件、检查格式、统一列表和空行 |
| `mdformat-gfm` | `mdformat` 的 GFM 插件 | 格式化 GFM 表格、task list、strikethrough、autolinks |
| `python-frontmatter` | YAML/TOML frontmatter 读写 | 稳定更新课程元数据，建议额外引入 |

建议安装：

```bash
uv add markdown-it-py mdit-py-plugins mdformat mdformat-gfm python-frontmatter
```

## 基础初始化

```python
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.wordcount import wordcount_plugin

md = (
    MarkdownIt("gfm-like2")
    .use(tasklists_plugin)
    .use(wordcount_plugin)
)

tokens = md.parse(markdown_text)
html = md.render(markdown_text)
```

`markdown-it-py` 的 block token 通常带有 `map` 字段，格式类似
`[start_line, end_line]`。它适合定位标题、章节、代码块等块级结构。
编辑时通常不要尝试”修改 AST 再还原 Markdown”，而是使用 token 的行号范围
对原始文本做切片替换，然后用 `mdformat` 收尾。

## Token 类型参考

`markdown-it-py` 的 `Token.type` 字段标识了 token 代表的 Markdown 结构，
与 `nesting` 字段（`1`=开标签，`0`=自闭合，`-1`=闭标签）配合使用。
以下列出 CommonMark 标准的核心类型（无需额外插件即可生成）。

### 块级元素（Block）

这些 token 直接出现在 `md.parse(text)` 返回的顶层列表中，
且 `token.block == True`。每个块级 token 通常带有 `token.map`（`[start_line, end_line]`），
可用于定位源码行号。

| type | nesting | tag | 含义 |
|------|---------|-----|------|
| `heading_open` | 1 | `h1`~`h6` | 标题开始，如 `# 标题` |
| `heading_close` | -1 | `h1`~`h6` | 标题结束 |
| `paragraph_open` | 1 | `p` | 段落开始 |
| `paragraph_close` | -1 | `p` | 段落结束 |
| `inline` | 0 | `””` | 内联内容容器，实际内容存放在 `children` 字段中 |
| `code_block` | 0 | `code` | 缩进代码块（4 个空格或 1 个 tab） |
| `fence` | 0 | `code` | 围栏代码块（`` ``` `` 或 `~~~`），语言在 `token.info` |
| `hr` | 0 | `hr` | 水平分隔线 `---` / `***` / `___` |
| `html_block` | 0 | `””` | HTML 块级标签（如 `<div>`） |
| `blockquote_open` | 1 | `blockquote` | 引用块开始 `>` |
| `blockquote_close` | -1 | `blockquote` | 引用块结束 |
| `bullet_list_open` | 1 | `ul` | 无序列表开始 `-` / `*` / `+` |
| `bullet_list_close` | -1 | `ul` | 无序列表结束 |
| `ordered_list_open` | 1 | `ol` | 有序列表开始 `1.` |
| `ordered_list_close` | -1 | `ol` | 有序列表结束 |
| `list_item_open` | 1 | `li` | 列表项开始 |
| `list_item_close` | -1 | `li` | 列表项结束 |
| `table_open` | 1 | `table` | 表格开始 |
| `table_close` | -1 | `table` | 表格结束 |
| `thead_open` | 1 | `thead` | 表头开始 |
| `thead_close` | -1 | `thead` | 表头结束 |
| `tbody_open` | 1 | `tbody` | 表体开始 |
| `tbody_close` | -1 | `tbody` | 表体结束 |
| `tr_open` | 1 | `tr` | 表格行开始 |
| `tr_close` | -1 | `tr` | 表格行结束 |
| `th_open` | 1 | `th` | 表头单元格开始 |
| `th_close` | -1 | `th` | 表头单元格结束 |
| `td_open` | 1 | `td` | 表体单元格开始 |
| `td_close` | -1 | `td` | 表体单元格结束 |

### 内联元素（Inline）

这些 token 不会直接出现在顶层列表中，而是作为 `inline` token 的 `children`
出现（`token.children`）。它们描述段落内的格式化元素。

| type | nesting | tag | 含义 |
|------|---------|-----|------|
| `em_open` | 1 | `em` | 斜体开始 `*text*` / `_text_` |
| `em_close` | -1 | `em` | 斜体结束 |
| `strong_open` | 1 | `strong` | 粗体开始 `**text**` / `__text__` |
| `strong_close` | -1 | `strong` | 粗体结束 |
| `s_open` | 1 | `s` | 删除线开始 `~~text~~`（仅 GFM 模式） |
| `s_close` | -1 | `s` | 删除线结束（仅 GFM 模式） |
| `link_open` | 1 | `a` | 链接开始 `[text](url)` |
| `link_close` | -1 | `a` | 链接结束 |
| `image` | 0 | `img` | 图片 `![alt](url)`，自闭合 |
| `text` | 0 | `””` | 普通文本 |
| `text_special` | 0 | `””` | 特殊字符（HTML 实体 `&amp;`、转义符 `\*`） |
| `code_inline` | 0 | `code` | 行内代码 `` `code` `` |
| `html_inline` | 0 | `””` | 行内 HTML（如 `<br>`） |
| `hardbreak` | 0 | `br` | 硬换行（行末两个空格 + 换行） |
| `softbreak` | 0 | `br` | 软换行（普通换行符） |

### 嵌套结构示例

解析 `# Hello **world**` 得到的 token 结构：

```
heading_open  (type=”heading_open”, tag=”h1”, nesting=1)       ← 标题开始
└── inline    (type=”inline”, tag=””, nesting=0)                ← 内联容器（children 中放具体内容）
    ├── text          (type=”text”,          content=”Hello “)  ← 普通文本
    ├── strong_open   (type=”strong_open”,   tag=”strong”)      ← 粗体开始
    │   └── text      (type=”text”,          content=”world”)   ← 粗体中的文本
    └── strong_close  (type=”strong_close”,  tag=”strong”)      ← 粗体结束
heading_close (type=”heading_close”, tag=”h1”, nesting=-1)      ← 标题结束
```

注意 `inline` token 自身 `nesting=0`，它的子内容通过 `token.children` 列表访问，
而不是作为兄弟 token。这在遍历顶层 token 列表时很容易忽略内联内容。

## 基础工具

### `markdown_outline`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` |
| 用法 | `MarkdownIt("gfm-like2").parse(text)`，扫描 `heading_open -> inline -> heading_close` |
| 输入 | `path: str` |
| 输出 | 标题树，包括 `level`、`title`、`line_start`、`line_end`、`section_start`、`section_end` |
| 说明 | 用于后续所有“按章节操作”的基础索引 |

实现要点：

1. 读取 Markdown 文本并解析 token。
2. 找到 `heading_open` token，读取 `tag` 得到 `h1` 到 `h6`。
3. 下一个 `inline` token 的 `content` 通常是标题文本。
4. 根据下一个同级或更高级标题推断当前章节范围。

### `markdown_get_section`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + 自定义行范围逻辑 |
| 用法 | 先调用 `markdown_outline`，找到目标标题，再截取原文行 |
| 输入 | `path: str`、`heading: str`、`occurrence: int = 1` |
| 输出 | 章节标题、章节行号范围、章节原文 |
| 说明 | 适合让 agent 读取某一讲、某个小节或练习部分 |

实现要点：

1. 使用标题文本和出现次数定位目标标题。
2. `section_start` 通常是标题所在行。
3. `section_end` 是下一个同级或更高级标题前一行。
4. 返回原始 Markdown，而不是渲染后的 HTML。

### `markdown_replace_section`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + 文本切片 |
| 用法 | 定位章节范围后替换 `lines[start:end]` |
| 输入 | `path: str`、`heading: str`、`content: str`、`occurrence: int = 1` |
| 输出 | 修改结果、旧范围、新范围 |
| 说明 | 编辑能力来自你自己的文本替换，不是库的 AST 写回 |

实现要点：

1. 通过 `markdown_get_section` 找到章节范围。
2. 保留标题行或允许调用者传入完整章节内容，需要明确约定。
3. 写回文件前建议保留备份或返回 diff。
4. 写回后可调用 `markdown_format_file`。

### `markdown_insert_after_heading`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + 文本插入 |
| 用法 | 找到标题 token 的结束行，在其后插入内容 |
| 输入 | `path: str`、`heading: str`、`content: str`、`occurrence: int = 1` |
| 输出 | 插入位置、插入后的文件路径 |
| 说明 | 适合插入学习目标、练习题、提示块、参考资料 |

实现要点：

1. 定位目标标题。
2. 默认插在标题行之后。
3. 如果标题后已有空行，需要处理空行规范。
4. 插入后调用 `mdformat` 可以统一格式。

### `markdown_list_code_blocks`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` |
| 用法 | 扫描 `token.type == "fence"` 或 `token.type == "code_block"` |
| 输入 | `path: str`、`language: str | None = None` |
| 输出 | 代码块列表，包括序号、语言、内容、行号范围、所属章节 |
| 说明 | 适合课程中提取示例代码、检查语言标注、批量验证代码块 |

实现要点：

1. fenced code block 的语言通常在 `token.info`。
2. 代码内容在 `token.content`。
3. 行号范围来自 `token.map`。
4. 可结合 `markdown_outline` 计算代码块所属章节。

### `markdown_update_code_block`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + 文本切片 |
| 用法 | 先调用 `markdown_list_code_blocks`，再按定位结果替换原文行 |
| 输入 | `path: str`、`block_index: int`、`content: str`、`language: str | None = None` |
| 输出 | 修改结果、替换的代码块信息 |
| 说明 | 推荐用“章节 + 第几个代码块”定位，避免误改 |

实现要点：

1. 用代码块序号、语言和所属章节缩小定位范围。
2. 替换时保留 fenced code block 标记，通常只替换 fence 内部内容。
3. 可选择同步更新语言标注。

### `markdown_list_tasks`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdit-py-plugins.tasklists` + 文本行扫描 |
| 用法 | 启用 `tasklists_plugin`，同时扫描原文中的 `- [ ]` 和 `- [x]` |
| 输入 | `path: str` |
| 输出 | 任务列表，包括完成状态、任务文本、行号、所属章节 |
| 说明 | 插件负责识别和渲染 task list，稳定更新仍建议按原始行修改 |

实现要点：

1. 用插件确认 task list 语法支持。
2. 用正则定位原始行更适合写回。
3. 推荐只支持标准形式：`- [ ] task`、`- [x] task`、`- [X] task`。

### `markdown_update_task`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdit-py-plugins.tasklists` + 文本行替换 |
| 用法 | 找到任务行，把 `[ ]` 和 `[x]` 切换 |
| 输入 | `path: str`、`task_index: int`、`done: bool` |
| 输出 | 修改结果、任务旧状态、新状态 |
| 说明 | 该工具应限制只改 checkbox，不改任务文本 |

实现要点：

1. 先调用 `markdown_list_tasks` 获取任务行号。
2. 只替换 checkbox 标记。
3. 保留缩进、列表符号和任务文本。

### `markdown_word_count`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdit-py-plugins.wordcount` |
| 用法 | 启用 `wordcount_plugin` 后渲染文本，并从 `env` 读取统计结果 |
| 输入 | `path: str` |
| 输出 | 字数、预计阅读时间等 |
| 说明 | 适合课程讲义长度控制和学习时长估算 |

示例：

```python
from markdown_it import MarkdownIt
from mdit_py_plugins.wordcount import wordcount_plugin

env = {}
md = MarkdownIt().use(wordcount_plugin)
md.render(markdown_text, env)
wordcount = env.get("wordcount")
```

### `markdown_format_file`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdformat` + `mdformat-gfm` |
| 用法 | `mdformat.file(path, extensions={"gfm"})` 或 CLI `mdformat path` |
| 输入 | `path: str`、`extensions: list[str] = ["gfm"]` |
| 输出 | 格式化后的文件 |
| 说明 | GFM 表格和 task list 格式化需要安装并启用 `mdformat-gfm` |

注意：

1. `mdformat` 是 opinionated formatter，会改变空行、列表、表格等风格。
2. 建议固定版本，避免课程文档格式随依赖升级变化。

### `markdown_check_format`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdformat` |
| 用法 | CLI `mdformat --check path` 最直接 |
| 输入 | `path: str` |
| 输出 | 是否符合格式、失败文件列表 |
| 说明 | 不修改文件，只做检查 |

实现方式：

```bash
uv run mdformat --check docs
```

### `markdown_render_html`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + `mdit-py-plugins` |
| 用法 | `MarkdownIt("gfm-like2").render(text)` |
| 输入 | `path: str`、`plugins: list[str] = []` |
| 输出 | HTML 字符串 |
| 说明 | 适合课程预览、渲染测试、检查 Markdown 是否能正常渲染 |

## 课程增强工具

### `course_lesson_summary`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown_outline` + AgentScope LLM |
| 用法 | 先提取标题、学习目标、代码块、练习题，再交给模型总结 |
| 输入 | `path: str` |
| 输出 | 课程摘要、知识点、练习点、预计学习时长 |
| 说明 | 这不是 Markdown 库能力，而是 Agent 能力 |

### `course_validate_lesson_structure`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` |
| 用法 | 基于标题树和 token 检查课程结构 |
| 输入 | `path: str`、`schema: dict | None = None` |
| 输出 | 校验结果、错误列表、建议修复项 |
| 说明 | 适合做确定性校验 |

可检查项：

- 是否只有一个 H1。
- 是否存在标题跳级，例如 H2 后直接 H4。
- 是否包含必备章节，如学习目标、核心概念、实践练习、总结。
- 是否存在空章节。
- 代码块是否标注语言。
- task list 是否符合标准格式。

### `course_insert_exercise`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown_insert_after_heading` + `mdformat` |
| 用法 | 找到练习章节，没有则创建，再插入练习模板 |
| 输入 | `path: str`、`exercise: dict`、`heading: str = "练习"` |
| 输出 | 插入结果、插入位置 |
| 说明 | 适合课程自动补充作业、课堂练习、思考题 |

### `course_update_learning_objectives`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown_get_section` + `markdown_replace_section` |
| 用法 | 定位“学习目标”章节，替换为标准列表 |
| 输入 | `path: str`、`objectives: list[str]` |
| 输出 | 更新结果 |
| 说明 | 可强制格式为 Markdown 无序列表 |

### `course_update_frontmatter`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | 建议使用 `python-frontmatter`；`mdit-py-plugins.front_matter` 只适合识别 |
| 用法 | 读取 frontmatter，合并 patch，再写回 |
| 输入 | `path: str`、`patch: dict` |
| 输出 | 更新后的元数据 |
| 说明 | 严格只用前三个库时不建议做成写工具 |

建议实现：

```python
import frontmatter

post = frontmatter.load(path)
post.metadata.update(patch)
frontmatter.dump(post, path)
```

### `course_check_internal_links`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown-it-py` + 文件系统 |
| 用法 | 提取链接，检查相对路径和 anchor 是否存在 |
| 输入 | `root: str`、`path: str | None = None` |
| 输出 | 死链列表、缺失 anchor、重复 anchor |
| 说明 | 可结合 `mdit-py-plugins.anchors` 的 slug 逻辑 |

实现要点：

1. 提取 inline link 和 image link。
2. 忽略外部 URL，或单独做 URL 检查。
3. 对 `./lesson.md#some-heading` 检查文件存在和 heading anchor 存在。
4. 用 `markdown_outline` 生成目标文件 heading 列表。

### `course_generate_toc`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `markdown_outline` + 自定义 anchor 生成 |
| 用法 | 从标题树生成目录，再插入或替换 `## 目录` 章节 |
| 输入 | `path: str`、`max_depth: int = 3` |
| 输出 | 生成的 TOC、更新结果 |
| 说明 | 适合课程讲义自动维护目录 |

实现要点：

1. 从 `markdown_outline` 获取标题树。
2. 跳过 `目录` 自身。
3. 生成 GitHub 风格 anchor 或与课程渲染器一致的 anchor。
4. 使用 `markdown_replace_section` 或 `markdown_insert_after_heading` 写回。

### `course_format_all_markdown`

| 项目 | 内容 |
| --- | --- |
| 主要来自 | `mdformat` + `mdformat-gfm` |
| 用法 | 遍历课程目录下 `.md` 文件，逐个格式化 |
| 输入 | `root: str`、`include: list[str] = ["**/*.md"]`、`exclude: list[str] = []` |
| 输出 | 格式化文件列表 |
| 说明 | 建议固定 `mdformat` 版本，避免格式风格变化 |

实现方式：

```bash
uv run mdformat .
```

或在 Python 中遍历文件后调用 `mdformat.file(...)`。

## 推荐分层

```text
Parser tools:
  markdown_outline
  markdown_get_section
  markdown_list_code_blocks
  markdown_list_tasks
  markdown_word_count
  markdown_render_html

Editor tools:
  markdown_replace_section
  markdown_insert_after_heading
  markdown_update_code_block
  markdown_update_task

Formatter tools:
  markdown_format_file
  markdown_check_format

Course tools:
  course_lesson_summary
  course_validate_lesson_structure
  course_insert_exercise
  course_update_learning_objectives
  course_check_internal_links
  course_generate_toc
  course_format_all_markdown

Needs extra dependency:
  course_update_frontmatter
```

## 参考资料

- `markdown-it-py` 使用文档: <https://markdown-it-py.readthedocs.io/en/latest/using.html>
- `mdit-py-plugins` 插件文档: <https://mdit-py-plugins.readthedocs.io/en/latest/>
- `mdformat` 使用文档: <https://mdformat.readthedocs.io/en/stable/users/installation_and_usage.html>
- `mdformat` 插件文档: <https://mdformat.readthedocs.io/en/stable/users/plugins.html>
