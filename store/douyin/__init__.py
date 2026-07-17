# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/douyin/__init__.py
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

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 18:46
# @Desc    :
from typing import Dict, List

import config
from var import source_keyword_var, crawler_type_var, run_id_var
from tools.user_hash import anonymize_user_id, mask_nickname
from tools.async_file_writer import AsyncFileWriter
from tools import utils

from ._store_impl import *
from .douyin_store_media import *


class DouyinStoreFactory:
    STORES = {
        "csv": DouyinCsvStoreImplement,
        "db": DouyinDbStoreImplement,
        "postgres": DouyinDbStoreImplement,
        "json": DouyinJsonStoreImplement,
        "jsonl": DouyinJsonlStoreImplement,
        "sqlite": DouyinSqliteStoreImplement,
        "mongodb": DouyinMongoStoreImplement,
        "excel": DouyinExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = DouyinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[DouyinStoreFactory.create_store] Invalid save option only supported csv or db or json or sqlite or mongodb or excel ...")
        return store_class()


def _extract_note_image_list(aweme_detail: Dict) -> List[str]:
    """
    Extract note image list

    Args:
        aweme_detail (Dict): Douyin content details

    Returns:
        List[str]: Note image list
    """
    images_res: List[str] = []
    images: List[Dict] = aweme_detail.get("images", [])

    if not images:
        return []

    for image in images:
        image_url_list = image.get("url_list", [])  # download_url_list has watermarked images, url_list has non-watermarked images
        if image_url_list:
            images_res.append(image_url_list[-1])

    return images_res


def _extract_comment_image_list(comment_item: Dict) -> List[str]:
    """
    Extract comment image list

    Args:
        comment_item (Dict): Douyin comment

    Returns:
        List[str]: Comment image list
    """
    images_res: List[str] = []
    image_list: List[Dict] = comment_item.get("image_list", [])

    if not image_list:
        return []

    for image in image_list:
        image_url_list = image.get("origin_url", {}).get("url_list", [])
        if image_url_list and len(image_url_list) > 1:
            images_res.append(image_url_list[1])

    return images_res


def _extract_content_cover_url(aweme_detail: Dict) -> str:
    """
    Extract video cover URL

    Args:
        aweme_detail (Dict): Douyin content details

    Returns:
        str: Video cover URL
    """
    res_cover_url = ""

    video_item = aweme_detail.get("video", {})
    raw_cover_url_list = (video_item.get("raw_cover", {}) or video_item.get("origin_cover", {})).get("url_list", [])
    if raw_cover_url_list and len(raw_cover_url_list) > 1:
        res_cover_url = raw_cover_url_list[1]

    return res_cover_url


def _extract_video_download_url(aweme_detail: Dict) -> str:
    """
    Extract video download URL

    Args:
        aweme_detail (Dict): Douyin video

    Returns:
        str: Video download URL
    """
    video_item = aweme_detail.get("video", {})
    url_h264_list = video_item.get("play_addr_h264", {}).get("url_list", [])
    url_256_list = video_item.get("play_addr_256", {}).get("url_list", [])
    url_list = video_item.get("play_addr", {}).get("url_list", [])
    actual_url_list = url_h264_list or url_256_list or url_list
    if not actual_url_list or len(actual_url_list) < 2:
        return ""
    return actual_url_list[-1]


def _extract_music_download_url(aweme_detail: Dict) -> str:
    """
    Extract music download URL.

    抖音 music.play_url 与 video.play_addr 同构:
    url_list 第一项常为空占位,真实地址在后面,取 [-1]。
    uri 字段在搜索接口返回里常为空,仅作兜底。

    Args:
        aweme_detail (Dict): Douyin video

    Returns:
        str: Music download URL
    """
    music_item = aweme_detail.get("music", {}) or {}
    play_url = music_item.get("play_url", {}) or {}
    url_list = play_url.get("url_list", []) or []
    if url_list:
        # 取最后一个非空项(url_list 第一项常为空占位)
        for url in reversed(url_list):
            if url:
                return url
        return url_list[-1]
    return play_url.get("uri", "")


def _extract_music_info(aweme_detail: Dict) -> Dict:
    """
    Extract BGM (background music) metadata from aweme detail.

    Args:
        aweme_detail (Dict): Douyin video detail

    Returns:
        Dict: {music_title, music_author, music_duration, music_cover_url, music_download_url}
    """
    music_item: Dict = aweme_detail.get("music", {}) or {}
    play_url = music_item.get("play_url", {}) or {}
    cover = music_item.get("cover_medium", {}) or {}
    cover_url_list = cover.get("url_list", []) or []
    return {
        "music_title": music_item.get("title", ""),
        "music_author": music_item.get("author", ""),
        "music_duration": music_item.get("duration", 0),  # seconds
        "music_cover_url": cover_url_list[-1] if cover_url_list else "",
        "music_download_url": _extract_music_download_url(aweme_detail),
    }


async def update_douyin_aweme(aweme_item: Dict):
    aweme_id = aweme_item.get("aweme_id")
    user_info = aweme_item.get("author", {})
    interact_info = aweme_item.get("statistics", {})
    _music_info = _extract_music_info(aweme_item)
    save_content_item = {
        "aweme_id": aweme_id,
        "aweme_type": str(aweme_item.get("aweme_type")),
        "title": aweme_item.get("desc", ""),
        "desc": aweme_item.get("desc", ""),
        "create_time": aweme_item.get("create_time"),
        "creator_hash": anonymize_user_id(user_info.get("uid")),  # 创作者匿名哈希(不存原始 uid)
        "nickname": mask_nickname(user_info.get("nickname")),  # 用户昵称(已脱敏)
        "liked_count": str(interact_info.get("digg_count")),
        "collected_count": str(interact_info.get("collect_count")),
        "comment_count": str(interact_info.get("comment_count")),
        "share_count": str(interact_info.get("share_count")),
        "last_modify_ts": utils.get_current_timestamp(),
        "aweme_url": f"https://www.douyin.com/video/{aweme_id}",
        "cover_url": _extract_content_cover_url(aweme_item),
        "video_download_url": _extract_video_download_url(aweme_item),
        "music_download_url": _music_info["music_download_url"],
        "music_title": _music_info["music_title"],
        "music_author": _music_info["music_author"],
        "music_duration": str(_music_info["music_duration"]),
        "music_cover_url": _music_info["music_cover_url"],
        "note_download_url": ",".join(_extract_note_image_list(aweme_item)),
        "source_keyword": source_keyword_var.get(),
        "run_id": run_id_var.get(),
    }
    utils.logger.info(f"[store.douyin.update_douyin_aweme] douyin aweme id:{aweme_id}, title:{save_content_item.get('title')}")
    await DouyinStoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_dy_aweme_comment(aweme_id, comment_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict):
    comment_aweme_id = comment_item.get("aweme_id")
    if aweme_id != comment_aweme_id:
        utils.logger.error(f"[store.douyin.update_dy_aweme_comment] comment_aweme_id: {comment_aweme_id} != aweme_id: {aweme_id}")
        return
    user_info = comment_item.get("user", {})
    comment_id = comment_item.get("cid")
    parent_comment_id = comment_item.get("reply_id", "0")
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "aweme_id": aweme_id,
        "content": comment_item.get("text"),
        "creator_hash": anonymize_user_id(user_info.get("uid")),  # 创作者匿名哈希(不存原始 uid)
        "nickname": mask_nickname(user_info.get("nickname")),  # 用户昵称(已脱敏)
        "sub_comment_count": str(comment_item.get("reply_comment_total", 0)),
        "like_count": (comment_item.get("digg_count") if comment_item.get("digg_count") else 0),
        "last_modify_ts": utils.get_current_timestamp(),
        "parent_comment_id": parent_comment_id,
        "pictures": ",".join(_extract_comment_image_list(comment_item)),
        "run_id": run_id_var.get(),
    }
    utils.logger.info(f"[store.douyin.update_dy_aweme_comment] douyin aweme comment: {comment_id}, content: {save_comment_item.get('content')}")

    await DouyinStoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def save_creator(user_id: str, creator: Dict):
    # 教学版：创作者个人资料(昵称/性别/头像/签名/IP/粉丝数等)不再落库，防骚扰。
    return


async def update_dy_aweme_image(aweme_id, pic_content, extension_file_name):
    """
    Update Douyin note image
    Args:
        aweme_id:
        pic_content:
        extension_file_name:

    Returns:

    """

    await DouYinImage().store_image({"aweme_id": aweme_id, "pic_content": pic_content, "extension_file_name": extension_file_name})


async def update_dy_aweme_video(aweme_id, video_content, extension_file_name):
    """
    Update Douyin short video
    Args:
        aweme_id:
        video_content:
        extension_file_name:

    Returns:

    """

    await DouYinVideo().store_video({"aweme_id": aweme_id, "video_content": video_content, "extension_file_name": extension_file_name})


async def update_dy_aweme_bgm(aweme_id: str, bgm_content: bytes, extension_file_name: str, bgm_meta: Dict):
    """
    Save Douyin aweme BGM audio file + append a row to bgm_playlist.jsonl

    Args:
        aweme_id: aweme id
        bgm_content: audio bytes
        extension_file_name: e.g. "bgm.m4a" or "bgm.mp3"
        bgm_meta: dict with keyword, aweme_url, video_download_url, music_title,
                  music_author, music_duration, music_url, bgm_source, local_path

    Returns:

    """
    # 1. Save audio file to disk
    await DouYinBGM().store_bgm({
        "aweme_id": aweme_id,
        "bgm_content": bgm_content,
        "extension_file_name": extension_file_name,
    })
    # 2. Append a row to bgm_playlist.jsonl
    playlist_item = {
        "keyword": bgm_meta.get("keyword", source_keyword_var.get()),
        "aweme_id": aweme_id,
        "aweme_url": bgm_meta.get("aweme_url", f"https://www.douyin.com/video/{aweme_id}"),
        "video_download_url": bgm_meta.get("video_download_url", ""),
        "music_title": bgm_meta.get("music_title", ""),
        "music_author": bgm_meta.get("music_author", ""),
        "music_duration": bgm_meta.get("music_duration", 0),
        "music_url": bgm_meta.get("music_url", ""),
        "bgm_source": bgm_meta.get("bgm_source", "primary_url"),
        "local_path": bgm_meta.get("local_path", ""),
        "add_ts": utils.get_current_timestamp(),
        "run_id": run_id_var.get(),
    }
    writer = AsyncFileWriter(platform="douyin", crawler_type=crawler_type_var.get())
    await writer.write_to_jsonl(item=playlist_item, item_type="bgm_playlist")
    utils.logger.info(f"[store.douyin.update_dy_aweme_bgm] bgm saved aweme_id={aweme_id} source={playlist_item['bgm_source']}")
