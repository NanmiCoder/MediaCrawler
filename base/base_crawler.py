from abc import ABC, abstractmethod


class AbstractCrawler(ABC):
    @abstractmethod
    def init_config(self, **kwargs):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def search_posts(self):
        pass

    @abstractmethod
    async def get_comments(self, item_id: int):
        pass


class AbstractLogin(ABC):
    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def check_login_state(self):
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
