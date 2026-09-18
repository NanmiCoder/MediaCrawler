# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_spreadsheet_formulas.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import csv

import openpyxl
import pytest

import config
from store.excel_store_base import ExcelStoreBase
from tools.async_file_writer import AsyncFileWriter


@pytest.fixture
def writer(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config, "ENABLE_GET_WORDCLOUD", False)
    return AsyncFileWriter("xhs", "search")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["=1+1", "+1+1", "-1+1", "@SUM(1)", "\t=1+1", "\r=1+1", "  =1+1"])
async def test_csv_neutralizes_formula_text(writer, value):
    await writer.write_to_csv({"content": value, "count": -2}, "comments")
    with open(writer._get_file_path("csv", "comments"), newline="", encoding="utf-8-sig") as source:
        row = next(csv.DictReader(source))
    assert row["content"] == "'" + value
    assert row["count"] == "-2"


@pytest.mark.asyncio
@pytest.mark.parametrize("method,sheet_name", [
    ("store_content", "Contents"), ("store_comment", "Comments"),
    ("store_creator", "Creators"), ("store_contact", "Contacts"), ("store_dynamic", "Dynamics"),
])
async def test_excel_remote_text_is_literal(writer, method, sheet_name):
    store = ExcelStoreBase("xhs")
    await getattr(store, method)({"text": "=1+1", "count": -2})
    store.flush()
    workbook = openpyxl.load_workbook(store.filename, data_only=False)
    try:
        sheet = workbook[sheet_name]
        assert sheet["A2"].value == "=1+1"
        assert sheet["A2"].data_type == "s"
        assert sheet["B2"].value == -2
        assert sheet["B2"].data_type == "n"
    finally:
        workbook.close()
