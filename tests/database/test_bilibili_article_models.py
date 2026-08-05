# -*- coding: utf-8 -*-

from database.models import BilibiliArticle, BilibiliArticleComment


def test_bilibili_article_table_name():
    assert BilibiliArticle.__tablename__ == "bilibili_article"


def test_bilibili_article_columns():
    columns = set(BilibiliArticle.__table__.columns.keys())

    assert {
        "id",
        "article_id",
        "article_url",
        "title",
        "desc",
        "content",
        "creator_hash",
        "nickname",
        "liked_count",
        "favorite_count",
        "share_count",
        "comment_count",
        "create_time",
        "source_keyword",
        "add_ts",
        "last_modify_ts",
    }.issubset(columns)


def test_bilibili_article_comment_table_name():
    assert BilibiliArticleComment.__tablename__ == "bilibili_article_comment"


def test_bilibili_article_comment_columns():
    columns = set(BilibiliArticleComment.__table__.columns.keys())

    assert {
        "id",
        "creator_hash",
        "nickname",
        "add_ts",
        "last_modify_ts",
        "comment_id",
        "article_id",
        "content",
        "create_time",
        "sub_comment_count",
        "parent_comment_id",
        "like_count",
    }.issubset(columns)
