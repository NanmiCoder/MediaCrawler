# XHS Data Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `insight/viewer/` 下交付一个 Streamlit 本地小工具，可重复启动，用于查看 `database/sqlite_tables.db` 中的小红书笔记与评论。

**Architecture:** `insight/viewer/` 是一个新增子包，与 `insight/` 既有的爬取代码**互不依赖**。`data.py` 纯数据层（直接 `sqlite3`，不依赖 Streamlit，可单测）；`app.py` 仅做页面布局；`tests/insight/test_viewer_data.py` 仅覆盖 `data.py` 的纯函数。

**Tech Stack:** Python 3.11+、Streamlit（通过 `uv run --with streamlit` 临时拉取，**不**写入 `pyproject.toml`）、SQLite3（标准库）、pytest（已在上游 dev deps 中）。

**Spec:** [`docs/superpowers/specs/2026-06-06-xhs-data-viewer-design.md`](../specs/2026-06-06-xhs-data-viewer-design.md)

---

## File Structure

| 路径 | 状态 | 职责 |
|---|---|---|
| `insight/viewer/__init__.py` | Create | 空，仅作 Python 包 |
| `insight/viewer/data.py` | Create | 纯数据层：`load_notes()` / `load_comments(note_id)` / `format_ts(ts)` |
| `insight/viewer/app.py` | Create | Streamlit 入口：页面布局 + `st.session_state` |
| `insight/viewer/README.md` | Create | 启动与使用说明 |
| `tests/insight/test_viewer_data.py` | Create | 覆盖 `data.py` 的纯函数单测 |

**不修改任何上游文件**，包括 `pyproject.toml` / `requirements.txt` / `insight/` 现有任何文件。

---

## Task 1: 建立包骨架

**Files:**
- Create: `insight/viewer/__init__.py`
- Create: `insight/viewer/data.py`（含函数 stub，raise NotImplementedError）
- Create: `tests/insight/test_viewer_data.py`（含一个 import 烟雾测试）

- [ ] **Step 1: 创建 `insight/viewer/__init__.py`**

```python
# -*- coding: utf-8 -*-
# 小红书数据查看器子包（基于 Streamlit）
# 仅依赖标准库 + streamlit（运行时由 uv --with 临时拉取）
```

- [ ] **Step 2: 创建 `insight/viewer/data.py`（仅 stub）**

```python
# -*- coding: utf-8 -*-
"""纯数据层：从 database/sqlite_tables.db 读取小红书笔记与评论。

不导入 Streamlit，方便单测。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

# 与上游约定一致：数据库固定路径（不读 .env）
DB_PATH = Path(__file__).resolve().parents[2] / "database" / "sqlite_tables.db"


def format_ts(ts: int | None) -> str:
    """将 Unix 时间戳（秒）格式化为 'YYYY-MM-DD HH:MM'。None/0 返回 '—'。"""
    raise NotImplementedError


def load_notes() -> list[dict[str, Any]]:
    """加载所有笔记，按发布时间 time 倒序。"""
    raise NotImplementedError


def load_comments(note_id: str) -> list[dict[str, Any]]:
    """加载指定笔记的评论，按 create_time 升序。"""
    raise NotImplementedError
```

- [ ] **Step 3: 创建 `tests/insight/test_viewer_data.py`（含烟雾测试）**

```python
# -*- coding: utf-8 -*-
"""insight.viewer.data 纯函数单元测试。

仅测 data.py；app.py 不做单测（Streamlit 启动成本/收益不划算）。
"""
import pytest

from insight.viewer.data import format_ts, load_comments, load_notes


def test_imports_smoke():
    """烟雾测试：所有公开函数可导入。"""
    assert callable(format_ts)
    assert callable(load_notes)
    assert callable(load_comments)
```

- [ ] **Step 4: 运行烟雾测试**

Run: `uv run pytest tests/insight/test_viewer_data.py -v`
Expected: PASS（1 passed）

- [ ] **Step 5: 提交**

```bash
git add insight/viewer/__init__.py insight/viewer/data.py tests/insight/test_viewer_data.py
git commit -m "feat(viewer): 包骨架与 data.py stub（含烟雾测试）"
```

---

## Task 2: `data.format_ts`（TDD）

**Files:**
- Modify: `insight/viewer/data.py`
- Modify: `tests/insight/test_viewer_data.py`

- [ ] **Step 1: 追加 `test_format_ts` 失败用例**

在 `tests/insight/test_viewer_data.py` 末尾添加：

```python
def test_format_ts_normal_timestamp():
    """正常时间戳格式化。"""
    # 2024-03-15 12:34:00 UTC+8 = 1710474840
    assert format_ts(1710474840) == "2024-03-15 12:34"


def test_format_ts_none_returns_dash():
    """None 返回 '—'。"""
    assert format_ts(None) == "—"


def test_format_ts_zero_returns_dash():
    """0（未设置）返回 '—'。"""
    assert format_ts(0) == "—"
```

- [ ] **Step 2: 跑测试，验证失败**

Run: `uv run pytest tests/insight/test_viewer_data.py::test_format_ts_normal_timestamp -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: 实现 `format_ts`**

替换 `insight/viewer/data.py` 中的 `format_ts` 函数体：

```python
def format_ts(ts: int | None) -> str:
    """将 Unix 时间戳（秒）格式化为 'YYYY-MM-DD HH:MM'。None/0 返回 '—'。"""
    if not ts:
        return "—"
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
```

- [ ] **Step 4: 跑测试，验证通过**

Run: `uv run pytest tests/insight/test_viewer_data.py -v`
Expected: PASS（4 passed：含 Task 1 的烟雾测试 + 3 个新测试）

- [ ] **Step 5: 提交**

```bash
git add insight/viewer/data.py tests/insight/test_viewer_data.py
git commit -m "feat(viewer): format_ts 时间戳格式化（含 None/0 兜底）"
```

---

## Task 3: `data.load_notes`（TDD）

**Files:**
- Modify: `insight/viewer/data.py`
- Modify: `tests/insight/test_viewer_data.py`

> **设计说明**：`load_notes()` 接收一个 `db_path: Path | None = None` 参数；为 None 时使用 `DB_PATH`。这样测试可以注入临时数据库，生产代码走默认路径。

- [ ] **Step 1: 调整 `data.py` 让 `load_notes` 接受 `db_path` 参数，并把 stub 改成待实现**

修改 `insight/viewer/data.py` 的 `load_notes` 签名（函数体暂时保留 raise）：

```python
def load_notes(db_path: Path | None = None) -> list[dict[str, Any]]:
    """加载所有笔记，按发布时间 time 倒序。db_path=None 时使用 DB_PATH。"""
    raise NotImplementedError
```

- [ ] **Step 2: 追加失败用例（用临时 SQLite 灌假数据）**

在 `tests/insight/test_viewer_data.py` 末尾添加：

```python
def _make_xhs_db(path) -> None:
    """构造一个最小的 xhs_note 测试库。"""
    import sqlite3
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE xhs_note (
            note_id VARCHAR(255) PRIMARY KEY,
            title TEXT,
            liked_count TEXT,
            comment_count TEXT,
            time BIGINT,
            source_keyword TEXT,
            nickname TEXT,
            desc TEXT
        )
        """
    )
    cur.executemany(
        "INSERT INTO xhs_note VALUES (?,?,?,?,?,?,?,?)",
        [
            ("n1", "春日穿搭", "1200", "38", 1710474840, "穿搭", "博主A", "正文1"),
            ("n2", "护肤心得", "856",  "12", 1710388440, "护肤", "博主B", "正文2"),
            ("n3", "无时间戳笔记", "0", "0", 0, "", "博主C", ""),
        ],
    )
    conn.commit()
    conn.close()


def test_load_notes_returns_sorted_by_time_desc(tmp_path):
    """load_notes 按 time 倒序，time=0 的排最后。"""
    from insight.viewer.data import load_notes
    db = tmp_path / "t.db"
    _make_xhs_db(db)

    notes = load_notes(db_path=db)

    assert len(notes) == 3
    # 倒序：n1 (1710474840) > n2 (1710388440) > n3 (0)
    assert [n["note_id"] for n in notes] == ["n1", "n2", "n3"]
    assert notes[0]["title"] == "春日穿搭"
    assert notes[0]["source_keyword"] == "穿搭"


def test_load_notes_missing_table_raises():
    """xhs_note 表不存在时抛 OperationalError（让 UI 捕获后展示）。"""
    import sqlite3
    from insight.viewer.data import load_notes
    db_path = "/tmp/__no_such_xhs_db__.db"  # 实际不存在
    # 用一个临时空库（无表）替代
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        with pytest.raises(sqlite3.OperationalError):
            load_notes(db_path=type(DB_PATH_DEFAULT)())  # placeholder, fix below
    finally:
        os.unlink(path)
```

> **修订**：上面 `test_load_notes_missing_table_raises` 用了一个未定义的 `DB_PATH_DEFAULT`，需要替换为更简单的写法。重写为：

```python
def test_load_notes_missing_table_raises(tmp_path):
    """xhs_note 表不存在时抛 OperationalError（让 UI 捕获后展示）。"""
    import sqlite3
    from insight.viewer.data import load_notes
    db = tmp_path / "empty.db"
    # 不建表
    with pytest.raises(sqlite3.OperationalError):
        load_notes(db_path=db)
```

- [ ] **Step 3: 跑失败用例**

Run: `uv run pytest tests/insight/test_viewer_data.py::test_load_notes_returns_sorted_by_time_desc -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 4: 实现 `load_notes`**

替换 `insight/viewer/data.py` 中的 `load_notes` 函数体：

```python
def load_notes(db_path: Path | None = None) -> list[dict[str, Any]]:
    """加载所有笔记，按发布时间 time 倒序。db_path=None 时使用 DB_PATH。"""
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT note_id, title, liked_count, comment_count, time, "
            "source_keyword, nickname, desc "
            "FROM xhs_note ORDER BY time DESC"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
```

- [ ] **Step 5: 跑测试，验证通过**

Run: `uv run pytest tests/insight/test_viewer_data.py -v`
Expected: PASS（6 passed：1 烟雾 + 3 format_ts + 2 load_notes）

- [ ] **Step 6: 提交**

```bash
git add insight/viewer/data.py tests/insight/test_viewer_data.py
git commit -m "feat(viewer): load_notes 按发布时间倒序读取 xhs_note"
```

---

## Task 4: `data.load_comments`（TDD）

**Files:**
- Modify: `insight/viewer/data.py`
- Modify: `tests/insight/test_viewer_data.py`

- [ ] **Step 1: 追加失败用例**

在 `tests/insight/test_viewer_data.py` 末尾添加：

```python
def _make_xhs_db_with_comments(path) -> None:
    """构造包含 xhs_note + xhs_note_comment 的测试库。"""
    import sqlite3
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE xhs_note (
            note_id VARCHAR(255) PRIMARY KEY,
            title TEXT, liked_count TEXT, comment_count TEXT,
            time BIGINT, source_keyword TEXT, nickname TEXT, desc TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE xhs_note_comment (
            comment_id VARCHAR(255) PRIMARY KEY,
            note_id VARCHAR(255),
            nickname TEXT,
            content TEXT,
            like_count TEXT,
            create_time BIGINT
        )
        """
    )
    cur.executemany("INSERT INTO xhs_note VALUES (?,?,?,?,?,?,?,?)",
                    [("n1","A","0","0",0,"","",""), ("n2","B","0","0",0,"","","")])
    cur.executemany(
        "INSERT INTO xhs_note_comment VALUES (?,?,?,?,?,?)",
        [
            ("c1", "n1", "用户1", "第一条", "10", 1710475000),
            ("c2", "n1", "用户2", "第二条", "5",  1710476000),
            ("c3", "n2", "用户3", "另一条笔记的评论", "0", 1710477000),
        ],
    )
    conn.commit()
    conn.close()


def test_load_comments_filters_by_note_id(tmp_path):
    """load_comments 仅返回指定 note_id 的评论。"""
    from insight.viewer.data import load_comments
    db = tmp_path / "t.db"
    _make_xhs_db_with_comments(db)

    rows = load_comments("n1", db_path=db)

    assert len(rows) == 2
    assert {r["comment_id"] for r in rows} == {"c1", "c2"}
    # 默认按 create_time 升序
    assert [r["comment_id"] for r in rows] == ["c1", "c2"]


def test_load_comments_empty_when_no_match(tmp_path):
    """不存在的 note_id 返回空列表，不抛异常。"""
    from insight.viewer.data import load_comments
    db = tmp_path / "t.db"
    _make_xhs_db_with_comments(db)

    rows = load_comments("nonexistent", db_path=db)

    assert rows == []
```

- [ ] **Step 2: 跑失败用例**

Run: `uv run pytest tests/insight/test_viewer_data.py::test_load_comments_filters_by_note_id -v`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: 实现 `load_comments`**

替换 `insight/viewer/data.py` 中的 `load_comments` 函数体：

```python
def load_comments(note_id: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """加载指定笔记的评论，按 create_time 升序。db_path=None 时使用 DB_PATH。"""
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT comment_id, note_id, nickname, content, like_count, create_time "
            "FROM xhs_note_comment WHERE note_id = ? ORDER BY create_time ASC",
            (note_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
```

- [ ] **Step 4: 跑全部测试，验证通过**

Run: `uv run pytest tests/insight/test_viewer_data.py -v`
Expected: PASS（8 passed：1 烟雾 + 3 format_ts + 2 load_notes + 2 load_comments）

- [ ] **Step 5: 提交**

```bash
git add insight/viewer/data.py tests/insight/test_viewer_data.py
git commit -m "feat(viewer): load_comments 按 note_id 过滤 + create_time 升序"
```

---

## Task 5: `app.py` Streamlit UI

**Files:**
- Create: `insight/viewer/app.py`

> **设计说明**：本 Task **不写单测**（Streamlit 启动成本/收益不划算），通过 Task 7 的端到端手动烟雾测试验证。

- [ ] **Step 1: 创建 `insight/viewer/app.py`**

```python
# -*- coding: utf-8 -*-
"""小红书数据查看器：Streamlit 单页 UI。

页面布局（自上而下）：
  1. 顶部统计 + 刷新按钮
  2. 笔记列表（st.dataframe，自带列排序）
  3. 选中笔记的详情面板 + 评论列表

启动：
  uv run --with streamlit streamlit run insight/viewer/app.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from insight.viewer.data import (
    DB_PATH,
    format_ts,
    load_comments,
    load_notes,
)


# ---------- 启动配置 ----------
st.set_page_config(page_title="小红书数据查看", layout="wide")


# ---------- 数据加载（带缓存）----------
@st.cache_data(ttl=60)
def _cached_notes() -> list[dict]:
    return load_notes()


@st.cache_data(ttl=60)
def _cached_comments(note_id: str) -> list[dict]:
    return load_comments(note_id)


def _load_notes_safely() -> list[dict] | None:
    """加载笔记，错误以 None 返回并用 st.error 提示。"""
    if not DB_PATH.exists():
        st.error(
            f"未找到数据库 {DB_PATH}，请先运行爬虫。"
        )
        return None
    try:
        return _cached_notes()
    except sqlite3.OperationalError:
        st.error("数据库正忙（爬取进程可能正在写入），请稍后重试。")
        return None


def _load_comments_safely(note_id: str) -> list[dict] | None:
    try:
        return _cached_comments(note_id)
    except sqlite3.OperationalError:
        st.error("数据库正忙，请稍后重试。")
        return None


# ---------- 顶部 ----------
st.title("小红书数据查看")

notes = _load_notes_safely()
if notes is None:
    st.stop()

col_stat, col_btn = st.columns([4, 1])
with col_stat:
    total_comments = sum(int(n.get("comment_count") or 0) for n in notes)
    st.caption(f"共 {len(notes)} 条笔记 / {total_comments} 条评论（按 comment_count 估算）")
with col_btn:
    if st.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ---------- 笔记列表 ----------
if not notes:
    st.info("暂无数据")
    st.stop()

# 准备表格数据：加一列"发布时间"已格式化
import pandas as pd

df = pd.DataFrame(
    [
        {
            "#": idx + 1,
            "标题": n.get("title") or "—",
            "点赞": n.get("liked_count") or "—",
            "评论数": n.get("comment_count") or "—",
            "关键词": n.get("source_keyword") or "—",
            "发布时间": format_ts(n.get("time")),
            "note_id": n["note_id"],
        }
        for idx, n in enumerate(notes)
    ]
)

st.subheader("笔记列表")
st.caption("点击下方'查看'按钮查看评论")
event = st.dataframe(
    df[["#", "标题", "点赞", "评论数", "关键词", "发布时间"]],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="notes_table",
)

# Streamlit 1.32+：用户点击某行后 event.selected_rows 包含行号
selected_rows = event.selected_rows if hasattr(event, "selected_rows") else {}
selected_idx = selected_rows["rows"][0] if selected_rows and selected_rows.get("rows") else None


# ---------- 详情面板 ----------
if selected_idx is None:
    st.info("👆 在表格中选中一行后查看笔记详情与评论")
    st.stop()

selected_note = notes[selected_idx]

st.divider()
st.subheader(f"📝 笔记详情：{selected_note.get('title') or '—'}")
detail_cols = st.columns(3)
with detail_cols[0]:
    st.caption(f"**作者**：{selected_note.get('nickname') or '—'}")
with detail_cols[1]:
    st.caption(f"**发布时间**：{format_ts(selected_note.get('time'))}")
with detail_cols[2]:
    st.caption(f"**关键词**：{selected_note.get('source_keyword') or '—'}")

st.markdown("**正文**")
st.markdown(selected_note.get("desc") or "—")

# ---------- 评论 ----------
st.divider()
st.subheader("💬 评论")
comments = _load_comments_safely(selected_note["note_id"])
if comments is None:
    st.stop()
if not comments:
    st.info("该笔记暂无评论")
    st.stop()

# 准备评论表格
cdf = pd.DataFrame(
    [
        {
            "点赞": c.get("like_count") or "—",
            "用户": c.get("nickname") or "—",
            "内容": c.get("content") or "—",
            "时间": format_ts(c.get("create_time")),
        }
        for c in comments
    ]
)
st.dataframe(cdf, use_container_width=True, hide_index=True)
st.caption(f"共 {len(comments)} 条评论")
```

- [ ] **Step 2: 静态语法检查（不启动 Streamlit）**

Run: `uv run python -c "import ast; ast.parse(open('insight/viewer/app.py', encoding='utf-8').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add insight/viewer/app.py
git commit -m "feat(viewer): app.py Streamlit 单页 UI（笔记列表+详情+评论）"
```

---

## Task 6: `README.md` 启动说明

**Files:**
- Create: `insight/viewer/README.md`

- [ ] **Step 1: 创建 README**

```markdown
# 小红书数据查看器（XHS Data Viewer）

基于 Streamlit 的本地查看工具，复用上游 `database/sqlite_tables.db`。
仅做基础查看：笔记列表 + 点进去看评论。不修改任何上游文件。

## 一次性准备

```bash
# 确保上游 SQLite 表结构已创建
uv run python main.py --init_db sqlite
```

## 启动

从项目根目录执行：

```bash
uv run --with streamlit streamlit run insight/viewer/app.py
```

- 自动打开浏览器 `http://localhost:8501`
- 数据通过 `database/sqlite_tables.db` 实时读取，**不修改任何数据**
- 默认 60 秒缓存；点页面右上 🔄 立即重读
- Ctrl+C 停止

## 界面

```
顶部：  共 N 条笔记 / M 条评论         [🔄 刷新]
中段：  笔记列表（按发布时间倒序，可点击选中）
底段：  选中笔记的详情（作者/时间/关键词/正文）+ 评论列表
```

## 错误提示

| 情况 | 提示 |
|---|---|
| 数据库文件不存在 | 未找到数据库 ...，请先运行爬虫 |
| 数据库被爬取进程持锁 | 数据库正忙，请稍后重试 |
| `xhs_note` 表不存在 | 数据库缺少表 xhs_note，请先执行 `uv run python main.py --init_db sqlite` |
| 笔记表为空 | 暂无数据 |
| 选中笔记无评论 | 该笔记暂无评论 |

## 依赖

- Python 3.11+
- Streamlit（通过 `uv run --with streamlit` 临时拉取，**不**写入 `pyproject.toml` / `requirements.txt`）

## 相关

- 设计文档：[`docs/superpowers/specs/2026-06-06-xhs-data-viewer-design.md`](../../specs/2026-06-06-xhs-data-viewer-design.md)
- 数据来源：[`insight/` 爬取包](../../README.md)
```

- [ ] **Step 2: 提交**

```bash
git add insight/viewer/README.md
git commit -m "docs(viewer): README 启动与使用说明"
```

---

## Task 7: 端到端烟雾测试

**Files:** 无新增（验证所有交付物）

- [ ] **Step 1: 跑全部单元测试**

Run: `uv run pytest tests/insight/test_viewer_data.py -v`
Expected: PASS（8 passed）

- [ ] **Step 2: 验证 data.py 在真实数据库上可读**

Run: `uv run python -c "from insight.viewer.data import load_notes; print(len(load_notes()))"`
Expected: 打印一个数字 ≥ 1（当前生产库是 44 条）

- [ ] **Step 3: 验证 Streamlit 脚本可启动（5 秒后 Ctrl+C 退出）**

Run:
```bash
timeout 8 uv run --with streamlit streamlit run insight/viewer/app.py
# 或 Windows PowerShell：
# Start-Process -NoNewWindow uv -ArgumentList "run","--with","streamlit","streamlit","run","insight/viewer/app.py" -RedirectStandardOutput stdout.log
# Start-Sleep -Seconds 5
# Get-Process streamlit | Stop-Process -Force
```

Expected: 输出含 `You can now view your Streamlit app in your browser.` 后无致命错误；5–8 秒后被 timeout 杀掉

- [ ] **Step 4: 视觉验证（手动，10 秒）**

1. 浏览器自动打开 `http://localhost:8501`
2. 顶部统计正确显示笔记/评论数
3. 中段表格显示笔记列表（按时间倒序）
4. 选中某行 → 下方显示该笔记详情 + 评论列表
5. 点 🔄 → 页面无错

- [ ] **Step 5: 提交（如有改动；否则跳过）**

```bash
git status
# 若无改动：
echo "No changes to commit"
# 若有改动：
git add -A && git commit -m "chore(viewer): end-to-end smoke test cleanup"
```

---

## 验收清单

完成后应满足：

- [x] `insight/viewer/{__init__,app,data}.py` 与 `README.md` 均已创建
- [x] `tests/insight/test_viewer_data.py` 8 个用例全过
- [x] `uv run --with streamlit streamlit run insight/viewer/app.py` 可启动并展示真实数据
- [x] **未修改** MediaCrawler 任何上游文件（`git diff upstream/main -- '*.py' '*.toml'` 应仅显示 `insight/viewer/` 与 `tests/insight/test_viewer_data.py` 与 `docs/superpowers/*`）
- [x] `pyproject.toml` / `requirements.txt` 中**无** streamlit 条目
- [x] 6 个 commit，提交信息遵循现有风格
