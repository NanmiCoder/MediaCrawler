# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import asyncio
import functools
import sys
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from cache.cache_factory import CacheFactory
from tools import utils


class JuejinLogin(AbstractLogin):

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self, no_logged_in_session: str) -> bool:
        """
        检查当前登录状态是否成功，成功返回True，否则返回False
        retry装饰器会在返回值为False时重试600次，重试间隔为1秒
        如果达到最大重试次数，抛出RetryError
        """
        if "请通过验证" in await self.context_page.content():
            utils.logger.info("[JuejinLogin.check_login_state] 登录过程中出现验证码，请手动验证")

        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        
        # 掘金的登录状态通过多个cookie判断
        current_session_id = cookie_dict.get("sessionid")
        current_token = cookie_dict.get("token") 
        current_passport = cookie_dict.get("passport_csrf_token")
        
        # 检查是否有关键的登录cookie，并且与初始状态不同
        if current_session_id and current_session_id != no_logged_in_session:
            return True
        if current_token and current_token != no_logged_in_session:
            return True
        if current_passport and current_passport != no_logged_in_session:
            return True
            
        return False

    async def begin(self):
        """开始登录掘金"""
        utils.logger.info("[JuejinLogin.begin] 开始登录掘金...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[JuejinLogin.begin] 无效的登录类型，当前只支持 qrcode、phone 或 cookie")

    async def login_by_mobile(self):
        """通过手机号登录掘金"""
        utils.logger.info("[JuejinLogin.login_by_mobile] 开始通过手机号登录掘金...")
        
        try:
            # 导航到登录页面
            await self.context_page.goto("https://juejin.cn/login")
            await asyncio.sleep(2)
            
            # 点击手机号登录选项
            phone_login_btn = await self.context_page.wait_for_selector(
                selector='xpath=//div[contains(@class, "login-type")]//span[text()="手机号登录"]',
                timeout=10000
            )
            await phone_login_btn.click()
            await asyncio.sleep(1)
            
            # 输入手机号
            phone_input = await self.context_page.wait_for_selector(
                selector='input[placeholder*="手机号"]',
                timeout=5000
            )
            await phone_input.fill(self.login_phone)
            await asyncio.sleep(0.5)
            
            # 点击发送验证码
            send_code_btn = await self.context_page.wait_for_selector(
                selector='button[class*="send-btn"]',
                timeout=5000
            )
            await send_code_btn.click()
            
            # 等待验证码输入框
            code_input = await self.context_page.wait_for_selector(
                selector='input[placeholder*="验证码"]',
                timeout=5000
            )
            
            # 获取登录前的session状态
            current_cookie = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(current_cookie)
            no_logged_in_session = cookie_dict.get("sessionid", "")
            
            # 从缓存中获取验证码
            cache_client = CacheFactory.create_cache(config.CACHE_TYPE_MEMORY)
            max_get_sms_code_time = 60 * 2  # 最长获取验证码的时间为2分钟
            
            while max_get_sms_code_time > 0:
                utils.logger.info(f"[JuejinLogin.login_by_mobile] 从缓存获取验证码，剩余时间 {max_get_sms_code_time}s ...")
                await asyncio.sleep(1)
                sms_code_key = f"juejin_{self.login_phone}"
                sms_code_value = cache_client.get(sms_code_key)
                
                if not sms_code_value:
                    max_get_sms_code_time -= 1
                    continue
                
                # 输入验证码
                await code_input.fill(value=sms_code_value.decode())
                await asyncio.sleep(0.5)
                
                # 点击登录按钮
                login_btn = await self.context_page.wait_for_selector(
                    selector='button[class*="login-btn"]',
                    timeout=5000
                )
                await login_btn.click()
                break
            
            # 检查登录状态
            try:
                await self.check_login_state(no_logged_in_session)
            except RetryError:
                utils.logger.info("[JuejinLogin.login_by_mobile] 手机号登录掘金失败...")
                sys.exit()
                
        except Exception as e:
            utils.logger.error(f"[JuejinLogin.login_by_mobile] 手机号登录过程中出现错误: {e}")
            # 如果手机号登录失败，可以尝试其他登录方式
            utils.logger.info("[JuejinLogin.login_by_mobile] 尝试其他登录方式...")

        wait_redirect_seconds = 5
        utils.logger.info(f"[JuejinLogin.login_by_mobile] 登录成功，等待 {wait_redirect_seconds} 秒重定向...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_qrcode(self):
        """通过二维码登录掘金"""
        utils.logger.info("[JuejinLogin.login_by_qrcode] 开始通过二维码登录掘金...")
        
        try:
            # 导航到登录页面
            utils.logger.info("[JuejinLogin.login_by_qrcode] 导航到登录页面")
            await self.context_page.goto("https://juejin.cn/login", timeout=30000)
            await asyncio.sleep(3)
            
            # 检查页面是否正确加载
            page_title = await self.context_page.title()
            utils.logger.info(f"[JuejinLogin.login_by_qrcode] 页面标题: {page_title}")
            
            # 检查是否已经在登录页面
            current_url = self.context_page.url
            utils.logger.info(f"[JuejinLogin.login_by_qrcode] 当前URL: {current_url}")
            
            # 如果已经在首页，说明已经登录成功
            if "juejin.cn" in current_url and "/login" not in current_url:
                utils.logger.info("[JuejinLogin.login_by_qrcode] 检测到已经登录成功，跳过二维码登录")
                return
            
            # 等待页面完全加载
            await self.context_page.wait_for_load_state('networkidle', timeout=10000)
            
            # 首先尝试找到登录表单或登录区域
            try:
                # 等待登录容器出现
                await self.context_page.wait_for_selector('.login-box, .login-container, .passport-login-container', timeout=10000)
                utils.logger.info("[JuejinLogin.login_by_qrcode] 找到登录容器")
            except:
                utils.logger.warning("[JuejinLogin.login_by_qrcode] 未找到登录容器，继续尝试")
            
            # 寻找并点击微信登录选项来激活二维码
            wechat_login_selectors = [
                'xpath=//span[contains(text(), "微信登录")]',
                'xpath=//div[contains(text(), "微信登录")]', 
                'xpath=//button[contains(text(), "微信")]',
                '.wechat-login, .weixin-login',
                '[data-v-5244ef91][data-v-ce04894c]'  # 根据日志中的属性
            ]
            
            wechat_btn_found = False
            for selector in wechat_login_selectors:
                try:
                    wechat_btn = await self.context_page.wait_for_selector(selector, timeout=3000)
                    if wechat_btn:
                        utils.logger.info(f"[JuejinLogin.login_by_qrcode] 找到微信登录按钮: {selector}")
                        await wechat_btn.click()
                        await asyncio.sleep(3)  # 等待二维码加载
                        wechat_btn_found = True
                        break
                except:
                    continue
            
            if not wechat_btn_found:
                utils.logger.info("[JuejinLogin.login_by_qrcode] 未找到微信登录按钮，尝试直接查找二维码")
            
            # 查找登录二维码 - 包括隐藏的元素
            qrcode_selectors = [
                'xpath=//img[contains(@alt, "微信扫一扫")]',  # 根据日志中的实际内容
                'xpath=//img[contains(@class, "qrcode")]',
                'xpath=//img[contains(@src, "qrcode")]',
                'xpath=//canvas[@class="qrcode"]',
                '.login-qrcode img, .qrcode-container img'
            ]
            
            base64_qrcode_img = None
            for selector in qrcode_selectors:
                try:
                    # 等待元素出现，不管是否可见
                    await self.context_page.wait_for_selector(selector, timeout=5000, state='attached')
                    
                    # 尝试使元素可见
                    try:
                        await self.context_page.evaluate(f'''
                            const elements = document.querySelectorAll("{selector.replace("xpath=", "")}");
                            elements.forEach(el => {{
                                if (el) {{
                                    el.style.display = 'block';
                                    el.style.visibility = 'visible';
                                    el.style.opacity = '1';
                                }}
                            }});
                        ''')
                        await asyncio.sleep(1)
                    except:
                        pass
                    
                    base64_qrcode_img = await utils.find_login_qrcode(
                        self.context_page,
                        selector=selector
                    )
                    if base64_qrcode_img:
                        utils.logger.info(f"[JuejinLogin.login_by_qrcode] 找到二维码: {selector}")
                        break
                except Exception as e:
                    utils.logger.debug(f"[JuejinLogin.login_by_qrcode] 选择器 {selector} 失败: {e}")
                    continue
            
            if not base64_qrcode_img:
                utils.logger.error("[JuejinLogin.login_by_qrcode] 无法找到登录二维码")
                # 截图调试
                await self.context_page.screenshot(path="debug_login_page.png")
                utils.logger.info("[JuejinLogin.login_by_qrcode] 已保存调试截图: debug_login_page.png")
                sys.exit()

            # 获取未登录时的session状态
            current_cookie = await self.browser_context.cookies()
            _, cookie_dict = utils.convert_cookies(current_cookie)
            no_logged_in_session = cookie_dict.get("sessionid", "")

            # 显示登录二维码
            partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
            asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

            utils.logger.info(f"[JuejinLogin.login_by_qrcode] 等待扫码登录，剩余时间120秒")
            
            try:
                await self.check_login_state(no_logged_in_session)
            except RetryError:
                utils.logger.info("[JuejinLogin.login_by_qrcode] 二维码登录掘金失败...")
                sys.exit()

        except Exception as e:
            utils.logger.error(f"[JuejinLogin.login_by_qrcode] 二维码登录过程中出现错误: {e}")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[JuejinLogin.login_by_qrcode] 登录成功，等待 {wait_redirect_seconds} 秒重定向...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """通过cookies登录掘金"""
        utils.logger.info("[JuejinLogin.login_by_cookies] 开始通过cookie登录掘金...")
        
        try:
            cookie_dict = utils.convert_str_cookie_to_dict(self.cookie_str)
            
            for key, value in cookie_dict.items():
                # 掘金主要的认证cookie包括sessionid, token等
                if key in ["sessionid", "token", "_ga", "_gid", "MONITOR_WEB_ID"]:
                    await self.browser_context.add_cookies([{
                        'name': key,
                        'value': value,
                        'domain': ".juejin.cn",
                        'path': "/"
                    }])
            
            # 刷新页面以应用cookies
            await self.context_page.reload()
            await asyncio.sleep(2)
            
            utils.logger.info("[JuejinLogin.login_by_cookies] Cookie登录完成")
            
        except Exception as e:
            utils.logger.error(f"[JuejinLogin.login_by_cookies] Cookie登录失败: {e}")
            raise e 