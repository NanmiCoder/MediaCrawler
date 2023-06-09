from abc import ABC, abstractmethod


class Crawler(ABC):
    @abstractmethod
    def init_config(self, **kwargs):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def login(self):
        pass

    @abstractmethod
    async def search_posts(self):
        pass

    @abstractmethod
    async def get_comments(self, item_id: int):
        pass
