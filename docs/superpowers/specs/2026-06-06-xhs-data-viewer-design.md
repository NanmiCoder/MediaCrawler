# 小红书数据查看器（XHS Data Viewer）设计文档

- 日期：2026-06-06
- 状态：已确认设计，待编写实现计划
- 作者：Jake (chuangjieren@gmail.com)
- 关联：本文是 [2026-06-05-xhs-insight-pipeline-design.md](./2026-06-05-xhs-insight-pipeline-design.md) 的下游配套（数据查看器）

## 1. 背景与目标

上一期「XHS Insight Pipeline」已经能定时把小红书笔记与评论爬到 `database/sqlite_tables.db`。当前数据规模：44 条 `xhs_note`、435 条 `xhs_note_comment`、10 条 `insight_runs`。

本期目标：**提供一个可重复启动的本地小工具，让人能快速查看这些已爬到的数据**。

- **使用方式**：每次爬完一批数据后，执行一个命令 → 浏览器里看到笔记列表 + 点进去看评论。
- **范围**：基础查看即可。**不**做搜索、筛选、导出、采集运行面板等。
- **平台约束**：Windows；实现要简单。

## 2. 核心隔离策略

延续上期「不修改任何上游文件」的原则：

- 自研代码全部放入**新增子包 `insight/viewer/`**。
- **不修改** MediaCrawler 既有任何文件，不修改 `insight/` 中既有的 `cli.py` / `runner.py` / `orchestrator.py` / `db.py` / `config.py` / `crawl_entry.py` 等。
- 只读 `database/sqlite_tables.db`，**不写**任何表（`insight_runs` 也只读）。
- 与 `insight/` 同级（`insight/viewer/`），未来可单独升级/替换。

## 3. 方案选型

候选三选一：

| 方案 | 代码量 | 表格展示 | 依赖体积 | 结论 |
|---|---|---|---|---|
| **A. Streamlit** | ~80 行 Python，0 行 HTML | 极好 | 中（~150MB） | **采用** |
| B. Flask + HTML | 1 个 .py + 1 个 .html | 一般 | 小 | 否 |
| C. Gradio | ~100 行 | 弱 | 中 | 否 |

理由：

- 「基础查看 + Windows + 简单实现」三个约束下，Streamlit 匹配度最高。
- 不写一行 HTML/CSS/JS，符合「简单实现」。
- `st.dataframe` 自带列排序、`st.session_state` 选行状态、`st.cache_data` 缓存都内置。
- 依赖通过 `uv run --with streamlit` 临时拉取，**不写进** `pyproject.toml` / `requirements.txt`，避免污染上游依赖。

## 4. 文件结构

```
insight/viewer/
├── __init__.py          # 空，仅作包
├── app.py               # Streamlit 入口（页面布局、session_state）
├── data.py              # 纯函数：load_notes() / load_comments(note_id) / format_ts(ts)
└── README.md            # 启动说明
```

职责切分：

- `data.py`：纯数据层，**不导入** Streamlit，方便单测与未来换 UI。
- `app.py`：仅做页面布局和交互，调 `data.py` 取数据。
- 复用约定：SQLite 路径 = `database/sqlite_tables.db`（与上游 / `insight/db.py` 一致），**不读 `.env`**。

## 5. 界面与交互

单页面三块布局（自上而下）：

```
┌─────────────────────────────────────────────────────────┐
│  小红书数据查看    共 44 条笔记 / 435 条评论  [刷新]    │ ← 顶部
├─────────────────────────────────────────────────────────┤
│  笔记列表（按发布时间 time 倒序）                          │
│  ┌─────┬──────────────┬──────┬─────────┬────────┐      │
│  │  #  │ 标题         │ 点赞 │ 评论数 │ 关键词 │      │
│  ├─────┼──────────────┼──────┼─────────┼────────┤      │
│  │  1 │ 春日穿搭...   │ 1.2k │   38   │ 穿搭  │      │
│  │  2 │ 护肤心得...   │  856 │   12   │ 护肤  │      │
│  │ ... │              │      │         │        │      │
│  └─────┴──────────────┴──────┴─────────┴────────┘      │
├─────────────────────────────────────────────────────────┤
│  ▾ 笔记详情（选中后展开）                                  │
│  作者：xxx  |  发布时间：2024-03-15  |  关键词：穿搭    │
│  正文：今天分享...                                        │
│  ─────────────────────────────────                      │
│  评论（38 条）                                            │
│  ┌────┬──────────┬───────────────────────────────┐    │
│  │ 点赞│ 用户    │ 内容                          │    │
│  └────┴──────────┴───────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

交互细节：

- 笔记列表用 `st.dataframe`，自带列排序。
- 「查看」用按钮 → 写入 `st.session_state["selected_note_id"]`，详情区根据它重新查询。
- 顶部 `[刷新]` 按钮 → `st.cache_data.clear()` 后重读。
- 时间戳统一用 `format_ts` 转 `YYYY-MM-DD HH:MM`。
- 大文本字段（正文/评论）用 `st.markdown` 容器展示，必要时折叠。
- 缓存：`@st.cache_data(ttl=60)`，60 秒自动重读；不点刷新也最多延迟 1 分钟。
- 数据规模小（44 + 435），**不做评论分页**。

## 6. 字段映射

UI 展示字段与数据库字段对应：

| UI 列 | 数据源 |
|---|---|
| 标题 | `xhs_note.title` |
| 点赞 | `xhs_note.liked_count` |
| 评论数 | `xhs_note.comment_count` |
| 发布时间 | `xhs_note.time` → `format_ts` |
| 关键词 | `xhs_note.source_keyword` |
| 正文 | `xhs_note.desc` |
| 评论用户 | `xhs_note_comment.nickname` |
| 评论内容 | `xhs_note_comment.content` |
| 评论时间 | `xhs_note_comment.create_time` → `format_ts` |

## 7. 错误处理

所有错误在 UI 层用 `st.error` 友好展示，不抛 traceback：

| 场景 | 行为 |
|---|---|
| SQLite 文件不存在 | `未找到数据库 database/sqlite_tables.db，请先运行爬虫` |
| `xhs_note` 表不存在 | `数据库缺少表 xhs_note，请先执行 uv run python main.py --init_db sqlite` |
| 笔记表为空 | 表格区显示 `暂无数据` |
| 选中笔记无评论 | 评论区显示 `该笔记暂无评论` |
| 数据库被爬取进程持锁 | `try/except sqlite3.OperationalError` → `数据库正忙，请稍后重试` |
| 单条记录字段为 None | UI 显示 `—`，不崩 |

## 8. 数据流

```
app.py
  └─ st.cache_data(ttl=60)
       └─ data.load_notes()        → list[dict]   (SELECT * FROM xhs_note ORDER BY time DESC)
       └─ data.load_comments(id)   → list[dict]   (SELECT … FROM xhs_note_comment WHERE note_id = ?)
       └─ data.format_ts(int|None) → str          (时间戳→可读字符串)
```

设计决策：

- **不**复用 `database/db_session.py`：那是异步 SQLAlchemy，为爬取设计；本工具只读、低频、同步访问，独立 `sqlite3.connect` 更轻、更稳、更易测。
- 所有 SQL 集中在 `data.py`，`app.py` 不出现 SQL 字符串。
- 工具对数据库**只读不写**。

## 9. 测试

`tests/insight/test_viewer.py`，**仅测 `data.py` 纯函数**，不启 Streamlit：

- `test_load_notes_returns_list`：临时 SQLite 灌 3 条假数据 → 验证返回条数与字段
- `test_load_comments_filters_by_note_id`：灌 2 笔记 + 3 评论 → 验证过滤正确
- `test_load_comments_empty_when_no_match`：不存在的 `note_id` → 返回 `[]`
- `test_format_ts_handles_none_and_zero`：None / 0 / 正常时间戳都正常处理
- `test_missing_table_raises_operational_error`：删表后调函数 → 验证抛 `sqlite3.OperationalError`（让 UI 捕获后展示）

`app.py` 不写 Streamlit 单测（成本/收益不划算），通过 `uv run … insight.viewer.app` 手动烟雾测试一次。

## 10. 启动方式

```bash
# 从项目根目录
uv run --with streamlit python -m insight.viewer.app
# → 自动打开 http://localhost:8501
```

补充：

- 依赖通过 `--with streamlit` 临时拉取，**不修改** `pyproject.toml` / `requirements.txt`。
- `insight/viewer/README.md` 写一份简要说明（含首次跑、刷新操作、停止 Ctrl+C）。

## 11. YAGNI 清单（本期明确不做）

- 全局搜索框（笔记标题 + 正文 + 评论）
- 按关键词/作者下拉筛选
- 数据导出按钮（CSV / Excel / JSON）
- `insight_runs` 采集运行记录面板
- 评论分页
- 多人协作 / 用户登录
- 在查看器中编辑 / 删除数据

## 12. 与上期设计的关系

- 上期 `insight/` 提供「爬数据」能力，本期 `insight/viewer/` 提供「看数据」能力。
- 两者**互不依赖**：viewer 不 import `insight.cli` / `insight.runner` / `insight.orchestrator` / `insight.config`。
- 共用同一个 SQLite 文件与同一个表结构，**这是唯一的耦合点**。
- 上期 Git 同步策略（`upstream` remote + `merge`/`rebase`）继续适用。
