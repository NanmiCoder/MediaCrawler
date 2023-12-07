from abc import ABC, abstractmethod

from proxy.proxy_account_pool import AccountPool


class AbstractCrawler(ABC):
    @abstractmethod
    def init_config(self, platform: str, login_type: str, crawler_type: str):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def search(self):
        pass


class AbstractLogin(ABC):
    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def login_by_qrcode(self):
        pass

    @abstractmethod
    async def login_by_mobile(self):
        pass

    @abstractmethod
    async def login_by_cookies(self):
        pass
