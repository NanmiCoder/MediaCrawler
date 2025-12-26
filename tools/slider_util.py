# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/slider_util.py
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
# @Time    : 2023/12/2 12:55
# @Desc    : Slider verification utility package
import os
from typing import List
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np


class Slide:
    """
    copy from https://blog.csdn.net/weixin_43582101 thanks for author
    update: relakkes
    """
    def __init__(self, gap, bg, gap_size=None, bg_size=None, out=None):
        """
        :param gap: Gap image path or url
        :param bg: Background image with gap path or url
        """
        self.img_dir = os.path.join(os.getcwd(), 'temp_image')
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)

        bg_resize = bg_size if bg_size else (340, 212)
        gap_size = gap_size if gap_size else (68, 68)
        self.bg = self.check_is_img_path(bg, 'bg', resize=bg_resize)
        self.gap = self.check_is_img_path(gap, 'gap', resize=gap_size)
        self.out = out if out else os.path.join(self.img_dir, 'out.jpg')

    @staticmethod
    def check_is_img_path(img, img_type, resize):
        if img.startswith('http'):
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
                          "q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en-GB;q=0.8,en;q=0.7,ja;q=0.6",
                "AbstractCache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Host": urlparse(img).hostname,
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/91.0.4472.164 Safari/537.36",
            }
            img_res = httpx.get(img, headers=headers)
            if img_res.status_code == 200:
                img_path = f'./temp_image/{img_type}.jpg'
                image = np.asarray(bytearray(img_res.content), dtype="uint8")
                image = cv2.imdecode(image, cv2.IMREAD_COLOR)
                if resize:
                    image = cv2.resize(image, dsize=resize)
                cv2.imwrite(img_path, image)
                return img_path
            else:
                raise Exception(f"Failed to save {img_type} image")
        else:
            return img

    @staticmethod
    def clear_white(img):
        """Clear whitespace from image, mainly clearing slider whitespace"""
        img = cv2.imread(img)
        rows, cols, channel = img.shape
        min_x = 255
        min_y = 255
        max_x = 0
        max_y = 0
        for x in range(1, rows):
            for y in range(1, cols):
                t = set(img[x, y])
                if len(t) >= 2:
                    if x <= min_x:
                        min_x = x
                    elif x >= max_x:
                        max_x = x

                    if y <= min_y:
                        min_y = y
                    elif y >= max_y:
                        max_y = y
        img1 = img[min_x:max_x, min_y: max_y]
        return img1

    def template_match(self, tpl, target):
        th, tw = tpl.shape[:2]
        result = cv2.matchTemplate(target, tpl, cv2.TM_CCOEFF_NORMED)
        # Find min and max value positions in matrix
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        tl = max_loc
        br = (tl[0] + tw, tl[1] + th)
        # Draw rectangle border to mark the matched area
        # target: target image
        # tl: rectangle top-left corner
        # br: rectangle width and height
        # (0,0,255): rectangle border color
        # 1: rectangle border size
        cv2.rectangle(target, tl, br, (0, 0, 255), 2)
        cv2.imwrite(self.out, target)
        return tl[0]

    @staticmethod
    def image_edge_detection(img):
        edges = cv2.Canny(img, 100, 200)
        return edges

    def discern(self):
        img1 = self.clear_white(self.gap)
        img1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        slide = self.image_edge_detection(img1)

        back = cv2.imread(self.bg, cv2.COLOR_RGB2GRAY)
        back = self.image_edge_detection(back)

        slide_pic = cv2.cvtColor(slide, cv2.COLOR_GRAY2RGB)
        back_pic = cv2.cvtColor(back, cv2.COLOR_GRAY2RGB)
        x = self.template_match(slide_pic, back_pic)
        # Output x-coordinate, i.e., slider position on image
        return x


def get_track_simple(distance) -> List[int]:
    # Some detection checks movement speed - constant speed will be detected, so use gradual acceleration
    # distance is the total distance to move
    # Movement track
    track: List[int] = []
    # Current displacement
    current = 0
    # Deceleration threshold
    mid = distance * 4 / 5
    # Time interval
    t = 0.2
    # Initial velocity
    v = 1

    while current < distance:
        if current < mid:
            # Acceleration = 4
            a = 4
        else:
            # Acceleration = -3
            a = -3
        v0 = v
        # Current velocity
        v = v0 + a * t  # type: ignore
        # Movement distance
        move = v0 * t + 1 / 2 * a * t * t
        # Current displacement
        current += move  # type: ignore
        # Add to track
        track.append(round(move))
    return track


def get_tracks(distance: int, level: str = "easy") -> List[int]:
    if level == "easy":
        return get_track_simple(distance)
    else:
        from . import easing
        _, tricks = easing.get_tracks(distance, seconds=2, ease_func="ease_out_expo")
        return tricks
