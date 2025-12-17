#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明:本代码仅供学习和研究目的使用。使用者应遵守以下原则:
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率,避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。

"""
Xiaohongshu URL Crawler - Standalone module for crawling a single Xiaohongshu note URL

This module provides a simple interface to crawl Xiaohongshu (Little Red Book) note details
from a given URL without requiring database storage.

Usage:
    from xhs_url_crawler import XhsUrlCrawler

    async def main():
        crawler = XhsUrlCrawler()
        note_url = "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=xxx&xsec_source=pc_search"

        # Login (choose one method)
        await crawler.login_by_qrcode()  # QR code login
        # OR
        # await crawler.login_by_cookie("your_cookie_string")  # Cookie login

        # Crawl note
        note_data = await crawler.crawl_note(note_url)
        print(note_data)

        # Cleanup
        await crawler.close()

    if __name__ == "__main__":
        import asyncio
        asyncio.run(main())
"""

import asyncio
import ctypes
import functools
import json
import logging
import random
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
import humps
from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)
from pydantic import BaseModel, Field
from tenacity import RetryError, retry, retry_if_result, stop_after_attempt, wait_fixed
from xhshow import Xhshow


# ==================== Data Models ====================

class NoteUrlInfo(BaseModel):
    """Parsed note URL information"""
    note_id: str = Field(title="note id")
    xsec_token: str = Field(title="xsec token")
    xsec_source: str = Field(title="xsec source")


# ==================== Exceptions ====================

class DataFetchError(Exception):
    """Error when fetching data"""
    pass


class IPBlockError(Exception):
    """IP blocked by server"""
    pass


# ==================== Helper Functions ====================

def extract_url_params_to_dict(url: str) -> Dict:
    """Extract URL parameters to dict"""
    url_params_dict = dict()
    if not url:
        return url_params_dict
    parsed_url = urllib.parse.urlparse(url)
    url_params_dict = dict(urllib.parse.parse_qsl(parsed_url.query))
    return url_params_dict


def parse_note_info_from_note_url(url: str) -> NoteUrlInfo:
    """
    Parse note information from Xiaohongshu note URL
    Args:
        url: "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
    Returns:
        NoteUrlInfo object
    """
    note_id = url.split("/")[-1].split("?")[0]
    params = extract_url_params_to_dict(url)
    xsec_token = params.get("xsec_token", "")
    xsec_source = params.get("xsec_source", "")
    return NoteUrlInfo(note_id=note_id, xsec_token=xsec_token, xsec_source=xsec_source)


def convert_cookies(cookies: Optional[List[Dict]]) -> Tuple[str, Dict]:
    """Convert playwright cookies to string and dict"""
    if not cookies:
        return "", {}
    cookies_str = ";".join([f"{cookie.get('name')}={cookie.get('value')}" for cookie in cookies])
    cookie_dict = dict()
    for cookie in cookies:
        cookie_dict[cookie.get('name')] = cookie.get('value')
    return cookies_str, cookie_dict


def convert_str_cookie_to_dict(cookie_str: str) -> Dict:
    """Convert cookie string to dict"""
    cookie_dict: Dict[str, str] = dict()
    if not cookie_str:
        return cookie_dict
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        cookie_list = cookie.split("=")
        if len(cookie_list) != 2:
            continue
        cookie_value = cookie_list[1]
        if isinstance(cookie_value, list):
            cookie_value = "".join(cookie_value)
        cookie_dict[cookie_list[0]] = cookie_value
    return cookie_dict


# ==================== Signature Functions ====================

def get_b3_trace_id():
    """Generate b3 trace ID"""
    re = "abcdef0123456789"
    je = 16
    e = ""
    for t in range(16):
        e += re[random.randint(0, je - 1)]
    return e


def mrc(e):
    """MRC checksum calculation"""
    ie = [
        0, 1996959894, 3993919788, 2567524794, 124634137, 1886057615, 3915621685,
        2657392035, 249268274, 2044508324, 3772115230, 2547177864, 162941995,
        2125561021, 3887607047, 2428444049, 498536548, 1789927666, 4089016648,
        2227061214, 450548861, 1843258603, 4107580753, 2211677639, 325883990,
        1684777152, 4251122042, 2321926636, 335633487, 1661365465, 4195302755,
        2366115317, 997073096, 1281953886, 3579855332, 2724688242, 1006888145,
        1258607687, 3524101629, 2768942443, 901097722, 1119000684, 3686517206,
        2898065728, 853044451, 1172266101, 3705015759, 2882616665, 651767980,
        1373503546, 3369554304, 3218104598, 565507253, 1454621731, 3485111705,
        3099436303, 671266974, 1594198024, 3322730930, 2970347812, 795835527,
        1483230225, 3244367275, 3060149565, 1994146192, 31158534, 2563907772,
        4023717930, 1907459465, 112637215, 2680153253, 3904427059, 2013776290,
        251722036, 2517215374, 3775830040, 2137656763, 141376813, 2439277719,
        3865271297, 1802195444, 476864866, 2238001368, 4066508878, 1812370925,
        453092731, 2181625025, 4111451223, 1706088902, 314042704, 2344532202,
        4240017532, 1658658271, 366619977, 2362670323, 4224994405, 1303535960,
        984961486, 2747007092, 3569037538, 1256170817, 1037604311, 2765210733,
        3554079995, 1131014506, 879679996, 2909243462, 3663771856, 1141124467,
        855842277, 2852801631, 3708648649, 1342533948, 654459306, 3188396048,
        3373015174, 1466479909, 544179635, 3110523913, 3462522015, 1591671054,
        702138776, 2966460450, 3352799412, 1504918807, 783551873, 3082640443,
        3233442989, 3988292384, 2596254646, 62317068, 1957810842, 3939845945,
        2647816111, 81470997, 1943803523, 3814918930, 2489596804, 225274430,
        2053790376, 3826175755, 2466906013, 167816743, 2097651377, 4027552580,
        2265490386, 503444072, 1762050814, 4150417245, 2154129355, 426522225,
        1852507879, 4275313526, 2312317920, 282753626, 1742555852, 4189708143,
        2394877945, 397917763, 1622183637, 3604390888, 2714866558, 953729732,
        1340076626, 3518719985, 2797360999, 1068828381, 1219638859, 3624741850,
        2936675148, 906185462, 1090812512, 3747672003, 2825379669, 829329135,
        1181335161, 3412177804, 3160834842, 628085408, 1382605366, 3423369109,
        3138078467, 570562233, 1426400815, 3317316542, 2998733608, 733239954,
        1555261956, 3268935591, 3050360625, 752459403, 1541320221, 2607071920,
        3965973030, 1969922972, 40735498, 2617837225, 3943577151, 1913087877,
        83908371, 2512341634, 3803740692, 2075208622, 213261112, 2463272603,
        3855990285, 2094854071, 198958881, 2262029012, 4057260610, 1759359992,
        534414190, 2176718541, 4139329115, 1873836001, 414664567, 2282248934,
        4279200368, 1711684554, 285281116, 2405801727, 4167216745, 1634467795,
        376229701, 2685067896, 3608007406, 1308918612, 956543938, 2808555105,
        3495958263, 1231636301, 1047427035, 2932959818, 3654703836, 1088359270,
        936918000, 2847714899, 3736837829, 1202900863, 817233897, 3183342108,
        3401237130, 1404277552, 615818150, 3134207493, 3453421203, 1423857449,
        601450431, 3009837614, 3294710456, 1567103746, 711928724, 3020668471,
        3272380065, 1510334235, 755167117,
    ]
    o = -1

    def right_without_sign(num: int, bit: int = 0) -> int:
        val = ctypes.c_uint32(num).value >> bit
        MAX32INT = 4294967295
        return (val + (MAX32INT + 1)) % (2 * (MAX32INT + 1)) - MAX32INT - 1

    for n in range(57):
        o = ie[(o & 255) ^ ord(e[n])] ^ right_without_sign(o, 8)
    return o ^ -1 ^ 3988292384


lookup = [
    "Z", "m", "s", "e", "r", "b", "B", "o", "H", "Q", "t", "N", "P", "+", "w", "O",
    "c", "z", "a", "/", "L", "p", "n", "g", "G", "8", "y", "J", "q", "4", "2", "K",
    "W", "Y", "j", "0", "D", "S", "f", "d", "i", "k", "x", "3", "V", "T", "1", "6",
    "I", "l", "U", "A", "F", "M", "9", "7", "h", "E", "C", "v", "u", "R", "X", "5",
]


def tripletToBase64(e):
    """Convert triplet to base64"""
    return (
        lookup[63 & (e >> 18)] +
        lookup[63 & (e >> 12)] +
        lookup[(e >> 6) & 63] +
        lookup[e & 63]
    )


def encodeChunk(e, t, r):
    """Encode chunk"""
    m = []
    for b in range(t, r, 3):
        n = (16711680 & (e[b] << 16)) + \
            ((e[b + 1] << 8) & 65280) + (e[b + 2] & 255)
        m.append(tripletToBase64(n))
    return ''.join(m)


def b64Encode(e):
    """Base64 encode with custom alphabet"""
    P = len(e)
    W = P % 3
    U = []
    z = 16383
    H = 0
    Z = P - W
    while H < Z:
        U.append(encodeChunk(e, H, Z if H + z > Z else H + z))
        H += z
    if 1 == W:
        F = e[P - 1]
        U.append(lookup[F >> 2] + lookup[(F << 4) & 63] + "==")
    elif 2 == W:
        F = (e[P - 2] << 8) + e[P - 1]
        U.append(lookup[F >> 10] + lookup[63 & (F >> 4)] +
                 lookup[(F << 2) & 63] + "=")
    return "".join(U)


def encodeUtf8(e):
    """UTF-8 encode"""
    b = []
    m = urllib.parse.quote(e, safe='~()*!.\'')
    w = 0
    while w < len(m):
        T = m[w]
        if T == "%":
            E = m[w + 1] + m[w + 2]
            S = int(E, 16)
            b.append(S)
            w += 2
        else:
            b.append(ord(T[0]))
        w += 1
    return b


def sign(a1="", b1="", x_s="", x_t=""):
    """
    Generate signature headers for Xiaohongshu API
    """
    common = {
        "s0": 3,  # getPlatformCode
        "s1": "",
        "x0": "1",  # localStorage.getItem("b1b1")
        "x1": "4.2.2",  # version
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.74.0",
        "x5": a1,  # cookie of a1
        "x6": x_t,
        "x7": x_s,
        "x8": b1,  # localStorage.getItem("b1")
        "x9": mrc(x_t + x_s + b1),
        "x10": 154,  # getSigCount
        "x11": "normal"
    }
    encode_str = encodeUtf8(json.dumps(common, separators=(',', ':')))
    x_s_common = b64Encode(encode_str)
    x_b3_traceid = get_b3_trace_id()
    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": x_s_common,
        "x-b3-traceid": x_b3_traceid
    }


# ==================== Cookie Manager ====================

class CookieManager:
    """Manage Xiaohongshu cookie persistence"""

    def __init__(self, cookie_dir: str = "cookies", logger: Optional[logging.Logger] = None):
        """
        Initialize Cookie Manager

        Args:
            cookie_dir: Directory to store cookies
            logger: Logger instance
        """
        self.cookie_dir = Path(cookie_dir)
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.cookie_dir / "xhs_cookies.json"
        self.logger = logger or logging.getLogger("CookieManager")

    def save_cookies(self, cookies: List[Dict]) -> bool:
        """
        Save cookies to file

        Args:
            cookies: Playwright format cookie list

        Returns:
            bool: Whether save was successful
        """
        try:
            # Add timestamp
            cookie_data = {
                "cookies": cookies,
                "saved_at": time.time(),
                "saved_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Successfully saved {len(cookies)} cookies to {self.cookie_file}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self) -> Optional[List[Dict]]:
        """
        Load cookies from file

        Returns:
            Optional[List[Dict]]: Playwright format cookie list, or None if not found
        """
        if not self.cookie_file.exists():
            self.logger.info(f"Cookie file not found: {self.cookie_file}")
            return None

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            cookies = cookie_data.get("cookies", [])
            saved_at = cookie_data.get("saved_at", 0)
            saved_time = cookie_data.get("saved_time", "Unknown")

            # Check if cookies are older than 30 days
            if time.time() - saved_at > 30 * 24 * 3600:
                self.logger.warning(
                    f"Cookies are older than 30 days (saved at {saved_time}), may be expired"
                )

            self.logger.info(
                f"Successfully loaded {len(cookies)} cookies from {self.cookie_file} (saved at {saved_time})"
            )
            return cookies

        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return None

    def clear_cookies(self) -> bool:
        """
        Clear saved cookies file

        Returns:
            bool: Whether clear was successful
        """
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                self.logger.info(f"Successfully cleared cookies file: {self.cookie_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")
            return False

    def get_cookie_info(self) -> Optional[Dict]:
        """
        Get saved cookie information (without actual cookie data)

        Returns:
            Optional[Dict]: Cookie info dict with save time, count, etc.
        """
        if not self.cookie_file.exists():
            return None

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)

            return {
                "saved_at": cookie_data.get("saved_at", 0),
                "saved_time": cookie_data.get("saved_time", "Unknown"),
                "cookie_count": len(cookie_data.get("cookies", [])),
                "file_path": str(self.cookie_file)
            }

        except Exception as e:
            self.logger.error(f"Failed to get cookie info: {e}")
            return None


# ==================== HTML Extractor ====================

class XiaoHongShuExtractor:
    """Extract data from Xiaohongshu HTML"""

    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        """
        Extract note details from HTML
        Args:
            note_id: Note ID
            html: HTML string
        Returns:
            Dict: Note details
        """
        if "noteDetailMap" not in html:
            return None

        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[
            0
        ].replace("undefined", '""')
        if state != "{}":
            note_dict = humps.decamelize(json.loads(state))
            return note_dict["note"]["note_detail_map"][note_id]["note"]
        return None


# ==================== API Client ====================

class XiaoHongShuClient:
    """Xiaohongshu API Client"""

    def __init__(
        self,
        timeout=60,
        proxy=None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        logger: logging.Logger,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://edith.xiaohongshu.com"
        self._domain = "https://www.xiaohongshu.com"
        self.IP_ERROR_STR = "网络连接异常，请检查网络设置或重启试试"
        self.IP_ERROR_CODE = 300012
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self._extractor = XiaoHongShuExtractor()
        self._xhshow_client = Xhshow()
        self.logger = logger

    async def _pre_headers(self, url: str, params: Optional[Dict] = None, payload: Optional[Dict] = None) -> Dict:
        """
        Generate signature headers
        """
        a1_value = self.cookie_dict.get("a1", "")
        parsed = urllib.parse.urlparse(url)
        uri = parsed.path
        if params is not None:
            x_s = self._xhshow_client.sign_xs_get(
                uri=uri, a1_value=a1_value, params=params
            )
        elif payload is not None:
            x_s = self._xhshow_client.sign_xs_post(
                uri=uri, a1_value=a1_value, payload=payload
            )
        else:
            raise ValueError("params or payload is required")

        # Get b1 value
        b1_value = ""
        try:
            if self.playwright_page:
                local_storage = await self.playwright_page.evaluate(
                    "() => window.localStorage"
                )
                b1_value = local_storage.get("b1", "")
        except Exception as e:
            self.logger.warning(f"Failed to get b1 from localStorage: {e}")

        signs = sign(
            a1=a1_value,
            b1=b1_value,
            x_s=x_s,
            x_t=str(int(time.time() * 1000)),
        )

        headers = {
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "x-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"],
        }
        self.headers.update(headers)
        return self.headers

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, **kwargs) -> Union[str, Any]:
        """
        HTTP request wrapper
        """
        return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code == 471 or response.status_code == 461:
            verify_type = response.headers.get("Verifytype", "")
            verify_uuid = response.headers.get("Verifyuuid", "")
            msg = f"Captcha detected, request failed, Verifytype: {verify_type}, Verifyuuid: {verify_uuid}"
            self.logger.error(msg)
            raise Exception(msg)

        if return_response:
            return response.text
        data: Dict = response.json()
        if data["success"]:
            return data.get("data", data.get("success", {}))
        elif data["code"] == self.IP_ERROR_CODE:
            raise IPBlockError(self.IP_ERROR_STR)
        else:
            err_msg = data.get("msg", None) or f"{response.text}"
            raise DataFetchError(err_msg)

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST request with signature
        """
        headers = await self._pre_headers(uri, payload=data)
        json_str = self._xhshow_client.build_json_body(payload=data)
        return await self.request(
            method="POST",
            url=f"{self._host}{uri}",
            data=json_str,
            headers=headers,
            **kwargs,
        )

    async def get_note_by_id(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
    ) -> Dict:
        """
        Get note details by ID via API
        """
        if xsec_source == "":
            xsec_source = "pc_search"

        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        self.logger.error(f"Get note id:{note_id} empty, res:{res}")
        return dict()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        """
        Get note details from HTML page (fallback method)
        """
        url = (
            "https://www.xiaohongshu.com/explore/"
            + note_id
            + f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
        )
        copy_headers = self.headers.copy()
        if not enable_cookie:
            copy_headers.pop("Cookie", None)

        html = await self.request(
            method="GET", url=url, return_response=True, headers=copy_headers
        )

        return self._extractor.extract_note_detail_from_html(note_id, html)

    async def pong(self) -> bool:
        """
        Check if login state is valid
        """
        self.logger.info("Checking login state...")
        try:
            # Try a simple API call to check login
            test_note_id = "66fad51c000000001b0224b8"
            await self.get_note_by_id_from_html(test_note_id, "", "", enable_cookie=True)
            return True
        except Exception as e:
            self.logger.error(f"Login state check failed: {e}")
            return False

    async def update_cookies(self, browser_context: BrowserContext):
        """
        Update cookies after login
        """
        cookie_str, cookie_dict = convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict


# ==================== Login Handler ====================

class XiaoHongShuLogin:
    """Xiaohongshu login handler"""

    def __init__(
        self,
        browser_context: BrowserContext,
        context_page: Page,
        logger: logging.Logger,
        cookie_str: str = "",
        cookie_manager: Optional[CookieManager] = None
    ):
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str
        self.logger = logger
        self.cookie_manager = cookie_manager or CookieManager(logger=logger)

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
        Check if login is successful
        """
        if "请通过验证" in await self.context_page.content():
            self.logger.info("Captcha detected during login, please verify manually")

        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = convert_cookies(current_cookie)
        current_web_session = cookie_dict.get("web_session")
        if current_web_session != no_logged_in_session:
            return True
        return False

    async def login_by_qrcode(self):
        """Login via QR code"""
        self.logger.info("Starting QR code login...")
        qrcode_img_selector = "xpath=//img[@class='qrcode-img']"

        try:
            # Wait for QR code image
            await self.context_page.wait_for_selector(qrcode_img_selector, timeout=5000)
        except Exception:
            # Try clicking login button if QR code not visible
            self.logger.info("QR code not visible, trying to click login button...")
            try:
                login_button_ele = self.context_page.locator(
                    "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button"
                )
                await login_button_ele.click()
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Failed to find login button: {e}")
                raise

        # Get current session before login
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = convert_cookies(current_cookie)
        no_logged_in_session = cookie_dict.get("web_session")

        self.logger.info("Please scan the QR code with your Xiaohongshu app (waiting up to 600 seconds)...")

        try:
            await self.check_login_state(no_logged_in_session)
        except RetryError:
            self.logger.error("Login failed: timeout waiting for QR code scan")
            raise Exception("QR code login timeout")

        self.logger.info("Login successful! Waiting for redirect...")
        await asyncio.sleep(5)

    async def login_by_cookies(self):
        """Login via cookies"""
        self.logger.info("Starting cookie login...")

        # First try to load cookies from file if cookie_str is empty
        if not self.cookie_str:
            self.logger.info("Attempting to load cookies from file...")
            saved_cookies = self.cookie_manager.load_cookies()
            if saved_cookies:
                await self.browser_context.add_cookies(saved_cookies)
                self.logger.info(f"Successfully loaded {len(saved_cookies)} cookies from file")
                return
            else:
                self.logger.warning("No saved cookies found, please login manually first")
                return

        # If cookie_str is provided, use it
        cookie_dict = convert_str_cookie_to_dict(self.cookie_str)
        cookies_to_add = []

        # Add all cookies, not just web_session
        for key, value in cookie_dict.items():
            cookies_to_add.append({
                'name': key,
                'value': value,
                'domain': ".xiaohongshu.com",
                'path': "/"
            })

        if cookies_to_add:
            await self.browser_context.add_cookies(cookies_to_add)
            self.logger.info(f"Successfully added {len(cookies_to_add)} cookies from cookie string")

    async def save_cookies_to_file(self):
        """Save current browser cookies to file for future use"""
        self.logger.info("Saving cookies to file...")
        try:
            current_cookies = await self.browser_context.cookies()
            if current_cookies:
                success = self.cookie_manager.save_cookies(current_cookies)
                if success:
                    self.logger.info(f"Successfully saved {len(current_cookies)} cookies")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            return False


# ==================== Main Crawler Class ====================

class XhsUrlCrawler:
    """
    Standalone Xiaohongshu URL Crawler

    Simple interface to crawl Xiaohongshu note details from a URL.
    Handles authentication and data fetching without database storage.
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[str] = None,
        auto_save_cookies: bool = True,
        cookie_dir: str = "cookies"
    ):
        """
        Initialize the crawler

        Args:
            headless: Run browser in headless mode (default: True)
            proxy: HTTP proxy URL (optional)
            auto_save_cookies: Automatically save and load cookies (default: True)
            cookie_dir: Directory to store cookies (default: "cookies")
        """
        self.headless = headless
        self.proxy = proxy
        self.auto_save_cookies = auto_save_cookies
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

        # Setup logging
        self.logger = logging.getLogger("XhsUrlCrawler")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize cookie manager
        self.cookie_manager = CookieManager(cookie_dir=cookie_dir, logger=self.logger)

        # Playwright objects (initialized in start())
        self.playwright: Optional[Playwright] = None
        self.browser_context: Optional[BrowserContext] = None
        self.context_page: Optional[Page] = None
        self.xhs_client: Optional[XiaoHongShuClient] = None
        self._started = False

    async def _start_browser(self):
        """Start browser and initialize client"""
        if self._started:
            return

        self.playwright = await async_playwright().start()

        # Prepare proxy settings
        playwright_proxy = None
        httpx_proxy = None
        if self.proxy:
            playwright_proxy = {"server": self.proxy}
            httpx_proxy = self.proxy

        # Launch browser
        chromium = self.playwright.chromium
        browser = await chromium.launch(headless=self.headless, proxy=playwright_proxy)
        self.browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self.user_agent
        )

        # Add stealth script to avoid detection
        await self.browser_context.add_init_script(path="libs/stealth.min.js")

        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(self.index_url)

        # Create API client
        cookie_str, cookie_dict = convert_cookies(await self.browser_context.cookies())
        self.xhs_client = XiaoHongShuClient(
            proxy=httpx_proxy,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "referer": "https://www.xiaohongshu.com/",
                "user-agent": self.user_agent,
                "Cookie": cookie_str,
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            logger=self.logger,
        )

        self._started = True
        self.logger.info("Browser started successfully")

    async def login_by_qrcode(self, save_cookies: Optional[bool] = None):
        """
        Login to Xiaohongshu using QR code

        The QR code will be displayed in the browser. Scan it with your Xiaohongshu app.

        Args:
            save_cookies: Whether to save cookies after login (default: use auto_save_cookies setting)
        """
        await self._start_browser()

        if save_cookies is None:
            save_cookies = self.auto_save_cookies

        login_obj = XiaoHongShuLogin(
            browser_context=self.browser_context,
            context_page=self.context_page,
            logger=self.logger,
            cookie_manager=self.cookie_manager,
        )
        await login_obj.login_by_qrcode()
        await self.xhs_client.update_cookies(browser_context=self.browser_context)

        # Auto-save cookies after successful login
        if save_cookies:
            await login_obj.save_cookies_to_file()

        self.logger.info("QR code login completed successfully")

    async def login_by_cookie(self, cookie_str: str = ""):
        """
        Login to Xiaohongshu using cookie string or saved cookies

        Args:
            cookie_str: Cookie string containing web_session value (optional)
                       Example: "web_session=xxx; other_cookie=yyy"
                       If empty, will try to load from saved cookies file
        """
        await self._start_browser()

        login_obj = XiaoHongShuLogin(
            browser_context=self.browser_context,
            context_page=self.context_page,
            logger=self.logger,
            cookie_str=cookie_str,
            cookie_manager=self.cookie_manager,
        )
        await login_obj.login_by_cookies()
        await self.xhs_client.update_cookies(browser_context=self.browser_context)

        # Reload page with new cookies
        await self.context_page.reload()
        await asyncio.sleep(2)

        self.logger.info("Cookie login completed successfully")

    async def auto_login(self) -> bool:
        """
        Attempt to login automatically using saved cookies

        Returns:
            bool: True if login successful, False otherwise
        """
        await self._start_browser()

        # Check if saved cookies exist
        cookie_info = self.cookie_manager.get_cookie_info()
        if not cookie_info:
            self.logger.info("No saved cookies found for auto-login")
            return False

        self.logger.info(f"Found saved cookies from {cookie_info['saved_time']}, attempting auto-login...")

        # Try to login with saved cookies
        try:
            await self.login_by_cookie()

            # Validate login by checking with pong
            if await self.xhs_client.pong():
                self.logger.info("Auto-login successful!")
                return True
            else:
                self.logger.warning("Auto-login failed: cookies may be expired")
                return False

        except Exception as e:
            self.logger.error(f"Auto-login failed: {e}")
            return False

    async def crawl_note(self, note_url: str) -> Optional[Dict]:
        """
        Crawl a single Xiaohongshu note from URL

        Args:
            note_url: Full Xiaohongshu note URL
                     Example: "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=xxx&xsec_source=pc_search"

        Returns:
            Dict containing note data, or None if failed
        """
        await self._start_browser()

        # Parse URL
        try:
            note_info: NoteUrlInfo = parse_note_info_from_note_url(note_url)
            self.logger.info(f"Parsed note URL: note_id={note_info.note_id}")
        except Exception as e:
            self.logger.error(f"Failed to parse note URL: {e}")
            return None

        # Try to fetch note details
        note_detail = None
        try:
            # Try API first
            try:
                note_detail = await self.xhs_client.get_note_by_id(
                    note_info.note_id,
                    note_info.xsec_source,
                    note_info.xsec_token
                )
            except Exception as e:
                self.logger.warning(f"API fetch failed, trying HTML fallback: {e}")

            # Fallback to HTML parsing
            if not note_detail:
                note_detail = await self.xhs_client.get_note_by_id_from_html(
                    note_info.note_id,
                    note_info.xsec_source,
                    note_info.xsec_token,
                    enable_cookie=True
                )

            if note_detail:
                note_detail.update({
                    "xsec_token": note_info.xsec_token,
                    "xsec_source": note_info.xsec_source
                })
                self.logger.info(f"Successfully fetched note: {note_info.note_id}")
                return note_detail
            else:
                self.logger.error(f"Failed to fetch note: {note_info.note_id}")
                return None

        except Exception as e:
            self.logger.error(f"Error crawling note: {e}")
            return None

    async def close(self):
        """Close browser and cleanup resources"""
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
        self._started = False
        self.logger.info("Crawler closed")


# ==================== Example Usage ====================

async def main():
    """Example usage of XhsUrlCrawler"""
    # Enable auto-save cookies (default behavior)
    crawler = XhsUrlCrawler(headless=False, auto_save_cookies=True)

    try:
        # Try auto-login first (uses saved cookies if available)
        login_success = await crawler.auto_login()

        if not login_success:
            # If auto-login fails, use manual login
            print("\nAuto-login failed. Please login manually:")

            # Method 1: QR code login (scan with your Xiaohongshu app)
            # Cookies will be automatically saved for next time
            await crawler.login_by_qrcode()

            # Method 2: Cookie login (if you have cookies)
            # cookie_str = "web_session=your_session_value_here"
            # await crawler.login_by_cookie(cookie_str)

        # Crawl a note
        note_url = "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
        note_data = await crawler.crawl_note(note_url)

        if note_data:
            print("\n" + "="*50)
            print("Note Data:")
            print("="*50)
            print(json.dumps(note_data, ensure_ascii=False, indent=2))
        else:
            print("Failed to crawl note")

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
