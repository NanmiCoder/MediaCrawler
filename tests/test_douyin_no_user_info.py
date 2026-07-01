# -*- coding: utf-8 -*-
"""
教学版回归测试(抖音 douyin):确保 store/douyin 存储链路不再持久化可定位真人的
用户个人信息。

教学版约定:用户 ID(uid/sec_uid/short_user_id/user_unique_id)/IP/头像/签名/性别
一律不持久化;原始 uid 经 tools.user_hash.anonymize_user_id 转成 creator_hash
(sha256 截断 16 位)写入;昵称保留但经 mask_nickname 中间脱敏。desc(作品描述)是
内容字段,保留。

覆盖:
1. test_douyin_aweme_masks_user_info
   - mock aweme_item(含 author.uid/sec_uid/short_id/unique_id/nickname/
     avatar_thumb.url_list/signature、aweme_item.ip_label、statistics、video/
     music/images 等内容字段)
   - FakeStore 捕获 update_douyin_aweme 产出的存储 dict
   - 断言:不含禁用键;含 creator_hash(≠原 uid);nickname 脱敏≠原文;
     原始敏感值不在任何存储值中;内容字段正常提取
2. test_douyin_comment_masks_user_info
   - 同上,针对 update_dy_aweme_comment(含嵌套 user.* / comment_item.ip_label /
     cid / text / image_list 等)
3. test_douyin_store_end_to_end_sqlite
   - FakeStore 捕获真实 dict → DouyinAweme(**captured) 构造(ORM 列校验:
     dict 多了已删列会 TypeError)
   - 端到端:monkeypatch db_session 为内存 SQLite engine + create_all,
     走真实 DouyinDbStoreImplement.store_content(含 int(aweme_id) / if title
     判断 / DouyinAweme(**content_item)),查询回读,验证 dict key 与删列后 ORM
     完全对得上
"""
import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
import store.douyin as ds
from database import db_session
from database.models import Base, DouyinAweme, DouyinAwemeComment
from tools.user_hash import anonymize_user_id, mask_nickname


# 抖音教学版禁用字段(键):不得作为存储 dict 的 key 出现。
FORBIDDEN_KEYS = {
    "user_id", "sec_uid", "short_user_id", "user_unique_id",
    "avatar", "user_signature", "ip_location",
}


# ----------------------------- mock payload -----------------------------

def _build_aweme_item() -> dict:
    """贴近真实抖音结构的 mock aweme_item。
    含会被拍平的用户字段(uid/sec_uid/short_id/unique_id/avatar/signature)与
    ip_label,这些必须不落库;同时含 statistics/video/music/images 等内容字段,
    让 _extract_* 辅助函数返回非空值。"""
    return {
        "aweme_id": "7234567890123456",
        "aweme_type": 0,
        "desc": "这是一个作品描述,同时作为 title",
        "create_time": 1700000000,
        "ip_label": "上海",  # IP 归属地,禁用
        "author": {
            "uid": "9876543210",
            "sec_uid": "MS4wLjABAAAASecretSecUidForTest",
            "short_id": "88877766",
            "unique_id": "creator_unique_abc",
            "nickname": "抖音创作者",
            "avatar_thumb": {"url_list": ["http://x/avatar_thumb.jpg"]},
            "avatar_medium": {"url_list": ["http://x/avatar_medium.jpg"]},
            "signature": "这是创作者个人签名内容",
        },
        "statistics": {
            "digg_count": 100,
            "collect_count": 5,
            "comment_count": 20,
            "share_count": 3,
        },
        "video": {
            "raw_cover": {"url_list": ["", "http://x/cover.jpg"]},
            "origin_cover": {"url_list": ["", "http://x/cover2.jpg"]},
            "play_addr_h264": {"url_list": ["", "http://x/video_h264.mp4"]},
            "play_addr_256": {"url_list": ["", "http://x/video_256.mp4"]},
            "play_addr": {"url_list": ["", "http://x/video.mp4"]},
        },
        "music": {
            "play_url": {"uri": "http://x/music.mp3"},
        },
        "images": [
            {"url_list": ["", "http://x/note_img1.jpg"]},
            {"url_list": ["", "http://x/note_img2.jpg"]},
        ],
    }


def _build_comment_item() -> dict:
    """贴近真实抖音结构的 mock comment_item。aweme_id 须与传入
    update_dy_aweme_comment 的 aweme_id 一致。"""
    return {
        "aweme_id": "7234567890123456",
        "cid": "1111111111",
        "text": "这是一条评论内容",
        "create_time": 1700000001,
        "reply_id": "0",
        "reply_comment_total": 2,
        "digg_count": 5,
        "ip_label": "北京",  # IP 归属地,禁用
        "user": {
            "uid": "555666777",
            "sec_uid": "MS4wLjABBBBCommentSecUid",
            "short_id": "22233344",
            "unique_id": "commenter_unique_xyz",
            "nickname": "评论员小王",
            "avatar_medium": {"url_list": ["http://x/cavatar.jpg"]},
            "signature": "评论员个人签名内容",
        },
        "image_list": [
            {"origin_url": {"url_list": ["", "http://x/cimg.jpg"]}},
        ],
    }


# ----------------------------- 辅助 -----------------------------

class _FakeStore:
    """捕获存储 dict,不真正落库。"""

    def __init__(self):
        self.contents = []
        self.comments = []

    async def store_content(self, content_item):
        self.contents.append(dict(content_item))

    async def store_comment(self, comment_item):
        self.comments.append(dict(comment_item))


def _patch_factory(fake):
    """把 DouyinStoreFactory.create_store 替换为返回 fake,返回原方法用于还原。"""
    orig = ds.DouyinStoreFactory.create_store
    ds.DouyinStoreFactory.create_store = staticmethod(lambda: fake)
    return orig


def _assert_no_forbidden(captured: dict, label: str):
    hit = set(captured.keys()) & FORBIDDEN_KEYS
    assert not hit, f"[{label}] 存储 dict 仍含禁用键: {hit}"


def _assert_raw_values_absent(captured: dict, raw_values, label: str):
    """禁用的原始敏感值(uid/sec_uid/头像/签名/IP 等)不得出现在任何存储值里。
    creator_hash 是由 uid 派生的匿名哈希(已单独断言 ≠ 原文),不参与子串扫描。"""
    leaked = []
    for rv in raw_values:
        if not rv:
            continue
        for k, v in captured.items():
            if k == "creator_hash":
                continue
            if isinstance(v, str) and rv in v:
                leaked.append((k, rv))
    assert not leaked, f"[{label}] 存储 dict 中泄漏了原始敏感值: {leaked}"


# ----------------------------- 测试 -----------------------------

def test_douyin_aweme_masks_user_info():
    aweme = _build_aweme_item()
    raw_uid = aweme["author"]["uid"]
    raw_nick = aweme["author"]["nickname"]
    raw_sensitive = [
        raw_uid,
        aweme["author"]["sec_uid"],
        aweme["author"]["short_id"],
        aweme["author"]["unique_id"],
        aweme["author"]["avatar_thumb"]["url_list"][0],
        aweme["author"]["signature"],
        aweme["ip_label"],
    ]

    fake = _FakeStore()
    orig = _patch_factory(fake)
    try:
        asyncio.run(ds.update_douyin_aweme(aweme))
    finally:
        ds.DouyinStoreFactory.create_store = orig

    assert len(fake.contents) == 1
    captured = fake.contents[0]

    # 1. 禁用键不出现
    _assert_no_forbidden(captured, "douyin_aweme")
    # 2. 原始敏感值不泄漏到任何存储值
    _assert_raw_values_absent(captured, raw_sensitive, "douyin_aweme")
    # 3. creator_hash 存在、≠原 uid、与 anonymize_user_id 一致
    assert captured.get("creator_hash")
    assert captured["creator_hash"] != raw_uid
    assert captured["creator_hash"] == anonymize_user_id(raw_uid)
    # 4. nickname 保留但脱敏,≠原文,与 mask_nickname 一致
    assert captured.get("nickname")
    assert captured["nickname"] != raw_nick
    assert captured["nickname"] == mask_nickname(raw_nick)
    # 5. 内容字段保留(desc/title 是作品描述,不禁用)
    assert captured.get("desc") == aweme["desc"]
    assert captured.get("title") == aweme["desc"]
    # 6. _extract_* 内容字段正常提取(非空)
    assert captured.get("cover_url") == "http://x/cover.jpg"
    assert captured.get("video_download_url") == "http://x/video_h264.mp4"
    assert captured.get("music_download_url") == "http://x/music.mp3"
    assert "http://x/note_img1.jpg" in captured.get("note_download_url", "")
    # 7. 互动数据拍平
    assert captured.get("liked_count") == "100"
    assert captured.get("collected_count") == "5"
    assert captured.get("comment_count") == "20"
    assert captured.get("share_count") == "3"
    assert captured.get("aweme_url") == f"https://www.douyin.com/video/{aweme['aweme_id']}"


def test_douyin_comment_masks_user_info():
    aweme_id = "7234567890123456"
    comment = _build_comment_item()
    raw_uid = comment["user"]["uid"]
    raw_nick = comment["user"]["nickname"]
    raw_sensitive = [
        raw_uid,
        comment["user"]["sec_uid"],
        comment["user"]["short_id"],
        comment["user"]["unique_id"],
        comment["user"]["avatar_medium"]["url_list"][0],
        comment["user"]["signature"],
        comment["ip_label"],
    ]

    fake = _FakeStore()
    orig = _patch_factory(fake)
    try:
        asyncio.run(ds.update_dy_aweme_comment(aweme_id, comment))
    finally:
        ds.DouyinStoreFactory.create_store = orig

    assert len(fake.comments) == 1
    captured = fake.comments[0]

    _assert_no_forbidden(captured, "douyin_comment")
    _assert_raw_values_absent(captured, raw_sensitive, "douyin_comment")

    assert captured.get("creator_hash")
    assert captured["creator_hash"] != raw_uid
    assert captured["creator_hash"] == anonymize_user_id(raw_uid)
    assert captured.get("nickname")
    assert captured["nickname"] != raw_nick
    assert captured["nickname"] == mask_nickname(raw_nick)

    # 评论内容/ID 保留
    assert captured.get("content") == comment["text"]
    assert captured.get("comment_id") == comment["cid"]
    assert captured.get("aweme_id") == aweme_id
    assert captured.get("parent_comment_id") == "0"
    assert captured.get("sub_comment_count") == "2"
    # 评论图片提取
    assert captured.get("pictures") == "http://x/cimg.jpg"


def test_douyin_store_end_to_end_sqlite(monkeypatch):
    aweme = _build_aweme_item()
    raw_uid = aweme["author"]["uid"]
    raw_nick = aweme["author"]["nickname"]

    # ---- 1. FakeStore 捕获 update_douyin_aweme 产出的真实 dict ----
    fake = _FakeStore()
    orig = _patch_factory(fake)
    try:
        asyncio.run(ds.update_douyin_aweme(aweme))
    finally:
        ds.DouyinStoreFactory.create_store = orig
    assert len(fake.contents) == 1
    captured = fake.contents[0]

    # ---- 2. DouyinAweme(**captured) 构造校验 ----
    # dict 多了已删列会 TypeError,少了非空必填列 SQLAlchemy 也会报错;
    # 此处证明 captured 的 key 与删列后 ORM 列完全对得上,不抛异常。
    obj = DouyinAweme(**captured)
    assert obj.aweme_id == aweme["aweme_id"]
    assert obj.creator_hash == anonymize_user_id(raw_uid)
    assert obj.creator_hash != raw_uid
    assert obj.nickname == mask_nickname(raw_nick)
    assert obj.nickname != raw_nick
    assert obj.title == aweme["desc"]
    assert obj.desc == aweme["desc"]
    _assert_no_forbidden(captured, "douyin_aweme_orm_construct")

    # ---- 3. 端到端:内存 SQLite + 真实 store_content ----
    # 用 StaticPool 保证 :memory: 库在同一个连接上持久(跨 session 可见)。
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    # 让 db_session 用内存 engine;SAVE_DATA_OPTION=db 让工厂走 DouyinDbStoreImplement
    monkeypatch.setattr(db_session, "get_async_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def _scenario():
        # 建表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # 真实 store_content 路径(含 int(aweme_id) 与 if content_item.get("title") 判断)
        await ds.update_douyin_aweme(aweme)
        # 查询回读
        async with db_session.get_session() as session:
            res = await session.execute(
                select(DouyinAweme).where(DouyinAweme.aweme_id == aweme["aweme_id"])
            )
            row = res.scalar_one_or_none()
        await engine.dispose()
        return row

    row = asyncio.run(_scenario())

    # ---- 4. 回读断言 ----
    assert row is not None, "作品未写入 SQLite"
    assert row.aweme_id == aweme["aweme_id"]
    assert row.creator_hash == anonymize_user_id(raw_uid)
    assert row.creator_hash != raw_uid
    assert row.nickname == mask_nickname(raw_nick)
    assert row.nickname != raw_nick
    assert row.desc == aweme["desc"]
    assert row.title == aweme["desc"]
    assert row.cover_url == "http://x/cover.jpg"
    assert row.video_download_url == "http://x/video_h264.mp4"
    assert row.music_download_url == "http://x/music.mp3"
    # 禁用列在 ORM 上不存在(自省)
    orm_cols = {c.name for c in DouyinAweme.__table__.columns}
    assert not (orm_cols & FORBIDDEN_KEYS), f"ORM 仍含禁用列: {orm_cols & FORBIDDEN_KEYS}"
    # captured 的所有 key 都是合法 ORM 列(无悬空 key)
    assert set(captured.keys()).issubset(orm_cols), (
        f"captured 含非 ORM 列: {set(captured.keys()) - orm_cols}"
    )

    # 评论同样做一次 ORM 构造校验(证明 comment dict key 对得上)
    comment = _build_comment_item()
    fake_c = _FakeStore()
    orig_c = _patch_factory(fake_c)
    try:
        asyncio.run(ds.update_dy_aweme_comment(comment["aweme_id"], comment))
    finally:
        ds.DouyinStoreFactory.create_store = orig_c
    captured_comment = fake_c.comments[0]
    comment_obj = DouyinAwemeComment(**captured_comment)  # 不抛异常即对得上
    assert comment_obj.comment_id == comment["cid"]
    assert comment_obj.creator_hash == anonymize_user_id(comment["user"]["uid"])
    assert comment_obj.nickname == mask_nickname(comment["user"]["nickname"])
    _assert_no_forbidden(captured_comment, "douyin_comment_orm_construct")
    comment_orm_cols = {c.name for c in DouyinAwemeComment.__table__.columns}
    assert set(captured_comment.keys()).issubset(comment_orm_cols), (
        f"captured_comment 含非 ORM 列: {set(captured_comment.keys()) - comment_orm_cols}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
