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