# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/bilibili/bilibili_store_audio.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对目标平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from pathlib import Path
from typing import Dict, Optional

from base.base_crawler import AbstractStoreAudio
from tools import utils
from tools.media_util import extract_audio_from_video
import config


class BilibiliAudio(AbstractStoreAudio):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.audio_store_path = f"{config.SAVE_DATA_PATH}/bili/audios"
        else:
            self.audio_store_path = "data/bili/audios"

    def make_save_file_name(self, aid: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            aid: aid
            extension_file_name: audio filename with extension

        Returns:

        """
        return f"{self.audio_store_path}/{aid}/{extension_file_name}"

    async def store_audio(self, audio_content_item: Dict) -> Optional[str]:
        """
        Extract audio from a downloaded video and save it to the audio store path.

        Args:
            audio_content_item: dict with keys:
                - aid: aid
                - video_path: path to the downloaded video file
                - extension_file_name: audio filename with extension

        Returns:
            Path to the extracted audio file, or None if failed.
        """
        aid: str = str(audio_content_item.get("aid"))
        video_path: str = audio_content_item.get("video_path")
        extension_file_name: str = audio_content_item.get("extension_file_name")

        if not video_path or not Path(video_path).exists():
            utils.logger.warning(f"[BilibiliAudio.store_audio] Video not found: {video_path}")
            return None

        Path(self.audio_store_path + "/" + aid).mkdir(parents=True, exist_ok=True)
        audio_path = self.make_save_file_name(aid, extension_file_name)

        return await extract_audio_from_video(
            video_path=video_path,
            audio_path=audio_path,
            audio_format=config.AUDIO_FORMAT,
        )
