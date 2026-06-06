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


def test_format_ts_normal_timestamp():
    """正常时间戳格式化。"""
    # 2024-03-15 12:34:00 UTC+8 = 1710477240
    assert format_ts(1710477240) == "2024-03-15 12:34"


def test_format_ts_none_returns_dash():
    """None 返回 '—'。"""
    assert format_ts(None) == "—"


def test_format_ts_zero_returns_dash():
    """0（未设置）返回 '—'。"""
    assert format_ts(0) == "—"