import re
import json
import httpx

import config
from base.base_crawler import AbstractCrawler
from tools import utils


class NiukeCrawler(AbstractCrawler):
    """Simple crawler for Niuke discussions"""

    def __init__(self) -> None:
        self.base_url = "https://www.nowcoder.com"
        self.user_agent = utils.get_user_agent()

    async def start(self):
        await self.search()

    async def search(self):
        keyword = config.KEYWORDS.split(",")[0]
        url = f"{self.base_url}/search?type=post&order=default&query={keyword}"
        async with httpx.AsyncClient(headers={"User-Agent": self.user_agent}) as client:
            resp = await client.get(url)
        m = re.search(r"window.__INITIAL_STATE__=(.*?);\(function", resp.text, re.S)
        if not m:
            utils.logger.warning("[NiukeCrawler.search] initial state not found")
            return
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            utils.logger.warning("[NiukeCrawler.search] parse initial state failed")
            return
        items = data.get("store", {}).get("search", {}).get("items", [])
        for item in items:
            title = item.get("title", "")
            utils.logger.info(f"[NiukeCrawler.search] {title}")

    async def launch_browser(self, *args, **kwargs):
        raise NotImplementedError
