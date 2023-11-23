# -*- coding: utf-8 -*-
from typing import Dict
import asyncio
import json
from typing import Dict, Optional

import httpx
from playwright.async_api import BrowserContext, Page

from tools import utils

from .exception import DataFetchError, IPBlockError



class KuaishouClient:
    def __init__(
            self,
            timeout=10,
            proxies=None,
            *,
            headers: Dict[str, str],
            playwright_page: Page,
            cookie_dict: Dict[str, str],
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://edith.xiaohongshu.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def _pre_headers(self, url: str, data=None):
        pass

    async def request(self, method, url, **kwargs) -> Dict:
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data: Dict = response.json()
        if data["success"]:
            return data.get("data", data.get("success", {}))
        else:
            raise DataFetchError(data.get("msg", None))

    async def get(self, uri: str, params=None) -> Dict:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{'&'.join([f'{k}={v}' for k, v in params.items()])}")
        headers = await self._pre_headers(final_uri)
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers)

    async def post(self, uri: str, data: dict) -> Dict:
        headers = await self._pre_headers(uri, data)
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}",
                                  data=json_str, headers=headers)

    async def ping(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("Begin to ping xhs...")
        ping_flag = False
        try:
            pass
        except Exception as e:
            utils.logger.error(f"Ping xhs failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag
