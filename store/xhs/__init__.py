# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/1/14 17:34
# @Desc    :
from typing import List

import config
import aiohttp
import os
import aiohttp
import asyncio
import logging

from . import xhs_store_impl
from .xhs_store_impl import *


class XhsStoreFactory:
    STORES = {
        "csv": XhsCsvStoreImplement,
        "db": XhsDbStoreImplement,
        "json": XhsJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = XhsStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[XhsStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


logging.basicConfig(level=logging.INFO)
async def download_image(url, save_path, retries=3):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(save_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)
                        logging.info(f"图片下载成功: {save_path}")
                        break  # 如果下载成功，跳出重试循环
                    else:
                        raise Exception(f"下载图片失败: {response.status}")
        except (aiohttp.ClientError, aiohttp.client_exceptions.ClientPayloadError) as e:
            if attempt == retries - 1:
                logging.error(f"下载图片失败: {e}")
                raise e  # 如果已经是最后一次重试，抛出异常
            await asyncio.sleep(2 ** attempt)  # 指数退避策略
            logging.warning(f"重试下载图片 ({attempt + 1}/{retries}): {url}")
        except Exception as e:
            logging.error(f"下载图片失败: {e}")
            raise e

async def download_video(url, save_path, retries=3):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # 确保目录存在
                        directory = os.path.dirname(save_path)
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                        async with aiofiles.open(save_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)
                    else:
                        raise Exception(f"下载视频失败: {response.status}")
            break  # 如果下载成功，跳出重试循环
        except aiohttp.client_exceptions.ClientPayloadError as e:
            if attempt == retries - 1:
                raise e  # 如果已经是最后一次重试，抛出异常
            await asyncio.sleep(2 ** attempt)  # 指数退避策略

async def update_xhs_note(note_item: Dict):
    note_id = note_item.get("note_id")
    user_info = note_item.get("user", {})
    user_id = user_info.get("user_id")
    interact_info = note_item.get("interact_info", {})
    image_list: List[Dict] = note_item.get("image_list", [])
    tag_list: List[Dict] = note_item.get("tag_list", [])

    video_url = ''
    if note_item.get('type') == 'video':
        videos = note_item.get('video').get('media').get('stream').get('h264')
        if type(videos).__name__ == 'list':
            video_url = ','.join([v.get('master_url') for v in videos])

    local_db_item = {
        "note_id": note_item.get("note_id"),
        "type": note_item.get("type"),
        "title": note_item.get("title") or note_item.get("desc", "")[:255],
        "desc": note_item.get("desc", ""),
        "video_url": video_url,
        "time": note_item.get("time"),
        "last_update_time": note_item.get("last_update_time", 0),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("avatar"),
        "liked_count": interact_info.get("liked_count"),
        "collected_count": interact_info.get("collected_count"),
        "comment_count": interact_info.get("comment_count"),
        "share_count": interact_info.get("share_count"),
        "ip_location": note_item.get("ip_location", ""),
        "image_list": ','.join([img.get('url', '') for img in image_list]),
        "tag_list": ','.join([tag.get('name', '') for tag in tag_list if tag.get('type') == 'topic']),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": f"https://www.xiaohongshu.com/explore/{note_id}"
    }
    utils.logger.info(f"[store.xhs.update_xhs_note] xhs note: {local_db_item}")

    # 下载视频
    if video_url:
        video_urls = video_url.split(',')
        for idx, url in enumerate(video_urls):
            save_path = f"data/xhs/videos/{user_id}/{note_id}_{idx}.mp4"
            await download_video(url, save_path)
            utils.logger.info(f"视屏下载到的地址: {save_path}")

    # 下载图片
    if image_list:
        note_images_dir = f"data/xhs/images/{user_id}/{note_id}"
        if not os.path.exists(note_images_dir):
            os.makedirs(note_images_dir)
        for idx, img in enumerate(image_list):
            img_url = img.get('url', '')
            if img_url:
                save_path = f"{note_images_dir}/{idx}.jpg"
                await download_image(img_url, save_path)
                utils.logger.info(f"图片下载到的地址: {save_path}")

    await XhsStoreFactory.create_store().store_content(local_db_item)


async def batch_update_xhs_note_comments(note_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_xhs_note_comment(note_id, comment_item)


async def update_xhs_note_comment(note_id: str, comment_item: Dict):
    user_info = comment_item.get("user_info", {})
    comment_id = comment_item.get("id")
    comment_pictures = [item.get("url_default", "") for item in comment_item.get("pictures", [])]
    target_comment = comment_item.get("target_comment", {})
    local_db_item = {
        "comment_id": comment_id,
        "create_time": comment_item.get("create_time"),
        "ip_location": comment_item.get("ip_location"),
        "note_id": note_id,
        "content": comment_item.get("content"),
        "user_id": user_info.get("user_id"),
        "nickname": user_info.get("nickname"),
        "avatar": user_info.get("image"),
        "sub_comment_count": comment_item.get("sub_comment_count", 0),
        "pictures": ",".join(comment_pictures),
        "parent_comment_id": target_comment.get("id", 0),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.xhs.update_xhs_note_comment] xhs note comment:{local_db_item}")
    await XhsStoreFactory.create_store().store_comment(local_db_item)


async def save_creator(user_id: str, creator: Dict):
    user_info = creator.get('basicInfo', {})

    follows = 0
    fans = 0
    interaction = 0
    for i in creator.get('interactions'):
        if i.get('type') == 'follows':
            follows = i.get('count')
        elif i.get('type') == 'fans':
            fans = i.get('count')
        elif i.get('type') == 'interaction':
            interaction = i.get('count')

    local_db_item = {
        'user_id': user_id,
        'nickname': user_info.get('nickname'),
        'gender': '女' if user_info.get('gender') == 1 else '男',
        'avatar': user_info.get('images'),
        'desc': user_info.get('desc'),
        'ip_location': user_info.get('ipLocation'),
        'follows': follows,
        'fans': fans,
        'interaction': interaction,
        'tag_list': json.dumps({tag.get('tagType'): tag.get('name') for tag in creator.get('tags')},
                               ensure_ascii=False),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.xhs.save_creator] creator:{local_db_item}")
    await XhsStoreFactory.create_store().store_creator(local_db_item)
