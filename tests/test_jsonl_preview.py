# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_jsonl_preview.py
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

import httpx
import pytest
from fastapi import HTTPException

from api.main import app
from api.routers import data


@pytest.mark.asyncio
async def test_jsonl_results_can_be_listed_counted_previewed_and_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    result_dir = tmp_path / "xhs" / "jsonl"
    result_dir.mkdir(parents=True)
    output = result_dir / "results.jsonl"
    output.write_text('{"id": "1", "text": "中文"}\n\n{"id": "2"}\n', encoding="utf-8")
    files = (await data.list_data_files())["files"]
    assert len(files) == 1
    assert files[0]["record_count"] == 2
    assert (await data.get_data_stats())["by_type"] == {"jsonl": 1}
    preview = await data.get_file_content("xhs/jsonl/results.jsonl", limit=1)
    assert preview == {"data": [{"id": "1", "text": "中文"}], "total": 2}
    assert (await data.download_file("xhs/jsonl/results.jsonl")).path == output


@pytest.mark.asyncio
async def test_invalid_jsonl_reports_bad_input(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    (tmp_path / "broken.jsonl").write_text('{"id": 1}\ninvalid\n', encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        await data.get_file_content("broken.jsonl")
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_uppercase_jsonl_with_utf8_bom_has_consistent_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    (tmp_path / "result.JSONL").write_text('{"text": "中文"}\n', encoding="utf-8-sig")
    files = (await data.list_data_files())["files"]
    assert files[0]["type"] == "jsonl"
    assert files[0]["record_count"] == 1
    assert (await data.get_file_content("result.JSONL"))["data"] == [{"text": "中文"}]


@pytest.mark.asyncio
async def test_invalid_jsonl_encoding_reports_bad_input(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "DATA_DIR", tmp_path)
    (tmp_path / "broken.jsonl").write_bytes(b"\xff\xfeinvalid")
    with pytest.raises(HTTPException) as error:
        await data.get_file_content("broken.jsonl")
    assert error.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1, 1001])
async def test_jsonl_preview_limit_is_validated(monkeypatch, limit):
    monkeypatch.delenv("MEDIACRAWLER_API_TOKEN", raising=False)
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8080") as client:
        response = await client.get("/api/data/files/results.jsonl", params={"limit": limit})
    assert response.status_code == 422
