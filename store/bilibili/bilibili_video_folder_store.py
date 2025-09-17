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
# @Author  : ZZZ
# @Time    : 2025/8/8
# @Desc    : B站按视频文件夹存储实现类

import asyncio
import json
import pathlib
from datetime import datetime
from typing import Dict

import aiofiles

import config
from base.base_crawler import AbstractStore, AbstractStoreVideo
from tools import utils
from var import source_keyword_var


class BiliVideoFolderStoreImplement(AbstractStore):
    """
    B站按视频文件夹存储实现
    目录结构：data/bilibili/keyword/{视频发布日期_视频发布时间_视频ID}/
    每个视频文件夹包含：
    - video_info.json (视频基本信息)
    - comments.json (评论信息)
    - video.mp4 (视频文件，如果开启媒体下载)
    - images/ (图片文件夹，如果有图片)
    """
    
    base_store_path: str = "data/bilibili"
    
    def get_keyword_folder(self, content_item: Dict = None) -> str:
        """
        获取当前搜索关键词文件夹
        Args:
            content_item: 内容项，可能包含source_keyword字段
        Returns:
            关键词文件夹名称
        """
        # 简化：直接从命令参数（config.KEYWORDS）获取第一个关键词
        keywords_str = getattr(config, 'KEYWORDS', '') or ''
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        if not keywords_list:
            raise ValueError("[BiliVideoFolderStore.get_keyword_folder] --keywords is required for search and must not be empty")
        return utils.replaceT(keywords_list[0])
    
    def make_video_folder_path(self, video_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        创建视频文件夹路径
        格式：data/bilibili/keyword/{视频发布日期_视频发布时间_视频ID}/
        Args:
            video_id: 视频ID
            publish_time: 视频发布时间戳（秒）
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        keyword_folder = self.get_keyword_folder(content_item)
        
        if publish_time:
            # 使用视频发布时间
            publish_datetime = datetime.fromtimestamp(publish_time)
            date_time_str = publish_datetime.strftime("%Y%m%d_%H%M%S")
        else:
            # 如果没有发布时间，使用当前时间作为备选
            now = datetime.now()
            date_time_str = now.strftime("%Y%m%d_%H%M%S")
        
        folder_name = f"{date_time_str}_{video_id}"
        return f"{self.base_store_path}/{keyword_folder}/{folder_name}"
    
    def get_existing_video_folder(self, video_id: str, content_item: Dict = None) -> str:
        """
        查找是否已存在该视频的文件夹
        Args:
            video_id: 视频ID
            content_item: 内容项，用于获取关键词
        Returns:
            已存在的文件夹路径，如果不存在返回None
        """
        import os
        
        keyword_folder = self.get_keyword_folder(content_item)
        keyword_path = f"{self.base_store_path}/{keyword_folder}"
        
        if not os.path.exists(keyword_path):
            return None
            
        for folder_name in os.listdir(keyword_path):
            if folder_name.endswith(f"_{video_id}"):
                return f"{keyword_path}/{folder_name}"
        return None
    
    def get_or_create_video_folder(self, video_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        获取或创建视频文件夹
        Args:
            video_id: 视频ID
            publish_time: 视频发布时间戳（秒）
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        existing_folder = self.get_existing_video_folder(video_id, content_item)
        if existing_folder:
            return existing_folder
        
        new_folder = self.make_video_folder_path(video_id, publish_time, content_item)
        pathlib.Path(new_folder).mkdir(parents=True, exist_ok=True)
        return new_folder
    
    async def store_content(self, content_item: Dict):
        """
        存储视频内容信息
        Args:
            content_item: 视频内容信息
        """
        video_id = content_item.get("video_id")
        if not video_id:
            utils.logger.error("[BiliVideoFolderStore.store_content] video_id is required")
            return
        
        # 获取视频发布时间
        publish_time = content_item.get("create_time")
        
        # 获取或创建视频文件夹
        video_folder = self.get_or_create_video_folder(video_id, publish_time, content_item)
        
        # 保存视频信息到 video_info.json
        video_info_file = f"{video_folder}/video_info.json"
        
        # 添加时间戳
        content_item["add_ts"] = utils.get_current_timestamp()
        content_item["save_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with aiofiles.open(video_info_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(content_item, ensure_ascii=False, indent=4))
        
        utils.logger.info(f"[BiliVideoFolderStore.store_content] Saved video info: {video_info_file}")
    
    async def store_comment(self, comment_item: Dict):
        """
        存储评论信息
        Args:
            comment_item: 评论信息
        """
        # 从评论中获取视频ID（可能需要根据实际的评论数据结构调整）
        video_id = comment_item.get("video_id") or comment_item.get("oid")
        if not video_id:
            utils.logger.error("[BiliVideoFolderStore.store_comment] video_id is required")
            return
        
        # 获取或创建视频文件夹（评论存储时不传递发布时间，因为可能不可用）
        video_folder = self.get_or_create_video_folder(str(video_id), None, comment_item)
        
        # 评论文件路径
        comments_file = f"{video_folder}/comments.json"
        
        # 读取现有评论
        comments_data = []
        try:
            if pathlib.Path(comments_file).exists():
                async with aiofiles.open(comments_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        comments_data = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            utils.logger.warning(f"[BiliVideoFolderStore.store_comment] Error reading existing comments: {e}")
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
            utils.logger.info(f"[BiliVideoFolderStore.store_comment] Saved comment to: {comments_file}")
    
    async def store_creator(self, creator: Dict):
        """
        存储创作者信息（将包含在视频信息中，无需单独存储）
        Args:
            creator: 创作者信息
        """
        # 创作者信息现在包含在视频基本信息中，不需要单独存储
        # 这个方法保留是为了兼容接口，但不执行任何操作
        utils.logger.info(f"[BiliVideoFolderStore.store_creator] Creator info will be stored with video info, skipping separate storage")


class BiliVideoFolderMediaStore(AbstractStoreVideo):
    """
    B站视频文件存储实现
    将视频文件存储到对应的视频文件夹中
    """
    
    base_store_path: str = "data/bilibili"
    
    def get_keyword_folder(self, content_item: Dict = None) -> str:
        """
        获取当前搜索关键词文件夹
        Args:
            content_item: 内容项，可能包含source_keyword字段
        Returns:
            关键词文件夹名称
        """
        # 简化：直接从命令参数（config.KEYWORDS）获取第一个关键词
        keywords_str = getattr(config, 'KEYWORDS', '') or ''
        keywords_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        if not keywords_list:
            raise ValueError("[BiliVideoFolderMediaStore.get_keyword_folder] --keywords is required for search and must not be empty")
        return utils.replaceT(keywords_list[0])
    
    def get_existing_video_folder(self, video_id: str, content_item: Dict = None) -> str:
        """
        查找是否已存在该视频的文件夹
        Args:
            video_id: 视频ID (aid)
            content_item: 内容项，用于获取关键词
        Returns:
            已存在的文件夹路径，如果不存在返回None
        """
        import os
        
        keyword_folder = self.get_keyword_folder(content_item)
        keyword_path = f"{self.base_store_path}/{keyword_folder}"
        
        if not os.path.exists(keyword_path):
            return None
            
        for folder_name in os.listdir(keyword_path):
            if folder_name.endswith(f"_{video_id}"):
                return f"{keyword_path}/{folder_name}"
        return None
    
    def make_video_folder_path(self, video_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        创建视频文件夹路径
        Args:
            video_id: 视频ID
            publish_time: 视频发布时间戳（秒）
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        keyword_folder = self.get_keyword_folder(content_item)
        
        if publish_time:
            # 使用视频发布时间
            publish_datetime = datetime.fromtimestamp(publish_time)
            date_time_str = publish_datetime.strftime("%Y%m%d_%H%M%S")
        else:
            # 如果没有发布时间，使用当前时间作为备选
            now = datetime.now()
            date_time_str = now.strftime("N%Y%m%d_%H%M%S")
        
        folder_name = f"{date_time_str}_{video_id}"
        return f"{self.base_store_path}/{keyword_folder}/{folder_name}"
    
    def get_or_create_video_folder(self, video_id: str, publish_time: int = None, content_item: Dict = None) -> str:
        """
        获取或创建视频文件夹
        Args:
            video_id: 视频ID
            publish_time: 视频发布时间戳（秒）
            content_item: 内容项，用于获取关键词
        Returns:
            文件夹路径
        """
        existing_folder = self.get_existing_video_folder(video_id, content_item)
        if existing_folder:
            return existing_folder
        
        new_folder = self.make_video_folder_path(video_id, publish_time, content_item)
        pathlib.Path(new_folder).mkdir(parents=True, exist_ok=True)
        return new_folder
    
    async def store_video(self, video_content_item: Dict):
        """
        存储视频文件
        Args:
            video_content_item: 包含aid, video_content, extension_file_name的字典
        """
        aid = str(video_content_item.get("aid"))
        video_content = video_content_item.get("video_content")
        extension_file_name = video_content_item.get("extension_file_name", "video.mp4")
        
        if not aid or not video_content:
            utils.logger.error("[BiliVideoFolderMediaStore.store_video] aid and video_content are required")
            return
        
        # 获取或创建视频文件夹
        video_folder = self.get_or_create_video_folder(aid, None, video_content_item)
        
        # 保存视频文件
        video_file_path = f"{video_folder}/{extension_file_name}"
        
        async with aiofiles.open(video_file_path, 'wb') as f:
            await f.write(video_content)
        
        utils.logger.info(f"[BiliVideoFolderMediaStore.store_video] Saved video: {video_file_path}")
