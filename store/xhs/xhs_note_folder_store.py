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
# @Author  : GitHub Copilot
# @Time    : 2025/8/16
# @Desc    : 小红书按笔记文件夹存储实现类

import asyncio
import json
import pathlib
from datetime import datetime
from typing import Dict

import aiofiles

import config
from base.base_crawler import AbstractStore, AbstractStoreImage, AbstractStoreVideo
from tools import utils
from var import source_keyword_var


class XhsNoteFolderStoreImplement(AbstractStore):
    """
    小红书按笔记文件夹存储实现
    目录结构：data/xhs/keyword/{发布日期_发布时间_笔记ID}/
    每个笔记文件夹包含：
    - note_info.json (笔记基本信息)
    - comments.json (评论信息)
    - images/ (图片文件夹，如果有图片)
    - videos/ (视频文件夹，如果有视频)
    """
    
    base_store_path: str = "data/xhs"
    
    def get_keyword_folder(self, content_item: Dict = None) -> str:
        """
        获取当前搜索关键词文件夹
        Returns:
            关键词文件夹名称
        """
        # 简化：直接从命令参数（config.KEYWORDS）获取第一个关键词
        keywords_str = getattr(config, 'KEYWORDS', '') or ''
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        if not keywords_list:
            raise ValueError("[XhsNoteFolderStore.get_keyword_folder] --keywords is required for search and must not be empty")
        keyword = utils.replaceT(keywords_list[0])
        return keyword
    
    def make_note_folder_path(self, note_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        创建笔记文件夹路径
        格式：data/xhs/keyword/{发布日期_发布时间_笔记ID}/
        Args:
            note_id: 笔记ID
            publish_time: 发布时间戳，如果提供则使用，否则使用当前时间
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        keyword_folder = self.get_keyword_folder(content_item)
        
        if publish_time:
            try:
                # 尝试处理不同格式的时间戳
                if publish_time > 9999999999:  # 如果是毫秒级时间戳
                    publish_time = publish_time / 1000
                dt = datetime.fromtimestamp(publish_time)
                date_time_str = dt.strftime("%Y%m%d_%H%M%S")
            except (OSError, ValueError, OverflowError) as e:
                # 如果时间戳无效，使用当前时间
                utils.logger.warning(f"[XhsNoteFolderStore.make_note_folder_path] Invalid publish_time {publish_time}, using current time. Error: {e}")
                now = datetime.now()
                date_time_str = now.strftime("%Y%m%d_%H%M%S")
        else:
            now = datetime.now()
            date_time_str = now.strftime("%Y%m%d_%H%M%S")

        folder_name = f"{date_time_str}_{note_id}"
        return f"{self.base_store_path}/{keyword_folder}/{folder_name}"
    
    def get_existing_note_folder(self, note_id: str, content_item: Dict = None) -> str:
        """
        查找是否已存在该笔记的文件夹
        Args:
            note_id: 笔记ID
        Returns:
            已存在的文件夹路径，如果不存在返回None
        """
        import os
        
        keyword_folder = self.get_keyword_folder(content_item)
        keyword_path = f"{self.base_store_path}/{keyword_folder}"
        
        if not os.path.exists(keyword_path):
            return None
            
        for folder_name in os.listdir(keyword_path):
            if folder_name.endswith(f"_{note_id}"):
                return f"{keyword_path}/{folder_name}"
        return None
    
    def get_or_create_note_folder(self, note_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        获取或创建笔记文件夹
        Args:
            note_id: 笔记ID
            publish_time: 发布时间戳
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        existing_folder = self.get_existing_note_folder(note_id, content_item)
        if existing_folder:
            return existing_folder
        
        new_folder = self.make_note_folder_path(note_id, publish_time, content_item)
        pathlib.Path(new_folder).mkdir(parents=True, exist_ok=True)
        return new_folder
    
    async def store_content(self, content_item: Dict):
        """
        存储笔记内容信息
        Args:
            content_item: 笔记内容信息
        """
        note_id = content_item.get("note_id")
        if not note_id:
            utils.logger.error("[XhsNoteFolderStore.store_content] note_id is required")
            return
        
        # 获取发布时间
        publish_time = content_item.get("time")

        # 获取或创建笔记文件夹
        note_folder = self.get_or_create_note_folder(note_id, publish_time, content_item)
        
        # 保存笔记信息到 note_info.json
        note_info_file = f"{note_folder}/note_info.json"
        
        # 添加时间戳
        content_item["add_ts"] = utils.get_current_timestamp()
        content_item["save_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with aiofiles.open(note_info_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(content_item, ensure_ascii=False, indent=4))
        
        utils.logger.info(f"[XhsNoteFolderStore.store_content] Saved note info: {note_info_file}")
    
    async def store_comment(self, comment_item: Dict):
        """
        存储评论信息
        Args:
            comment_item: 评论信息
        """
        note_id = comment_item.get("note_id")
        if not note_id:
            utils.logger.error("[XhsNoteFolderStore.store_comment] note_id is required")
            return

        # 获取或创建笔记文件夹
        note_folder = self.get_or_create_note_folder(note_id, None, comment_item)
        
        # 评论文件路径
        comments_file = f"{note_folder}/comments.json"
        
        # 读取现有评论
        comments_data = []
        try:
            if pathlib.Path(comments_file).exists():
                async with aiofiles.open(comments_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        comments_data = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            utils.logger.warning(f"[XhsNoteFolderStore.store_comment] Error reading existing comments: {e}")
            comments_data = []
        
        # 添加时间戳
        comment_item["add_ts"] = utils.get_current_timestamp()
        comment_item["save_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查评论是否已存在（防重复）
        comment_id = comment_item.get("comment_id")
        if comment_id:
            existing_comment = next((c for c in comments_data if c.get("comment_id") == comment_id), None)
            if existing_comment:
                # 更新现有评论
                comments_data = [c if c.get("comment_id") != comment_id else comment_item for c in comments_data]
            else:
                # 添加新评论
                comments_data.append(comment_item)
        else:
            # 没有comment_id，直接添加
            comments_data.append(comment_item)
        
        # 保存评论数据
        async with aiofiles.open(comments_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(comments_data, ensure_ascii=False, indent=4))
        
        if getattr(config, "ENABLE_COMMENT_LOG", True):
            utils.logger.info(f"[XhsNoteFolderStore.store_comment] Saved comment to: {comments_file}")
    
    async def store_creator(self, creator: Dict):
        """
        存储创作者信息（创作者信息现在包含在笔记基本信息中，无需单独存储）
        Args:
            creator: 创作者信息
        """
        # 创作者信息现在包含在笔记基本信息中，不需要单独存储
        # 这个方法保留是为了兼容接口，但不执行任何操作
        utils.logger.info(f"[XhsNoteFolderStore.store_creator] Creator info will be stored with note info, skipping separate storage")


class XhsNoteFolderImageStore(AbstractStoreImage):
    """
    小红书图片文件存储实现
    将图片文件存储到对应的笔记文件夹中
    """
    
    base_store_path: str = "data/xhs"
    
    def get_keyword_folder(self, content_item: Dict = None) -> str:
        """
        获取当前搜索关键词文件夹
        Returns:
            关键词文件夹名称
        """
        keywords_str = getattr(config, 'KEYWORDS', '') or ''
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        if not keywords_list:
            raise ValueError("[XhsNoteFolderImageStore.get_keyword_folder] --keywords is required for search and must not be empty")
        return utils.replaceT(keywords_list[0])
    
    def get_existing_note_folder(self, note_id: str, content_item: Dict = None) -> str:
        """
        查找是否已存在该笔记的文件夹
        Args:
            note_id: 笔记ID
        Returns:
            已存在的文件夹路径，如果不存在返回None
        """
        import os
        
        keyword_folder = self.get_keyword_folder(content_item)
        keyword_path = f"{self.base_store_path}/{keyword_folder}"
        
        if not os.path.exists(keyword_path):
            return None
            
        for folder_name in os.listdir(keyword_path):
            if folder_name.endswith(f"_{note_id}"):
                return f"{keyword_path}/{folder_name}"
        return None
    
    def make_note_folder_path(self, note_id: str, content_item: Dict = None) -> str:
        """
        创建笔记文件夹路径
        Args:
            note_id: 笔记ID
        Returns:
            文件夹路径
        """
        keyword_folder = self.get_keyword_folder(content_item)
        now = datetime.now()
        date_time_str = now.strftime("%Y%m%d_%H%M%S")
        folder_name = f"{date_time_str}_{note_id}"
        return f"{self.base_store_path}/{keyword_folder}/{folder_name}"
    
    def get_or_create_note_folder(self, note_id: str, content_item: Dict = None) -> str:
        """
        获取或创建笔记文件夹
        Args:
            note_id: 笔记ID
        Returns:
            文件夹路径
        """
        existing_folder = self.get_existing_note_folder(note_id, content_item)
        if existing_folder:
            return existing_folder
        
        new_folder = self.make_note_folder_path(note_id, content_item)
        pathlib.Path(new_folder).mkdir(parents=True, exist_ok=True)
        return new_folder
    
    async def store_image(self, image_content_item: Dict):
        """
        存储图片文件
        Args:
            image_content_item: 包含notice_id, pic_content, extension_file_name的字典
        """
        note_id = image_content_item.get("notice_id")
        pic_content = image_content_item.get("pic_content")
        extension_file_name = image_content_item.get("extension_file_name")
        
        if not note_id or not pic_content:
            utils.logger.error("[XhsNoteFolderImageStore.store_image] notice_id and pic_content are required")
            return

        # 获取或创建笔记文件夹
        note_folder = self.get_or_create_note_folder(note_id, image_content_item)
        
        # 创建images子文件夹
        images_folder = f"{note_folder}/images"
        pathlib.Path(images_folder).mkdir(parents=True, exist_ok=True)
        
        # 保存图片文件
        image_file_path = f"{images_folder}/{extension_file_name}"
        
        async with aiofiles.open(image_file_path, 'wb') as f:
            await f.write(pic_content)
        
        utils.logger.info(f"[XhsNoteFolderImageStore.store_image] Saved image: {image_file_path}")


class XhsNoteFolderVideoStore(AbstractStoreVideo):
    """
    小红书视频文件存储实现
    将视频文件存储到对应的笔记文件夹中
    """
    
    base_store_path: str = "data/xhs"
    
    def get_keyword_folder(self, content_item: Dict = None) -> str:
        """
        获取当前搜索关键词文件夹
        Returns:
            关键词文件夹名称
        """
        keywords_str = getattr(config, 'KEYWORDS', '') or ''
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        if not keywords_list:
            raise ValueError("[XhsNoteFolderVideoStore.get_keyword_folder] --keywords is required for search and must not be empty")
        return utils.replaceT(keywords_list[0])
    
    def get_existing_note_folder(self, note_id: str, content_item: Dict = None) -> str:
        """
        查找是否已存在该笔记的文件夹
        Args:
            note_id: 笔记ID
        Returns:
            已存在的文件夹路径，如果不存在返回None
        """
        import os
        
        keyword_folder = self.get_keyword_folder(content_item)
        keyword_path = f"{self.base_store_path}/{keyword_folder}"
        
        if not os.path.exists(keyword_path):
            return None
            
        for folder_name in os.listdir(keyword_path):
            if folder_name.endswith(f"_{note_id}"):
                return f"{keyword_path}/{folder_name}"
        return None
    
    def make_note_folder_path(self, note_id: str, content_item: Dict = None) -> str:
        """
        创建笔记文件夹路径
        Args:
            note_id: 笔记ID
        Returns:
            文件夹路径
        """
        keyword_folder = self.get_keyword_folder(content_item)
        now = datetime.now()
        date_time_str = now.strftime("%Y%m%d_%H%M%S")
        folder_name = f"{date_time_str}_{note_id}"
        return f"{self.base_store_path}/{keyword_folder}/{folder_name}"
    
    def get_or_create_note_folder(self, note_id: str, content_item: Dict = None) -> str:
        """
        获取或创建笔记文件夹
        Args:
            note_id: 笔记ID
        Returns:
            文件夹路径
        """
        existing_folder = self.get_existing_note_folder(note_id, content_item)
        if existing_folder:
            return existing_folder
        
        new_folder = self.make_note_folder_path(note_id, content_item)
        pathlib.Path(new_folder).mkdir(parents=True, exist_ok=True)
        return new_folder
    
    async def store_video(self, video_content_item: Dict):
        """
        存储视频文件
        Args:
            video_content_item: 包含notice_id, video_content, extension_file_name的字典
        """
        note_id = video_content_item.get("notice_id")
        video_content = video_content_item.get("video_content")
        extension_file_name = video_content_item.get("extension_file_name")
        
        if not note_id or not video_content:
            utils.logger.error("[XhsNoteFolderVideoStore.store_video] notice_id and video_content are required")
            return

        # 获取或创建笔记文件夹
        note_folder = self.get_or_create_note_folder(note_id, video_content_item)
        
        # 创建videos子文件夹
        videos_folder = f"{note_folder}/videos"
        pathlib.Path(videos_folder).mkdir(parents=True, exist_ok=True)
        
        # 保存视频文件
        video_file_path = f"{videos_folder}/{extension_file_name}"
        
        async with aiofiles.open(video_file_path, 'wb') as f:
            await f.write(video_content)
        
        utils.logger.info(f"[XhsNoteFolderVideoStore.store_video] Saved video: {video_file_path}")
