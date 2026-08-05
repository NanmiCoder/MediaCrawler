# -*- coding: utf-8 -*-

import asyncio

import pytest

import config
from media_platform.bilibili.core import BilibiliCrawler
from media_platform.bilibili.field import BilibiliCommentType
from media_platform.bilibili.help import split_bilibili_specified_ids
from store import bilibili as bilibili_store


@pytest.fixture
def crawler(monkeypatch):
    crawler_obj = BilibiliCrawler()
    monkeypatch.setattr(config, "MAX_CONCURRENCY_NUM", 2)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "ENABLE_GET_SUB_COMMENTS", False)
    monkeypatch.setattr(config, "CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", 2)

    async def fake_sleep(_):
        return None

    monkeypatch.setattr("media_platform.bilibili.core.asyncio.sleep", fake_sleep)
    return crawler_obj


@pytest.mark.asyncio
async def test_get_specified_articles_fetches_detail_and_comments(monkeypatch, crawler):
    stored_articles = []
    comment_calls = []

    class FakeClient:
        async def get_article_info(self, article_id):
            return {"id": int(article_id), "title": "article title"}

        async def get_all_comments(
            self,
            oid,
            comment_type,
            crawl_interval,
            is_fetch_sub_comments,
            callback,
            max_count,
        ):
            comment_calls.append({
                "oid": oid,
                "comment_type": comment_type,
                "crawl_interval": crawl_interval,
                "is_fetch_sub_comments": is_fetch_sub_comments,
                "callback": callback,
                "max_count": max_count,
            })

    async def fake_update_article(article_detail):
        stored_articles.append(article_detail)

    monkeypatch.setattr(bilibili_store, "update_bilibili_article", fake_update_article)
    monkeypatch.setattr(crawler, "bili_client", FakeClient(), raising=False)

    await crawler.get_specified_articles(["cv123456"])

    assert stored_articles == [{"id": 123456, "title": "article title"}]
    assert comment_calls[0]["oid"] == "123456"
    assert comment_calls[0]["comment_type"] is BilibiliCommentType.ARTICLE
    assert comment_calls[0]["callback"] is bilibili_store.batch_update_bilibili_article_comments
    assert comment_calls[0]["max_count"] == 2


@pytest.mark.asyncio
async def test_batch_get_article_comments_respects_comment_flag(monkeypatch, crawler):
    called = False

    async def fake_get_article_comments(article_id, semaphore):
        nonlocal called
        called = True

    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", False)
    monkeypatch.setattr(crawler, "get_article_comments", fake_get_article_comments, raising=False)

    await crawler.batch_get_article_comments(["123456"])

    assert called is False


def test_split_bilibili_specified_ids_separates_video_and_article_inputs():
    video_ids, article_ids = split_bilibili_specified_ids([
        "BV1Sz4y1U77N",
        "https://www.bilibili.com/video/BV1d54y1g7db",
        "https://www.bilibili.com/read/cv123456",
        "cv654321",
        "789012",
    ])

    assert video_ids == [
        "BV1Sz4y1U77N",
        "https://www.bilibili.com/video/BV1d54y1g7db",
    ]
    assert article_ids == [
        "https://www.bilibili.com/read/cv123456",
        "cv654321",
        "789012",
    ]


@pytest.mark.asyncio
async def test_get_specified_ids_dispatches_videos_and_articles(monkeypatch, crawler):
    video_calls = []
    article_calls = []

    async def fake_get_specified_videos(video_ids):
        video_calls.append(video_ids)

    async def fake_get_specified_articles(article_ids):
        article_calls.append(article_ids)

    monkeypatch.setattr(crawler, "get_specified_videos", fake_get_specified_videos)
    monkeypatch.setattr(crawler, "get_specified_articles", fake_get_specified_articles)

    await crawler.get_specified_ids([
        "BV1Sz4y1U77N",
        "cv123456",
    ])

    assert video_calls == [["BV1Sz4y1U77N"]]
    assert article_calls == [["cv123456"]]
