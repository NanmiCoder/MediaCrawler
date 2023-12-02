# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    :
from base.base_crawler import AbstractLogin


class BilibiliLogin(AbstractLogin):
    async def begin(self):
        pass

    async def login_by_qrcode(self):
        pass

    async def login_by_mobile(self):
        pass

    async def login_by_cookies(self):
        pass
