# -*- coding: utf-8 -*-
# @Author  : helloteemo
# @Time    : 2024/7/11 22:35
# @Desc    : 小红书图片保存
import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage
from tools import utils


class XiaoHongShuImage(AbstractStoreImage):
    image_store_path: str = "data/xhs/images"

    async def store_image(self, image_content_item: Dict):
        """
        store content
        Args:
            content_item:

        Returns:

        """
        await self.save_image(image_content_item.get("notice_id"), image_content_item.get("pic_content"),
                              image_content_item.get("extension_file_name"))

    def make_save_file_name(self, notice_id: str, extension_file_name: str) -> str:
        """
        make save file name by store type
        Args:
            notice_id: notice id
            picid: image id

        Returns:

        """
        return f"{self.image_store_path}/{notice_id}/{extension_file_name}"

    async def save_image(self, notice_id: str, pic_content: str, extension_file_name="jpg"):
        """
        save image to local
        Args:
            notice_id: notice id
            pic_content: image content

        Returns:

        """
        pathlib.Path(self.image_store_path + "/" + notice_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(notice_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[XiaoHongShuImageStoreImplement.save_image] save image {save_file_name} success ...")
