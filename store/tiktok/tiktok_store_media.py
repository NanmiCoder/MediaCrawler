# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/tiktok/tiktok_store_media.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习 and 研究目的使用。使用者应遵守以下原则：
# 1. 不得用于 any 商业用途。
# 2. 使用时应遵守目标平台的使用条款 and robots.txt规则。
# 3. 不得进行大规模爬取 or 对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于 any 非法 or 不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则 and LICENSE中的所有条款。

import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
import config


class TikTokImage(AbstractStoreImage):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.image_store_path = f"{config.SAVE_DATA_PATH}/tiktok/images"
        else:
            self.image_store_path = "data/tiktok/images"

    async def store_image(self, image_content_item: Dict):
        """
        store content

        Args:
            image_content_item:

        Returns:

        """
        await self.save_image(image_content_item.get("aweme_id"), image_content_item.get("pic_content"), image_content_item.get("extension_file_name"))

    def make_save_file_name(self, aweme_id: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            aweme_id: aweme id
            extension_file_name: image filename with extension

        Returns:

        """
        return f"{self.image_store_path}/{aweme_id}/{extension_file_name}"

    async def save_image(self, aweme_id: str, pic_content: bytes, extension_file_name: str):
        """
        save image to local

        Args:
            aweme_id: aweme id
            pic_content: image content (bytes)
            extension_file_name: image filename with extension

        Returns:

        """
        pathlib.Path(self.image_store_path + "/" + aweme_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(aweme_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[TikTokImageStoreImplement.save_image] save image {save_file_name} success ...")


class TikTokVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/tiktok/videos"
        else:
            self.video_store_path = "data/tiktok/videos"

    async def store_video(self, video_content_item: Dict):
        """
        store content

        Args:
            video_content_item:

        Returns:

        """
        await self.save_video(video_content_item.get("aweme_id"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"))

    def make_save_file_name(self, aweme_id: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            aweme_id: aweme id
            extension_file_name: video filename with extension

        Returns:

        """
        return f"{self.video_store_path}/{aweme_id}/{extension_file_name}"

    async def save_video(self, aweme_id: str, video_content: bytes, extension_file_name: str):
        """
        save video to local

        Args:
            aweme_id: aweme id
            video_content: video content (bytes)
            extension_file_name: video filename with extension

        Returns:

        """
        pathlib.Path(self.video_store_path + "/" + aweme_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(aweme_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(video_content)
            utils.logger.info(f"[TikTokVideoStoreImplement.save_video] save video {save_file_name} success ...")
