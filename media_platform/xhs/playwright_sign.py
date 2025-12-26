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

# Generate Xiaohongshu signature by calling window.mnsv2 via Playwright injection

import hashlib
import json
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, quote

from playwright.async_api import Page

from .xhs_sign import b64_encode, encode_utf8, get_trace_id, mrc


def _build_sign_string(uri: str, data: Optional[Union[Dict, str]] = None, method: str = "POST") -> str:
    """Build string to be signed

    Args:
        uri: API path
        data: Request data
        method: Request method (GET or POST)

    Returns:
        String to be signed
    """
    if method.upper() == "POST":
        # POST request uses JSON format
        c = uri
        if data is not None:
            if isinstance(data, dict):
                c += json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            elif isinstance(data, str):
                c += data
        return c
    else:
        # GET request uses query string format
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
                # Use URL encoding (safe parameter preserves certain characters from encoding)
                # Note: httpx will encode commas, equals signs, etc., we need to handle the same way
                value_str = quote(value_str, safe='')
                params.append(f"{key}={value_str}")
            return f"{uri}?{'&'.join(params)}"
        elif isinstance(data, str):
            return f"{uri}?{data}"
        return uri


def _md5_hex(s: str) -> str:
    """Calculate MD5 hash value"""
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _build_xs_payload(x3_value: str, data_type: str = "object") -> str:
    """Build x-s signature"""
    s = {
        "x0": "4.2.1",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": x3_value,
        "x4": data_type,
    }
    return "XYS_" + b64_encode(encode_utf8(json.dumps(s, separators=(",", ":"))))


def _build_xs_common(a1: str, b1: str, x_s: str, x_t: str) -> str:
    """Build x-s-common request header"""
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
    """Get b1 value from localStorage"""
    try:
        local_storage = await page.evaluate("() => window.localStorage")
        return local_storage.get("b1", "")
    except Exception:
        return ""


async def call_mnsv2(page: Page, sign_str: str, md5_str: str) -> str:
    """
    Call window.mnsv2 function via playwright

    Args:
        page: playwright Page object
        sign_str: String to be signed (uri + JSON.stringify(data))
        md5_str: MD5 hash value of sign_str

    Returns:
        Signature string returned by mnsv2
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
    Generate x-s signature via playwright injection

    Args:
        page: playwright Page object (must have Xiaohongshu page open)
        uri: API path, e.g., "/api/sns/web/v1/search/notes"
        data: Request data (GET params or POST payload)
        method: Request method (GET or POST)

    Returns:
        x-s signature string
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
    Generate complete signature request headers via playwright

    Args:
        page: playwright Page object (must have Xiaohongshu page open)
        uri: API path
        data: Request data
        a1: a1 value from cookie
        method: Request method (GET or POST)

    Returns:
        Dictionary containing x-s, x-t, x-s-common, x-b3-traceid
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
    Generate request header signature using playwright injection method
    Can directly replace _pre_headers method in client.py

    Args:
        page: playwright Page object
        url: Request URL
        cookie_dict: Cookie dictionary
        params: GET request parameters
        payload: POST request parameters

    Returns:
        Signed request header dictionary
    """
    a1_value = cookie_dict.get("a1", "")
    uri = urlparse(url).path

    # Determine request data and method
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
