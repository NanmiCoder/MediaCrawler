# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
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

from typing import Dict, List

import config
from tools import utils

from ._store_impl import (
    XhhCsvStoreImplement,
    XhhJsonStoreImplement,
    XhhJsonlStoreImplement,
)
from .xhh_store_media import XiaoHeiHeImage, XiaoHeiHeVideo


class XhhStoreFactory:
    STORES = {
        "csv": XhhCsvStoreImplement,
        "json": XhhJsonStoreImplement,
        "jsonl": XhhJsonlStoreImplement,
    }

    @staticmethod
    def create_store():
        store_class = XhhStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            store_class = XhhJsonlStoreImplement
        return store_class()


async def update_xhh_post(post_item: Dict):
    """Store xiaoheihe post data"""
    utils.logger.info(
        f"[store.xhh.update_xhh_post] Storing post link_id={post_item.get('link_id')}"
    )
    await XhhStoreFactory.create_store().store_content(post_item)


async def batch_update_xhh_post_comments(link_id: str, comments: List[Dict]):
    """Batch store xiaoheihe post comments"""
    if not comments:
        return
    for comment_item in comments:
        await update_xhh_post_comment(link_id, comment_item)


async def update_xhh_post_comment(link_id: str, comment_item: Dict):
    """Store a single xiaoheihe comment

    小黑盒评论结构（来自 /bbs/app/link/tree result.comments[].comment[]）：
    - commentid, userid, create_at, text, ip_location
    - up（点赞数）, child_num（子评论数）, floor_num（楼层）
    - user.username, user.avatar
    - replyid（父评论 id，二级评论才有）
    """
    user_info = comment_item.get("user", {})
    local_db_item = {
        "comment_id": str(comment_item.get("commentid", "")),
        "link_id": str(link_id),
        "content": comment_item.get("text", ""),
        "create_time": str(comment_item.get("create_at", 0)),
        "ip_location": comment_item.get("ip_location", ""),
        "user_id": str(user_info.get("userid", "")),
        "nickname": user_info.get("username", ""),
        "avatar": user_info.get("avatar", ""),
        "like_count": str(comment_item.get("up", 0)),
        "sub_comment_count": str(comment_item.get("child_num", 0)),
        "parent_comment_id": str(comment_item.get("replyid", 0)),
        "last_modify_ts": str(utils.get_current_timestamp()),
    }
    utils.logger.info(
        f"[store.xhh.update_xhh_post_comment] comment_id={local_db_item['comment_id']}"
    )
    await XhhStoreFactory.create_store().store_comment(local_db_item)


async def update_xhh_creator(creator_item: Dict):
    """Store xiaoheihe creator data

    小黑盒创作者结构（来自 /bbs/app/profile/user/profile result.account_detail）：
    - userid, username, avatar, signature, ip_location
    - bbs_info.follow_num, bbs_info.be_favoured_num, bbs_info.post_link_num
    """
    bbs_info = creator_item.get("bbs_info", {})
    local_db_item = {
        "user_id": str(creator_item.get("userid", "")),
        "nickname": creator_item.get("username", ""),
        "avatar": creator_item.get("avatar", ""),
        "desc": creator_item.get("signature", ""),
        "ip_location": creator_item.get("ip_location", ""),
        "follows": str(bbs_info.get("follow_num", 0)),
        "fans": str(bbs_info.get("be_favoured_num", 0)),
        "post_count": str(bbs_info.get("post_link_num", 0)),
        "last_modify_ts": str(utils.get_current_timestamp()),
    }
    utils.logger.info(
        f"[store.xhh.update_xhh_creator] user_id={local_db_item['user_id']}"
    )
    await XhhStoreFactory.create_store().store_creator(local_db_item)


async def update_xhh_post_image(link_id: str, pic_content: bytes, extension_file_name: str):
    """Save a post image to local storage (data/xhh/images/<link_id>/)"""
    await XiaoHeiHeImage().store_image({
        "notice_id": link_id,
        "pic_content": pic_content,
        "extension_file_name": extension_file_name,
    })


async def update_xhh_post_video(link_id: str, video_content: bytes, extension_file_name: str):
    """Save a post video to local storage (data/xhh/videos/<link_id>/)"""
    await XiaoHeiHeVideo().store_video({
        "notice_id": link_id,
        "video_content": video_content,
        "extension_file_name": extension_file_name,
    })
