# -*- coding: utf-8 -*-
"""
回归测试(小红书 xhs):访问受限异常不能击穿到 asyncio.gather。

背景:
IPBlockError / PlatformAccessError 被加入 request() 的 retry_if_not_exception_type 之后,
tenacity 会直接重抛原异常而不再包装成 RetryError。core 层原先只 catch
RetryError / NoteNotFoundError / DataFetchError / KeyError,导致单条笔记被限流
就会让整批 gather 抛出,同批已抓到但未入库的数据全部丢失。

覆盖:
1. 笔记详情任务遇到 IPBlockError / PlatformAccessError 时返回 None 并跳过。
2. 批量 gather 不会因为其中一条被限流而整体失败。
3. 创作者主页被限流时跳过该创作者,而不是中断整个任务。
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

import config
from media_platform.xhs.core import XiaoHongShuCrawler
from media_platform.xhs.exception import IPBlockError, PlatformAccessError


def make_crawler(xhs_client):
    crawler = XiaoHongShuCrawler.__new__(XiaoHongShuCrawler)
    crawler.xhs_client = xhs_client
    return crawler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        IPBlockError("Network connection error"),
        PlatformAccessError("XHS request blocked with HTTP 403"),
    ],
)
async def test_note_detail_task_skips_access_error(error):
    xhs_client = AsyncMock()
    xhs_client.get_note_by_id.side_effect = error
    xhs_client.get_note_by_id_from_html.side_effect = AssertionError(
        "被限流后不应再走 HTML 兜底"
    )

    result = await make_crawler(xhs_client).get_note_detail_async_task(
        note_id="n1",
        xsec_source="pc_search",
        xsec_token="token",
        semaphore=asyncio.Semaphore(1),
    )

    assert result is None


@pytest.mark.asyncio
async def test_gather_survives_single_blocked_note():
    """一条笔记被限流不能让同批次其他笔记的结果一起丢掉。"""
    xhs_client = AsyncMock()

    async def get_note_by_id(note_id, xsec_source, xsec_token):
        if note_id == "blocked":
            raise PlatformAccessError("XHS account security restriction, code: 300011")
        return {"note_id": note_id}

    xhs_client.get_note_by_id.side_effect = get_note_by_id
    crawler = make_crawler(xhs_client)

    semaphore = asyncio.Semaphore(2)
    results = await asyncio.gather(
        *[
            crawler.get_note_detail_async_task(
                note_id=note_id,
                xsec_source="pc_search",
                xsec_token="token",
                semaphore=semaphore,
            )
            for note_id in ("ok1", "blocked", "ok2")
        ]
    )

    assert [r.get("note_id") if r else None for r in results] == ["ok1", None, "ok2"]


@pytest.mark.asyncio
async def test_creator_flow_skips_blocked_creator(monkeypatch):
    """创作者主页 403 时跳过该创作者,不中断整个采集任务。"""
    monkeypatch.setattr(
        config,
        "XHS_CREATOR_ID_LIST",
        [
            "https://www.xiaohongshu.com/user/profile/blocked?xsec_token=a&xsec_source=pc_feed",
            "https://www.xiaohongshu.com/user/profile/ok?xsec_token=b&xsec_source=pc_feed",
        ],
        raising=False,
    )

    crawled_user_ids = []
    xhs_client = AsyncMock()

    async def get_creator_info(user_id, xsec_token, xsec_source):
        if user_id == "blocked":
            raise PlatformAccessError("XHS request blocked with HTTP 403")
        return {"user_id": user_id}

    async def get_all_notes_by_creator(user_id, **kwargs):
        crawled_user_ids.append(user_id)
        return []

    xhs_client.get_creator_info.side_effect = get_creator_info
    xhs_client.get_all_notes_by_creator.side_effect = get_all_notes_by_creator

    crawler = make_crawler(xhs_client)
    crawler.batch_get_note_comments = AsyncMock()
    monkeypatch.setattr(
        "media_platform.xhs.core.xhs_store.save_creator", AsyncMock(), raising=False
    )

    await crawler.get_creators_and_notes()

    # 被限流的创作者整体跳过,后面的创作者照常采集
    assert crawled_user_ids == ["ok"]
