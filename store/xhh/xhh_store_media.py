# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
import config


class XiaoHeiHeImage(AbstractStoreImage):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.image_store_path = f"{config.SAVE_DATA_PATH}/xhh/images"
        else:
            self.image_store_path = "data/xhh/images"

    async def store_image(self, image_content_item: Dict):
        await self.save_image(
            image_content_item.get("notice_id"),
            image_content_item.get("pic_content"),
            image_content_item.get("extension_file_name"),
        )

    def make_save_file_name(self, notice_id: str, extension_file_name: str) -> str:
        return f"{self.image_store_path}/{notice_id}/{extension_file_name}"

    async def save_image(self, notice_id: str, pic_content: bytes, extension_file_name: str):
        pathlib.Path(f"{self.image_store_path}/{notice_id}").mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(notice_id, extension_file_name)
        async with aiofiles.open(save_file_name, "wb") as f:
            await f.write(pic_content)
        utils.logger.info(
            f"[XiaoHeiHeImage.save_image] Saved image {save_file_name}"
        )


class XiaoHeiHeVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/xhh/videos"
        else:
            self.video_store_path = "data/xhh/videos"

    async def store_video(self, video_content_item: Dict):
        await self.save_video(
            video_content_item.get("notice_id"),
            video_content_item.get("video_content"),
            video_content_item.get("extension_file_name"),
        )

    def make_save_file_name(self, notice_id: str, extension_file_name: str) -> str:
        return f"{self.video_store_path}/{notice_id}/{extension_file_name}"

    async def save_video(self, notice_id: str, video_content: bytes, extension_file_name: str):
        pathlib.Path(f"{self.video_store_path}/{notice_id}").mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(notice_id, extension_file_name)
        async with aiofiles.open(save_file_name, "wb") as f:
            await f.write(video_content)
        utils.logger.info(
            f"[XiaoHeiHeVideo.save_video] Saved video {save_file_name}"
        )
