# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/extractor.py
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

import json
import re
from typing import Dict, Optional

import humps

from tools import utils

# Matches a bare JS `undefined` value (after `:`, `[` or `,`), not the word inside strings
_JS_UNDEFINED_RE = re.compile(r"(?<=[:\[,])\s*undefined(?=\s*[,}\]])")


class XiaoHongShuExtractor:
    def __init__(self):
        pass

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        """Extract note details from HTML

        Args:
            html (str): HTML string

        Returns:
            Dict: Note details dictionary
        """
        if "noteDetailMap" not in html:
            # Either a CAPTCHA appeared or the note doesn't exist
            return None

        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[0]
        # Only replace bare JS `undefined` values. A blanket str.replace also rewrote the
        # word "undefined" inside note titles/descriptions and produced invalid JSON.
        state = _JS_UNDEFINED_RE.sub("null", state)
        if state != "{}":
            try:
                note_dict = humps.decamelize(json.loads(state))
                return note_dict["note"]["note_detail_map"][note_id]["note"]
            except (json.JSONDecodeError, KeyError) as e:
                utils.logger.warning(f"[XiaoHongShuExtractor.extract_note_detail_from_html] parse failed for {note_id}: {e}")
                return None
        return None

    def extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        """Extract user information from HTML

        Args:
            html (str): HTML string

        Returns:
            Dict: User information dictionary
        """
        match = re.search(
            r"<script>window.__INITIAL_STATE__=(.+)<\/script>", html, re.M
        )
        if match is None:
            return None
        raw = _JS_UNDEFINED_RE.sub("null", match.group(1))
        # The page state can contain JS literals such as `new Set([...])`, which are not JSON
        raw = re.sub(r"new (?:Set|Map)\((\[[^()]*?\])\)", r"\1", raw)
        try:
            # The greedy regex may capture trailing script content; decode only the first JSON value
            info, _ = json.JSONDecoder(strict=False).raw_decode(raw.strip())
        except json.JSONDecodeError as e:
            utils.logger.warning(f"[XiaoHongShuExtractor.extract_creator_info_from_html] parse failed: {e}")
            return None
        if info is None:
            return None
        return info.get("user").get("userPageData")
