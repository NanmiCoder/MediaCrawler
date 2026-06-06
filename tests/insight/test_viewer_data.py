# -*- coding: utf-8 -*-
"""insight.viewer.data 纯函数单元测试。

仅测 data.py；app.py 不做单测（Streamlit 启动成本/收益不划算）。
"""
import datetime
import pytest

from insight.viewer.data import format_ts, load_comments, load_notes


def test_imports_smoke():
    """烟雾测试：所有公开函数可导入。"""
    assert callable(format_ts)
    assert callable(load_notes)
    assert callable(load_comments)


def test_format_ts_normal_timestamp():
    """正常时间戳格式化。"""
    ts = datetime.datetime(2024, 3, 15, 12, 34).timestamp()
    assert format_ts(int(ts)) == "2024-03-15 12:34"


def test_format_ts_none_returns_dash():
    """None 返回 '—'。"""
    assert format_ts(None) == "—"


def test_format_ts_zero_returns_dash():
    """0（未设置）返回 '—'。"""
    assert format_ts(0) == "—"


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


def test_load_notes_missing_table_raises(tmp_path):
    """xhs_note 表不存在时抛 OperationalError（让 UI 捕获后展示）。"""
    import sqlite3
    from insight.viewer.data import load_notes
    db = tmp_path / "empty.db"
    # 不建表
    with pytest.raises(sqlite3.OperationalError):
        load_notes(db_path=db)


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