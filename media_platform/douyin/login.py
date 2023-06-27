import sys
import asyncio

from playwright.async_api import Page
from playwright.async_api import BrowserContext

from tools import utils
from base.base_crawler import AbstractLogin


class DouYinLogin(AbstractLogin):
    async def login_by_cookies(self):
        pass

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: str = None,
                 cookie_str: str = None
                 ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        self.scan_qrcode_time = 60

    async def check_login_state(self):
        """Check if the current login status is successful and return True otherwise return False"""
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        if cookie_dict.get("LOGIN_STATUS") == "1":
            return True
        return False

    async def login_by_qrcode(self):
        """login douyin website and keep webdriver login state"""
        print("Begin login douyin ...")
        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector="xpath=//article[@class='web-login']//img"
        )
        if not base64_qrcode_img:
            if await self.check_login_state():
                return
            # todo ...if this website does not automatically popup login dialog box, we will manual click login button
            print("login failed , have not found qrcode please check ....")
            sys.exit()

        # show login qrcode
        utils.show_qrcode(base64_qrcode_img)

        while self.scan_qrcode_time > 0:
            await asyncio.sleep(1)
            self.scan_qrcode_time -= 1
            print(f"waiting for scan code login, remaining time is {self.scan_qrcode_time} seconds")
            # get login state from browser
            if await self.check_login_state():
                # If the QR code login is successful, you need to wait for a moment.
                # Because there will be a second redirection after successful login
                # executing JS during this period may be performed in a Page that has already been destroyed.
                wait_for_seconds = 5
                print(f"Login successful then wait for {wait_for_seconds} seconds redirect ...")
                while wait_for_seconds > 0:
                    await asyncio.sleep(1)
                    print(f"remaining wait {wait_for_seconds} seconds ...")
                    wait_for_seconds -= 1
                break
        else:
            sys.exit()

    async def login_by_mobile(self):
        # todo implement login by mobile
        pass

    async def begin(self):
        if self.login_type == "qrcode":
            await self.login_by_qrcode()
        elif self.login_type == "phone":
            await self.login_by_mobile()
        elif self.login_type == "cookies":
            await self.login_by_cookies()
        else:
            raise ValueError("Invalid Login Type Currently only supported qrcode or phone ...")
