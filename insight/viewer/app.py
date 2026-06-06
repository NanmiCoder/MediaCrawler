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

import pandas as pd
import streamlit as st

from insight.viewer.data import (
    DB_PATH,
    format_ts,
    load_comments,
    load_notes,
)


def _to_int(v: object) -> int:
    """安全地把 comment_count 等字符串字段转 int，失败回 0。"""
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


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
    total_comments = sum(_to_int(n.get("comment_count")) for n in notes)
    st.caption(f"共 {len(notes)} 条笔记 / {total_comments} 条评论（按 comment_count 估算）")
with col_btn:
    if st.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.session_state.pop("notes_table", None)  # 清掉旧选择，避免重读后指向错位
        st.rerun()


# ---------- 笔记列表 ----------
if not notes:
    st.info("暂无数据")
    st.stop()

# 准备表格数据：加一列"发布时间"已格式化
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
st.caption("点击表格中的行查看笔记详情与评论")
event = st.dataframe(
    df[["#", "标题", "点赞", "评论数", "关键词", "发布时间"]],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="notes_table",
)

# Streamlit 1.32+：用户点击某行后 event.selection.rows 包含选中行号（0-based）
selected_rows = getattr(event, "selection", None)
selected_idx = selected_rows.rows[0] if selected_rows and selected_rows.rows else None


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
