# -*- coding: utf-8 -*-
"""
教学版回归测试(微博 weibo):确保微博存储链路不再持久化可定位真人的用户个人信息。

覆盖:
1. test_weibo_note_masks_user_info —— 用贴近真实微博结构的 mock note_item 喂
   store.weibo.update_weibo_note,用 FakeStore 捕获拍平后的存储 dict,断言:
   - 不含任何禁用字段键(user_id/avatar/gender/profile_url/ip_location/desc ...)
   - 含 creator_hash,且不等于原始 user id
   - nickname 已脱敏且不等于原文
2. test_weibo_comment_masks_user_info —— 同上,对 update_weibo_note_comment。
3. test_weibo_store_end_to_end_sqlite —— 端到端:把 update_weibo_note /
   update_weibo_note_comment 产生的真实 dict 用 SQLite 内存库走完整 ORM
   写入+查询。WeiboNote(**captured_dict) 会因 SQLAlchemy 声明式构造器对未知
   关键字的校验,在 dict 含已删列时直接抛 TypeError —— 以此证明 dict 的 key
   与删列后的 ORM 完全对得上,且表中无禁用列、有 creator_hash。

说明:微博 note 的正文存于 content 字段,update_weibo_note 不产生 desc 键
(WeiboNote ORM 亦无 desc 列),故不存在用户 description 被持久化的风险。
"""
import asyncio

import pytest

# 原始(明文)测试数据
RAW_USER_ID = 7654321
RAW_NICKNAME = "微博达人"
RAW_COMMENT_USER_ID = 111222
RAW_COMMENT_NICKNAME = "评论员小张"
NOTE_ID = "5123456789"
COMMENT_ID = "998877"
# 合法 RFC2822 时间串(weekday 与日期已对齐:2025-06-14 是周六)
RFC2822_TIME = "Sat Jun 14 12:00:00 +0800 2025"

# 禁用字段名(键)。昵称字段允许保留,但值必须脱敏。
FORBIDDEN_KEYS = {
    "user_id", "sec_uid", "short_user_id", "user_unique_id",
    "avatar", "user_avatar", "face", "sign", "profile_url", "user_link",
    "ip_location", "ip_address", "gender", "sex", "desc",
}


# ----------------------------- mock 数据 -----------------------------

def make_mock_note() -> dict:
    """贴近真实 m.weibo.cn 接口结构的 mock note_item(含嵌套 user 信息)。"""
    return {
        "mblog": {
            "id": NOTE_ID,
            "text": "今天天气不错 <a href='#'>@好友</a> 出去玩",
            "created_at": RFC2822_TIME,
            "attitudes_count": 10,
            "comments_count": 2,
            "reposts_count": 1,
            "user": {
                "id": RAW_USER_ID,
                "screen_name": RAW_NICKNAME,
                "avatar_hd": "https://wx avatar.example.com/7654321.jpg",
                "gender": "f",
                "profile_url": "https://m.weibo.cn/profile/7654321",
                "description": "这是一个用户签名",
                "ip_location": "上海",
                "followers_count": 9999,
            },
        }
    }


def make_mock_comment() -> dict:
    """贴近真实微博评论结构的 mock comment_item(含嵌套 user 信息)。"""
    return {
        "id": COMMENT_ID,
        "text": "说得好 <a href='#'>支持</a>",
        "created_at": RFC2822_TIME,
        "total_number": 3,
        "like_count": 5,
        "rootid": "parent_abc",
        "user": {
            "id": RAW_COMMENT_USER_ID,
            "screen_name": RAW_COMMENT_NICKNAME,
            "avatar_hd": "https://wx avatar.example.com/111222.jpg",
            "gender": "m",
            "profile_url": "https://m.weibo.cn/profile/111222",
            "description": "评论员签名",
            "ip_location": "广东",
        },
    }


# ----------------------------- FakeStore 捕获 -----------------------------

class _FakeStore:
    """捕获 store_content / store_comment 收到的 dict,不触发任何真实存储。"""

    def __init__(self):
        self.captured_content = {}
        self.captured_comment = {}

    async def store_content(self, content_item):
        self.captured_content.update(content_item)

    async def store_comment(self, comment_item):
        self.captured_comment.update(comment_item)

    async def store_creator(self, creator):
        pass


def _patch_factory(fake: "_FakeStore"):
    """把 store.weibo.WeibostoreFactory.create_store 替换为返回 fake 的静态方法,
    返回 (module, orig) 便于 finally 还原。"""
    import store.weibo as wb
    orig = wb.WeibostoreFactory.create_store
    wb.WeibostoreFactory.create_store = staticmethod(lambda: fake)
    return wb, orig


def _restore(wb, orig):
    wb.WeibostoreFactory.create_store = orig


# ----------------------------- 测试 -----------------------------

def test_weibo_note_masks_user_info():
    """note 拍平后的存储 dict 不含禁用键、creator_hash 不等于原始 user id、昵称已脱敏。"""
    import store.weibo as wb

    fake = _FakeStore()
    wb_, orig = _patch_factory(fake)
    try:
        asyncio.run(wb.update_weibo_note(make_mock_note()))
    finally:
        _restore(wb_, orig)

    captured = fake.captured_content
    assert captured, "FakeStore 未捕获到 note dict"

    # 1. 不含任何禁用字段键
    hit = set(captured.keys()) & FORBIDDEN_KEYS
    assert not hit, f"note 存储 dict 仍含禁用字段键: {hit}"

    # 2. creator_hash 存在、是 16 位 hex、不等于原始 user id
    creator_hash = captured.get("creator_hash")
    assert creator_hash, "note dict 缺少 creator_hash"
    assert creator_hash != str(RAW_USER_ID)
    assert creator_hash != RAW_USER_ID
    assert len(creator_hash) == 16

    # 3. 昵称已脱敏:不等于原文且含星号
    nickname = captured.get("nickname")
    assert nickname, "note dict 缺少 nickname"
    assert nickname != RAW_NICKNAME, "note 昵称未脱敏,仍为原文"
    assert "*" in nickname, f"note 昵称未脱敏: {nickname}"

    # 4. 内容字段正确(正文存于 content,不是 desc)
    assert "hello" not in captured  # 确认没误存
    assert "今天天气不错" in captured["content"]
    assert captured["note_id"] == NOTE_ID
    assert captured["liked_count"] == "10"
    assert captured["comments_count"] == "2"
    assert captured["shared_count"] == "1"


def test_weibo_comment_masks_user_info():
    """comment 拍平后的存储 dict 不含禁用键、creator_hash 不等于原始 user id、昵称已脱敏。"""
    import store.weibo as wb

    fake = _FakeStore()
    wb_, orig = _patch_factory(fake)
    try:
        asyncio.run(wb.update_weibo_note_comment(NOTE_ID, make_mock_comment()))
    finally:
        _restore(wb_, orig)

    captured = fake.captured_comment
    assert captured, "FakeStore 未捕获到 comment dict"

    # 1. 不含任何禁用字段键
    hit = set(captured.keys()) & FORBIDDEN_KEYS
    assert not hit, f"comment 存储字典仍含禁用字段键: {hit}"

    # 2. creator_hash 存在、不等于原始 user id
    creator_hash = captured.get("creator_hash")
    assert creator_hash, "comment dict 缺少 creator_hash"
    assert creator_hash != str(RAW_COMMENT_USER_ID)
    assert creator_hash != RAW_COMMENT_USER_ID
    assert len(creator_hash) == 16

    # 3. 昵称已脱敏
    nickname = captured.get("nickname")
    assert nickname, "comment dict 缺少 nickname"
    assert nickname != RAW_COMMENT_NICKNAME, "comment 昵称未脱敏,仍为原文"
    assert "*" in nickname, f"comment 昵称未脱敏: {nickname}"

    # 4. 内容字段正确
    assert "说得好" in captured["content"]
    assert captured["comment_id"] == COMMENT_ID
    assert captured["comment_like_count"] == "5"
    assert captured["sub_comment_count"] == "3"
    assert captured["parent_comment_id"] == "parent_abc"


def test_weibo_store_end_to_end_sqlite():
    """端到端:捕获 note/comment 的真实 dict,用 SQLite 内存库走完整 ORM 写入+查询。

    关键点:WeiboNote(**captured_dict) / WeiboNoteComment(**captured_dict) 会触发
    SQLAlchemy 声明式构造器的关键字校验——若 dict 含已删列(如 avatar/gender)会直接
    抛 TypeError。此处不抛异常即证明 dict 的 key 与删列后的 ORM 列完全对得上。
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import store.weibo as wb
    from database.models import Base, WeiboNote, WeiboNoteComment

    # ---- 1. 用 FakeStore 捕获 update_weibo_note / update_weibo_note_comment 产生的真实 dict ----
    fake = _FakeStore()
    wb_, orig = _patch_factory(fake)
    try:
        asyncio.run(wb.update_weibo_note(make_mock_note()))
        asyncio.run(wb.update_weibo_note_comment(NOTE_ID, make_mock_comment()))
    finally:
        _restore(wb_, orig)

    captured_note = dict(fake.captured_content)
    captured_comment = dict(fake.captured_comment)
    assert captured_note and captured_comment

    # ---- 2. SQLite 内存库,建 weibo 两张表 ----
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[WeiboNote.__table__, WeiboNoteComment.__table__])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # ---- 3. note:构造 ORM 对象(dict 多了已删列会直接 TypeError)并写入 ----
        note_obj = WeiboNote(**captured_note)  # 不抛异常 => key 与 ORM 列对得上
        session.add(note_obj)
        session.commit()

        row = session.query(WeiboNote).one()
        note_cols = {c.name for c in WeiboNote.__table__.columns}
        # 表结构层面无禁用列
        assert not (note_cols & FORBIDDEN_KEYS), \
            f"WeiboNote 表仍含禁用列: {note_cols & FORBIDDEN_KEYS}"
        # 行数据层面:creator_hash 正确、昵称脱敏、正文保留
        assert row.creator_hash and row.creator_hash != str(RAW_USER_ID)
        assert row.nickname != RAW_NICKNAME and "*" in row.nickname
        assert row.note_id == NOTE_ID
        assert "今天天气不错" in row.content
        # 确认没有 desc 列存任何用户描述
        assert "desc" not in note_cols

        # ---- 4. comment:同上。ID 已统一为字符串类型,create_time 保持 int ----
        cc = dict(captured_comment)
        cc["create_time"] = int(cc.get("create_time", 0) or 0)
        comment_obj = WeiboNoteComment(**cc)  # 不抛异常 => key 与 ORM 列对得上
        session.add(comment_obj)
        session.commit()

        crow = session.query(WeiboNoteComment).one()
        comment_cols = {c.name for c in WeiboNoteComment.__table__.columns}
        assert not (comment_cols & FORBIDDEN_KEYS), \
            f"WeiboNoteComment 表仍含禁用列: {comment_cols & FORBIDDEN_KEYS}"
        assert crow.creator_hash and crow.creator_hash != str(RAW_COMMENT_USER_ID)
        assert crow.nickname != RAW_COMMENT_NICKNAME and "*" in crow.nickname
        assert crow.comment_id == COMMENT_ID
        assert crow.note_id == NOTE_ID
        assert "说得好" in crow.content
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
