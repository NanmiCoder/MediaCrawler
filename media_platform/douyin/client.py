from typing import Optional, Dict

import httpx
from playwright.async_api import Page


class DOUYINClient:
    def __init__(
            self,
            timeout=10,
            proxies=None,
            headers: Optional[Dict] = None,
            playwright_page: Page = None,
            cookie_dict: Dict = None
    ):
        self.proxies = proxies
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.douyin.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def _pre_params(self, url: str, data=None):
        pass

    async def request(self, method, url, **kwargs):
        async with httpx.AsyncClient(proxies=self.proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        data = response.json()
        if data["success"]:
            return data.get("data", data.get("success"))
        else:
            pass

    async def get(self, uri: str, params=None):
        pass

    async def post(self, uri: str, data: dict):
        pass
