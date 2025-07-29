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
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)
from tenacity import RetryError

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
import store.juejin as juejin_store
from store.juejin.juejin_store_impl import JuejinStoreFactory
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import JuejinClient
from .exception import DataFetchError
from .login import JuejinLogin


class JuejinCrawler(AbstractCrawler):
    platform: str
    login_type: str
    crawler_type: str
    context_page: Page
    juejin_client: JuejinClient
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://juejin.cn"
        self.login_url = "https://juejin.cn/login"

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 启动浏览器
            if config.CRAWLER_TYPE == "search":
                utils.logger.info("[JuejinCrawler] 使用标准模式启动浏览器")
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy=playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
            else:
                utils.logger.info("[JuejinCrawler] 使用CDP模式启动浏览器")
                # CDP模式代码（如果需要）
                pass

            # 创建页面
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            # 创建掘金客户端
            self.juejin_client = await self.create_juejin_client(httpx_proxy_format)
            
            # 检查当前页面URL来判断是否需要登录
            current_url = self.context_page.url
            utils.logger.info(f"[JuejinCrawler.start] 当前页面URL: {current_url}")
            
            # 如果页面重定向到登录页面，或者无法正常访问，则需要登录
            if "/login" in current_url or not await self.juejin_client.pong():
                utils.logger.info("[JuejinCrawler.start] 需要登录，导航到登录页面")
                await self.context_page.goto(self.login_url, timeout=30000)
                
                login_obj = JuejinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.juejin_client.update_cookies(browser_context=self.browser_context)
            else:
                utils.logger.info("[JuejinCrawler.start] 检测到已登录状态，跳过登录步骤")

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # 搜索指定关键字
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # 获取指定文章详情
                await self.get_specified_articles()
            else:
                pass

            utils.logger.info("[JuejinCrawler.start] 掘金爬虫任务执行完成")

    async def search(self) -> None:
        """搜索掘金文章"""
        utils.logger.info("[JuejinCrawler.search] 开始搜索掘金文章")
        keywords = config.KEYWORDS.split(",")
        
        for keyword in keywords:
            utils.logger.info(f"[JuejinCrawler.search] 开始搜索关键词: {keyword}")
            source_keyword_var.set(keyword)
            
            page = 1
            juejin_limit_count = 20  # 掘金每页固定20篇文章
            if config.CRAWLER_MAX_NOTES_COUNT < juejin_limit_count:
                config.CRAWLER_MAX_NOTES_COUNT = juejin_limit_count
            
            total_got_count = 0  # 已获取的文章总数
            current_cursor = "0"  # 初始cursor
            
            while total_got_count < config.CRAWLER_MAX_NOTES_COUNT:
                if config.CRAWLER_TYPE == "search":
                    try:
                        utils.logger.info(f"[JuejinCrawler.search] 搜索第{page}页，cursor: {current_cursor}")
                        
                        # 搜索文章
                        articles_res = await self.juejin_client.search_articles(
                            keyword=keyword,
                            page=page,
                            sort_type=config.SORT_TYPE if hasattr(config, 'SORT_TYPE') else 'comprehensive',
                            cursor=current_cursor
                        )
                        
                        if not articles_res or not articles_res.get("data", []):
                            utils.logger.info("没有更多内容!")
                            break
                        
                        # 获取文章列表
                        articles_data = articles_res.get("data", [])
                        utils.logger.info(f"[JuejinCrawler.search] 第{page}页获取到{len(articles_data)}篇文章")
                        
                        # 处理文章数据
                        article_ids = []  # 用于存储文章ID
                        
                        for idx, article in enumerate(articles_data):
                            # 从掘金搜索API的实际响应结构中提取文章ID
                            article_id = None
                            
                            # 掘金搜索API返回的结构：result_model 包含实际的文章数据
                            if 'result_model' in article and isinstance(article['result_model'], dict):
                                result_model = article['result_model']
                                
                                # 尝试从result_model中提取文章ID
                                possible_id_fields = ["article_id", "object_id", "id", "item_id", "content_id"]
                                for field in possible_id_fields:
                                    if field in result_model and result_model.get(field):
                                        article_id = str(result_model[field])
                                        utils.logger.info(f"[JuejinCrawler.search] 找到文章ID: {field}={article_id}")
                                        break
                                
                                # 直接从搜索结果创建文章数据
                                if article_id:
                                    article_info = result_model.get('article_info', {})
                                    author_info = result_model.get('author_user_info', {})
                                    
                                    # 创建文章数据
                                    article_data = {
                                        "article_id": article_id,
                                        "title": article_info.get('title', ''),
                                        "brief_content": article_info.get('brief_content', ''),
                                        "cover_image": article_info.get('cover_image', ''),
                                        "view_count": result_model.get('user_interact', {}).get('read_count', 0),
                                        "digg_count": result_model.get('user_interact', {}).get('digg_count', 0),
                                        "comment_count": result_model.get('user_interact', {}).get('comment_count', 0),
                                        "collect_count": result_model.get('user_interact', {}).get('collect_count', 0),
                                        "created_time": article_info.get('ctime', 0),
                                        "updated_time": article_info.get('mtime', 0),
                                        "source_keyword": keyword,
                                        "author_id": author_info.get('user_id', ''),
                                        "author_name": author_info.get('user_name', ''),
                                        "author_avatar": author_info.get('avatar_large', ''),
                                        "author_description": author_info.get('description', ''),
                                        "category_name": result_model.get('category', {}).get('category_name', ''),
                                        "tags": [tag.get('tag_name', '') for tag in result_model.get('tags', [])],
                                    }
                                    
                                    # 保存文章数据
                                    await juejin_store.update_juejin_article(article_data)
                                    article_ids.append(article_id)
                                    utils.logger.info(f"[JuejinCrawler.search] 成功保存文章: {article_id}")
                            
                            if not article_id:
                                utils.logger.warning(f"[JuejinCrawler.search] 第{idx+1}篇文章未找到有效ID，跳过")
                                continue
                        
                        utils.logger.info(f"[JuejinCrawler.search] 成功处理了{len(article_ids)}篇文章详情")
                        
                        # 更新总计数
                        total_got_count += len(article_ids)
                        utils.logger.info(f"[JuejinCrawler.search] 已获取文章总数: {total_got_count}/{config.CRAWLER_MAX_NOTES_COUNT}")
                        
                        # 获取评论
                        await self.batch_get_article_comments(article_ids)
                        
                        # 检查是否有更多页面
                        if not articles_res.get("has_more", False):
                            utils.logger.info("已获取所有页面内容!")
                            break
                        
                        # 更新cursor为下一页的cursor
                        next_cursor = articles_res.get("cursor", "")
                        if not next_cursor:
                            utils.logger.info("没有下一页cursor，结束搜索!")
                            break
                        current_cursor = next_cursor
                        
                        # 检查是否达到最大数量限制
                        if total_got_count >= config.CRAWLER_MAX_NOTES_COUNT:
                            utils.logger.info(f"已达到最大抓取数量限制: {config.CRAWLER_MAX_NOTES_COUNT}")
                            break
                            
                        page += 1
                        await asyncio.sleep(1)  # 添加延时避免请求过快
                        
                    except DataFetchError as ex:
                        utils.logger.error(f"[JuejinCrawler.search] 获取第{page}页数据失败: {ex}")
                        break
                    except Exception as ex:
                        utils.logger.error(f"[JuejinCrawler.search] 第{page}页处理异常: {ex}")
                        break

    async def get_specified_articles(self):
        """获取指定文章详情"""
        pass

    async def batch_get_article_comments(self, article_ids: List[str]) -> None:
        """批量获取文章评论"""
        utils.logger.info(f"[JuejinCrawler.batch_get_article_comments] 开始获取评论，文章数量: {len(article_ids)}")
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info("[JuejinCrawler.batch_get_article_comments] 未开启评论获取功能")
            return

        # 这里可以添加评论获取逻辑
        pass

    async def create_juejin_client(self, httpx_proxy: Optional[str]) -> JuejinClient:
        """创建掘金客户端"""
        utils.logger.info("[JuejinCrawler.create_juejin_client] 开始创建掘金客户端")
        
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        juejin_client_obj = JuejinClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Origin": "https://juejin.cn",
                "Referer": "https://juejin.cn/",
                "Content-Type": "application/json",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return juejin_client_obj

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict] = None,
        user_agent: Optional[str] = None,
        headless: bool = True,
    ) -> BrowserContext:
        """启动浏览器"""
        utils.logger.info("[JuejinCrawler.launch_browser] 开始创建浏览器上下文.")
        
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", "juejin_user_data_dir")
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-blink-features=AutomationControlled"
                ],
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
            return browser_context 