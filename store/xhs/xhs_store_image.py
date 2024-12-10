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
