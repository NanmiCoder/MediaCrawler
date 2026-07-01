# -*- coding: utf-8 -*-
"""
教学版回归测试：快手(kuaishou)存储链路不再持久化可定位真人的用户个人信息。

覆盖：
1. update_kuaishou_video —— mock video_item(含 author.id/name/headerUrl + photo 内容字段 + type)
   经 FakeStore 捕获，断言捕获 dict 不含禁用键(user_id/avatar/signature/ip_location/gender)、
   含 creator_hash(≠原 user_id)、nickname 脱敏(≠原文)。
2. update_ks_video_comment —— V2(snake_case) 与旧 GraphQL(camelCase) 两种 comment_item 格式各测一次。
3. test_kuaishou_store_end_to_end_sqlite —— 端到端：FakeStore 捕获真实 dict ->
   KuaishouVideo(**captured) 触发 ORM 列校验 -> 写入内存 SQLite -> 查询回读校验属性。

约束：只新建本测试文件，只读源码不改源码；不依赖网络/登录。
"""
import asyncio
import contextlib
import types

import pytest

import store.kuaishou as ks
from store.kuaishou import update_kuaishou_video, update_ks_video_comment
from tools.user_hash import anonymize_user_id, mask_nickname

# 教学版禁用字段(键)：一律不得出现在存储 dict 中。
# 昵称字段 nickname 允许保留，但值须脱敏。
FORBIDDEN_KEYS = {"user_id", "avatar", "signature", "ip_location", "gender"}

# ----------------------------- mock 数据 -----------------------------

MOCK_VIDEO_ID = "3xf8e9kq2b7w4"
MOCK_AUTHOR_ID = "ks_author_001"
MOCK_AUTHOR_NAME = "快手达人"
MOCK_CAPTION = "这是一条测试视频，教学版脱敏回归 #测试"

# 评论作者(两种格式用不同 id/昵称，便于分别断言)
MOCK_COMMENT_V2_AUTHOR_ID = "ks_user_888"
MOCK_COMMENT_V2_AUTHOR_NAME = "快手老铁"
MOCK_COMMENT_LEGACY_AUTHOR_ID = "ks_user_777"
MOCK_COMMENT_LEGACY_AUTHOR_NAME = "快乐源泉"


def make_mock_video() -> dict:
    """贴近真实快手结构的 video_item：author 在顶层，photo 含内容字段。
    author.headerUrl 与各禁用字段一样不应进入存储 dict。"""
    return {
        "type": 1,
        "photo": {
            "id": MOCK_VIDEO_ID,
            "caption": MOCK_CAPTION,
            "timestamp": 1700000000000,
            "coverUrl": "https://p.kuaishou.com/cover/abc.jpg",
            "photoUrl": "https://v.kuaishou.com/play/abc.mp4",
            "realLikeCount": 12345,
            "viewCount": 67890,
        },
        "author": {
            "id": MOCK_AUTHOR_ID,
            "name": MOCK_AUTHOR_NAME,
            "headerUrl": "https://p.kuaishou.com/header/u001.jpg",
        },
    }


def make_mock_comment_v2() -> dict:
    """V2 API 格式：snake_case 字段名，comment_id 为 int。"""
    return {
        "comment_id": 9001,
        "timestamp": 1700000001234,
        "content": "太搞笑了哈哈哈",
        "author_id": MOCK_COMMENT_V2_AUTHOR_ID,
        "author_name": MOCK_COMMENT_V2_AUTHOR_NAME,
        "headurl": "https://p.kuaishou.com/header/u888.jpg",
        "commentCount": 7,
    }


def make_mock_comment_legacy() -> dict:
    """旧 GraphQL API 格式：camelCase 字段名。"""
    return {
        "commentId": 8001,
        "timestamp": 1700000005678,
        "content": "这条评论来自旧 GraphQL 接口",
        "authorId": MOCK_COMMENT_LEGACY_AUTHOR_ID,
        "authorName": MOCK_COMMENT_LEGACY_AUTHOR_NAME,
        "headurl": "https://p.kuaishou.com/header/u777.jpg",
        "subCommentCount": 3,
    }


# ----------------------------- FakeStore 捕获 -----------------------------


@contextlib.contextmanager
def _patch_create_store():
    """把 KuaishouStoreFactory.create_store 替换为返回捕获用 FakeStore 的 staticmethod。
    FakeStore 把 store_content/store_comment 收到的 dict 原样写入 holder.content / holder.comment。

    保存/还原走类 __dict__ 中的 staticmethod 描述符本身，避免把 staticmethod 退化为普通方法
    而污染后续测试。"""
    holder = types.SimpleNamespace(content={}, comment={})

    class FakeStore:
        async def store_content(self, content_item):
            holder.content.clear()
            holder.content.update(content_item)

        async def store_comment(self, comment_item):
            holder.comment.clear()
            holder.comment.update(comment_item)

        async def store_creator(self, creator):
            pass

    orig = ks.KuaishouStoreFactory.__dict__["create_store"]
    ks.KuaishouStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        yield holder
    finally:
        ks.KuaishouStoreFactory.create_store = orig


def _assert_no_forbidden_keys(d: dict, label: str):
    hit = set(d.keys()) & FORBIDDEN_KEYS
    assert not hit, f"[{label}] 输出仍含禁用字段键: {hit}"


# ----------------------------- 测试 -----------------------------


def test_kuaishou_video_masks_user_info():
    """video 链路：原始 user_id 转 creator_hash、昵称脱敏、headerUrl/禁用键不落库。"""
    with _patch_create_store() as holder:
        asyncio.run(update_kuaishou_video(make_mock_video()))
    captured = holder.content

    assert captured, "FakeStore 未捕获到 content_item"
    _assert_no_forbidden_keys(captured, "kuaishou_video")
    # 头像字段不应进入存储 dict(author.headerUrl 已被丢弃)
    assert "headerUrl" not in captured and "avatar" not in captured

    # creator_hash 存在且不等于原始 user_id
    assert captured.get("creator_hash") == anonymize_user_id(MOCK_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_AUTHOR_ID
    assert captured["creator_hash"]  # 非空

    # 昵称已脱敏：等于 mask_nickname(原文) 且不等于原文
    assert captured.get("nickname") == mask_nickname(MOCK_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_AUTHOR_NAME
    assert "*" in captured["nickname"]

    # 内容字段保留(video_id / desc / title)
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["desc"] == MOCK_CAPTION
    assert captured["title"] == MOCK_CAPTION
    # video_type 来自 video_item.type，被 str() 化
    assert captured["video_type"] == "1"
    # 计数字段被 str() 化
    assert captured["liked_count"] == "12345"
    assert captured["viewd_count"] == "67890"


def test_kuaishou_comment_v2_masks_user_info():
    """评论 V2(snake_case)格式：author_id/author_name 经匿名+脱敏，headurl 不落库。"""
    with _patch_create_store() as holder:
        asyncio.run(update_ks_video_comment(MOCK_VIDEO_ID, make_mock_comment_v2()))
    captured = holder.comment

    assert captured, "FakeStore 未捕获到 comment_item"
    _assert_no_forbidden_keys(captured, "kuaishou_comment_v2")
    assert "headurl" not in captured and "avatar" not in captured

    # comment_id 由 int 转为 str
    assert captured["comment_id"] == "9001"
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["content"] == "太搞笑了哈哈哈"
    # V2 用 commentCount
    assert captured["sub_comment_count"] == "7"

    # creator_hash / 昵称
    assert captured["creator_hash"] == anonymize_user_id(MOCK_COMMENT_V2_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_COMMENT_V2_AUTHOR_ID
    assert captured["nickname"] == mask_nickname(MOCK_COMMENT_V2_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_COMMENT_V2_AUTHOR_NAME
    assert "*" in captured["nickname"]


def test_kuaishou_comment_legacy_masks_user_info():
    """评论旧 GraphQL(camelCase)格式：authorId/authorName 经匿名+脱敏，headurl 不落库。"""
    with _patch_create_store() as holder:
        asyncio.run(update_ks_video_comment(MOCK_VIDEO_ID, make_mock_comment_legacy()))
    captured = holder.comment

    assert captured, "FakeStore 未捕获到 comment_item"
    _assert_no_forbidden_keys(captured, "kuaishou_comment_legacy")
    assert "headurl" not in captured and "avatar" not in captured

    # commentId 由 int 转为 str
    assert captured["comment_id"] == "8001"
    assert captured["video_id"] == MOCK_VIDEO_ID
    assert captured["content"] == "这条评论来自旧 GraphQL 接口"
    # 旧格式用 subCommentCount
    assert captured["sub_comment_count"] == "3"

    # creator_hash / 昵称
    assert captured["creator_hash"] == anonymize_user_id(MOCK_COMMENT_LEGACY_AUTHOR_ID)
    assert captured["creator_hash"] != MOCK_COMMENT_LEGACY_AUTHOR_ID
    assert captured["nickname"] == mask_nickname(MOCK_COMMENT_LEGACY_AUTHOR_NAME)
    assert captured["nickname"] != MOCK_COMMENT_LEGACY_AUTHOR_NAME
    assert "*" in captured["nickname"]


def test_kuaishou_store_end_to_end_sqlite():
    """端到端：FakeStore 捕获真实 dict -> KuaishouVideo(**captured) ORM 列校验
    -> 写入内存 SQLite -> 查询回读，验证属性正确且无禁用列。

    全程在同一个事件循环内完成(aiosqlite 连接绑定事件循环，跨 loop 会报错)，
    不 patch db_session.get_session，而是直接用自建内存 engine 走 ORM 写入/查询。"""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from database.models import Base, KuaishouVideo, KuaishouVideoComment

    async def run():
        # 内存 SQLite + StaticPool：单连接共享，保证 create_all 与后续读写同一库
        engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
        SessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[KuaishouVideo.__table__, KuaishouVideoComment.__table__],
            )

        # 1) 经 update_kuaishou_video 产生真实存储 dict(FakeStore 捕获)
        with _patch_create_store() as holder:
            await update_kuaishou_video(make_mock_video())
        captured = holder.content
        assert captured, "FakeStore 未捕获到 content_item"

        # 2) ORM 列校验：captured 的所有 key 必须是 KuaishouVideo 的合法列，
        #    否则 KuaishouVideo(**captured) 抛 TypeError(若有禁用/多余键即暴露源码 bug)
        valid_cols = {c.name for c in KuaishouVideo.__table__.columns}
        assert set(captured.keys()) <= valid_cols, (
            f"captured 含非合法列: {set(captured.keys()) - valid_cols}"
        )
        obj = KuaishouVideo(**captured)  # 不抛异常即通过列校验
        assert obj.video_id == MOCK_VIDEO_ID
        assert obj.creator_hash == anonymize_user_id(MOCK_AUTHOR_ID)
        assert obj.creator_hash != MOCK_AUTHOR_ID
        assert obj.nickname == mask_nickname(MOCK_AUTHOR_NAME)
        assert obj.nickname != MOCK_AUTHOR_NAME
        assert obj.desc == MOCK_CAPTION  # 内容保留

        # 3) 真实写库 + 查询回读
        async with SessionFactory() as session:
            session.add(obj)
            await session.commit()

            res = await session.execute(
                select(KuaishouVideo).where(KuaishouVideo.video_id == MOCK_VIDEO_ID)
            )
            row = res.scalar_one()
            assert row is not None
            assert row.video_id == MOCK_VIDEO_ID
            assert row.creator_hash == anonymize_user_id(MOCK_AUTHOR_ID)
            assert row.creator_hash != MOCK_AUTHOR_ID
            assert row.nickname == mask_nickname(MOCK_AUTHOR_NAME)
            assert row.nickname != MOCK_AUTHOR_NAME
            # 内容字段保留
            assert row.desc == MOCK_CAPTION
            assert row.title == MOCK_CAPTION
            # ORM 行对象上不应存在任何禁用列属性
            for bad in FORBIDDEN_KEYS:
                assert not hasattr(row, bad), f"KuaishouVideo 行对象仍含禁用属性: {bad}"

        await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
