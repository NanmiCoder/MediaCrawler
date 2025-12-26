# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/bilibili/help.py
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
# @Time    : 2023/12/2 23:26
# @Desc    : bilibili request parameter signing
# Reverse engineering implementation reference: https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html#wbi%E7%AD%BE%E5%90%8D%E7%AE%97%E6%B3%95
import re
import urllib.parse
from hashlib import md5
from typing import Dict

from model.m_bilibili import VideoUrlInfo, CreatorUrlInfo
from tools import utils


class BilibiliSign:
    def __init__(self, img_key: str, sub_key: str):
        self.img_key = img_key
        self.sub_key = sub_key
        self.map_table = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
            33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
            61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
            36, 20, 34, 44, 52
        ]

    def get_salt(self) -> str:
        """
        Get the salted key
        :return:
        """
        salt = ""
        mixin_key = self.img_key + self.sub_key
        for mt in self.map_table:
            salt += mixin_key[mt]
        return salt[:32]

    def sign(self, req_data: Dict) -> Dict:
        """
        Add current timestamp to request parameters, sort keys in dictionary order,
        then URL encode the parameters and combine with salt to generate md5 for w_rid parameter
        :param req_data:
        :return:
        """
        current_ts = utils.get_unix_timestamp()
        req_data.update({"wts": current_ts})
        req_data = dict(sorted(req_data.items()))
        req_data = {
            # Filter "!'()*" characters from values
            k: ''.join(filter(lambda ch: ch not in "!'()*", str(v)))
            for k, v
            in req_data.items()
        }
        query = urllib.parse.urlencode(req_data)
        salt = self.get_salt()
        wbi_sign = md5((query + salt).encode()).hexdigest()  # Calculate w_rid
        req_data['w_rid'] = wbi_sign
        return req_data


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from Bilibili video URL
    Args:
        url: Bilibili video link
            - https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387.homepage.video_card.click
            - https://www.bilibili.com/video/BV1d54y1g7db
            - BV1d54y1g7db (directly pass BV number)
    Returns:
        VideoUrlInfo: Object containing video ID
    """
    # If the input is already a BV number, return directly
    if url.startswith("BV"):
        return VideoUrlInfo(video_id=url)

    # Use regex to extract BV number
    # Match /video/BV... or /video/av... format
    bv_pattern = r'/video/(BV[a-zA-Z0-9]+)'
    match = re.search(bv_pattern, url)

    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id)

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator ID from Bilibili creator space URL
    Args:
        url: Bilibili creator space link
            - https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0
            - https://space.bilibili.com/20813884
            - 434377496 (directly pass UID)
    Returns:
        CreatorUrlInfo: Object containing creator ID
    """
    # If the input is already a numeric ID, return directly
    if url.isdigit():
        return CreatorUrlInfo(creator_id=url)

    # Use regex to extract UID
    # Match /space.bilibili.com/number format
    uid_pattern = r'space\.bilibili\.com/(\d+)'
    match = re.search(uid_pattern, url)

    if match:
        creator_id = match.group(1)
        return CreatorUrlInfo(creator_id=creator_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    video_url1 = "https://www.bilibili.com/video/BV1dwuKzmE26/?spm_id_from=333.1387.homepage.video_card.click"
    video_url2 = "BV1d54y1g7db"
    print("Video URL parsing test:")
    print(f"URL1: {video_url1} -> {parse_video_info_from_url(video_url1)}")
    print(f"URL2: {video_url2} -> {parse_video_info_from_url(video_url2)}")

    # Test creator URL parsing
    creator_url1 = "https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0"
    creator_url2 = "20813884"
    print("\nCreator URL parsing test:")
    print(f"URL1: {creator_url1} -> {parse_creator_info_from_url(creator_url1)}")
    print(f"URL2: {creator_url2} -> {parse_creator_info_from_url(creator_url2)}")
