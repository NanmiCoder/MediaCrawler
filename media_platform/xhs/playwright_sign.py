# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/xhs/playwright_sign.py
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

# 通过 Playwright 注入调用 window.mnsv2 生成小红书签名

import hashlib
import json
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, quote

from playwright.async_api import Page

from .xhs_sign import b64_encode, encode_utf8, get_trace_id, mrc


def _build_sign_string(uri: str, data: Optional[Union[Dict, str]] = None, method: str = "POST") -> str:
    """构建待签名字符串
    
    Args:
        uri: API路径
        data: 请求数据
        method: 请求方法 (GET 或 POST)
        
    Returns:
        待签名字符串
    """
    if method.upper() == "POST":
        # POST 请求使用 JSON 格式
        c = uri
        if data is not None:
            if isinstance(data, dict):
                c += json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            elif isinstance(data, str):
                c += data
        return c
    else:
        # GET 请求使用查询字符串格式
        if not data or (isinstance(data, dict) and len(data) == 0):
            return uri
        
        if isinstance(data, dict):
            params = []
            for key in data.keys():
                value = data[key]
                if isinstance(value, list):
                    value_str = ",".join(str(v) for v in value)
                elif value is not None:
                    value_str = str(value)
                else:
                    value_str = ""
                # 使用URL编码（safe参数保留某些字符不编码）
                # 注意：httpx会对逗号、等号等字符进行编码，我们也需要同样处理
                value_str = quote(value_str, safe='')
                params.append(f"{key}={value_str}")
            return f"{uri}?{'&'.join(params)}"
        elif isinstance(data, str):
            return f"{uri}?{data}"
        return uri


def _md5_hex(s: str) -> str:
    """计算 MD5 哈希值"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _build_xs_payload(x3_value: str, data_type: str = "object") -> str:
    """构建 x-s 签名"""
    s = {
        "x0": "4.2.1",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": x3_value,
        "x4": data_type,
    }
    return "XYS_" + b64_encode(encode_utf8(json.dumps(s, separators=(",", ":"))))


def _build_xs_common(a1: str, b1: str, x_s: str, x_t: str) -> str:
    """构建 x-s-common 请求头"""
    payload = {
        "s0": 3,
        "s1": "",
        "x0": "1",
        "x1": "4.2.2",
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.74.0",
        "x5": a1,
        "x6": x_t,
        "x7": x_s,
        "x8": b1,
        "x9": mrc(x_t + x_s + b1),
        "x10": 154,
        "x11": "normal",
    }
    return b64_encode(encode_utf8(json.dumps(payload, separators=(",", ":"))))


async def get_b1_from_localstorage(page: Page) -> str:
    """从 localStorage 获取 b1 值"""
    try:
        local_storage = await page.evaluate("() => window.localStorage")
        return local_storage.get("b1", "")
    except Exception:
        return ""


async def call_mnsv2(page: Page, sign_str: str, md5_str: str) -> str:
    """
    通过 playwright 调用 window.mnsv2 函数

    Args:
        page: playwright Page 对象
        sign_str: 待签名字符串 (uri + JSON.stringify(data))
        md5_str: sign_str 的 MD5 哈希值

    Returns:
        mnsv2 返回的签名字符串
    """
    sign_str_escaped = sign_str.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    md5_str_escaped = md5_str.replace("\\", "\\\\").replace("'", "\\'")

    try:
        result = await page.evaluate(f"window.mnsv2('{sign_str_escaped}', '{md5_str_escaped}')")
        return result if result else ""
    except Exception:
        return ""


async def sign_xs_with_playwright(
    page: Page,
    uri: str,
    data: Optional[Union[Dict, str]] = None,
    method: str = "POST",
) -> str:
    """
    通过 playwright 注入生成 x-s 签名

    Args:
        page: playwright Page 对象（必须已打开小红书页面）
        uri: API 路径，如 "/api/sns/web/v1/search/notes"
        data: 请求数据（GET 的 params 或 POST 的 payload）
        method: 请求方法 (GET 或 POST)

    Returns:
        x-s 签名字符串
    """
    sign_str = _build_sign_string(uri, data, method)
    md5_str = _md5_hex(sign_str)
    x3_value = await call_mnsv2(page, sign_str, md5_str)
    data_type = "object" if isinstance(data, (dict, list)) else "string"
    return _build_xs_payload(x3_value, data_type)


async def sign_with_playwright(
    page: Page,
    uri: str,
    data: Optional[Union[Dict, str]] = None,
    a1: str = "",
    method: str = "POST",
) -> Dict[str, Any]:
    """
    通过 playwright 生成完整的签名请求头

    Args:
        page: playwright Page 对象（必须已打开小红书页面）
        uri: API 路径
        data: 请求数据
        a1: cookie 中的 a1 值
        method: 请求方法 (GET 或 POST)

    Returns:
        包含 x-s, x-t, x-s-common, x-b3-traceid 的字典
    """
    b1 = await get_b1_from_localstorage(page)
    x_s = await sign_xs_with_playwright(page, uri, data, method)
    x_t = str(int(time.time() * 1000))

    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": _build_xs_common(a1, b1, x_s, x_t),
        "x-b3-traceid": get_trace_id(),
    }


async def pre_headers_with_playwright(
    page: Page,
    url: str,
    cookie_dict: Dict[str, str],
    params: Optional[Dict] = None,
    payload: Optional[Dict] = None,
) -> Dict[str, str]:
    """
    使用 playwright 注入方式生成请求头签名
    可直接替换 client.py 中的 _pre_headers 方法

    Args:
        page: playwright Page 对象
        url: 请求 URL
        cookie_dict: cookie 字典
        params: GET 请求参数
        payload: POST 请求参数

    Returns:
        签名后的请求头字典
    """
    a1_value = cookie_dict.get("a1", "")
    uri = urlparse(url).path

    # 确定请求数据和方法
    if params is not None:
        data = params
        method = "GET"
    elif payload is not None:
        data = payload
        method = "POST"
    else:
        raise ValueError("params or payload is required")

    signs = await sign_with_playwright(page, uri, data, a1_value, method)

    return {
        "X-S": signs["x-s"],
        "X-T": signs["x-t"],
        "x-S-Common": signs["x-s-common"],
        "X-B3-Traceid": signs["x-b3-traceid"],
    }
