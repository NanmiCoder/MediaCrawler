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
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from playwright.async_api import BrowserContext, Page

from base.base_crawler import AbstractApiClient
from tools import utils
from .exception import DataFetchError


class JuejinClient(AbstractApiClient):
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
        self._host = "https://api.juejin.cn"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict

    async def request(self, method, url, **kwargs) -> Any:
        """发送HTTP请求"""
        utils.logger.info(f"[JuejinClient.request] 请求URL: {url}")
        
        try:
            async with httpx.AsyncClient(proxies=self.proxies) as client:
                response = await client.request(
                    method, url, timeout=30.0, **kwargs  # 增加超时时间
                )
            
            utils.logger.info(f"[JuejinClient.request] HTTP状态码: {response.status_code}")
            
            # 检查HTTP状态码
            if response.status_code != 200:
                utils.logger.error(f"[JuejinClient.request] HTTP请求失败: {response.status_code}, 响应: {response.text}")
                raise DataFetchError(f"HTTP请求失败: {response.status_code}")
                
            try:
                data: Dict = response.json()
                utils.logger.info(f"[JuejinClient.request] 响应数据结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            except Exception as e:
                utils.logger.error(f"[JuejinClient.request] JSON解析失败: {e}, 响应内容: {response.text[:200]}")
                raise DataFetchError(f"JSON解析失败: {e}")
            
            # 掘金API的错误检查
            if data.get("err_no") is not None and data.get("err_no") != 0:
                utils.logger.error(f"[JuejinClient.request] API返回错误: {data.get('err_msg', '未知错误')}")
                raise DataFetchError(data.get("err_msg", "请求失败"))
            
            # 返回数据，优先返回data字段，如果没有就返回整个响应
            return data.get("data", data)
            
        except httpx.TimeoutException as e:
            utils.logger.error(f"[JuejinClient.request] 请求超时: {e}")
            raise DataFetchError(f"请求超时: {e}")
        except httpx.RequestError as e:
            utils.logger.error(f"[JuejinClient.request] 网络请求错误: {e}")
            raise DataFetchError(f"网络请求错误: {e}")
        except Exception as e:
            utils.logger.error(f"[JuejinClient.request] 未知错误: {e}")
            import traceback
            utils.logger.error(f"[JuejinClient.request] 异常堆栈: {traceback.format_exc()}")
            raise DataFetchError(f"未知错误: {e}")

    async def pong(self) -> bool:
        """检查客户端连接状态和登录状态"""
        try:
            # 简单检查连接状态，不检查登录状态
            # 登录状态通过页面URL来判断更可靠
            async with httpx.AsyncClient(proxies=self.proxies) as client:
                response = await client.get(
                    "https://juejin.cn", 
                    timeout=self.timeout,
                    headers=self.headers
                )
                return response.status_code == 200
        except Exception:
            return False

    async def update_cookies(self, browser_context: BrowserContext):
        """更新cookies"""
        cookie_str, cookie_dict = utils.convert_cookies(
            await browser_context.cookies()
        )
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_articles(self, keyword: str, page: int = 1, sort_type: str = "comprehensive", cursor: str = "0") -> Dict[str, Any]:
        """搜索文章"""
        uri = "/search_api/v1/search"
        url = f"{self._host}{uri}"
        
        # 使用掘金实际的搜索API参数格式
        payload = {
            "key_word": keyword,
            "id_type": 2,  # 2表示文章类型
            "sort_type": 0 if sort_type == "comprehensive" else 1,  # 0:综合排序, 1:最新
            "cursor": cursor,  # 使用传入的cursor
            "limit": 20,
        }
        
        try:
            utils.logger.info(f"[JuejinClient.search_articles] 请求参数: {payload}")
            response = await self.request("POST", url, json=payload, headers=self.headers)
            utils.logger.info(f"[JuejinClient.search_articles] API原始响应类型: {type(response)}")
            
            # 添加详细的响应结构日志
            if isinstance(response, dict):
                utils.logger.info(f"[JuejinClient.search_articles] 响应键: {list(response.keys())}")
                if "data" in response:
                    data = response["data"]
                    utils.logger.info(f"[JuejinClient.search_articles] data类型: {type(data)}, 长度: {len(data) if isinstance(data, list) else 'N/A'}")
                    # 打印第一个文章的结构用于调试
                    if isinstance(data, list) and len(data) > 0:
                        first_article = data[0]
                        utils.logger.info(f"[JuejinCrawler.search_articles] 第一个文章的键: {list(first_article.keys()) if isinstance(first_article, dict) else 'N/A'}")
                        # 查找可能的文章ID字段
                        if 'result_model' in first_article and isinstance(first_article['result_model'], dict):
                            result_model = first_article['result_model']
                            utils.logger.info(f"[JuejinClient.search_articles] result_model键: {list(result_model.keys()) if isinstance(result_model, dict) else 'N/A'}")
            
            # 确保返回正确的数据结构
            if isinstance(response, list):
                utils.logger.info(f"[JuejinClient.search_articles] 获取到文章数量: {len(response)}")
                return {"data": response, "has_more": len(response) >= 20, "cursor": ""}
            elif isinstance(response, dict):
                data_list = response.get("data", [])
                has_more = response.get("has_more", len(data_list) >= 20)
                next_cursor = response.get("cursor", "")
                utils.logger.info(f"[JuejinClient.search_articles] 获取到文章数量: {len(data_list)}, has_more: {has_more}, cursor: {next_cursor}")
                return {
                    "data": data_list, 
                    "has_more": has_more,
                    "cursor": next_cursor
                }
            else:
                utils.logger.warning(f"[JuejinClient.search_articles] 未知响应格式: {response}")
                return {"data": [], "has_more": False, "cursor": ""}
        except Exception as ex:
            utils.logger.error(f"[JuejinClient.search_articles] 搜索文章失败: {ex}")
            utils.logger.error(f"[JuejinClient.search_articles] 异常类型: {type(ex)}")
            import traceback
            utils.logger.error(f"[JuejinClient.search_articles] 异常堆栈: {traceback.format_exc()}")
            return {"data": [], "has_more": False, "cursor": ""}

    async def get_article_detail(self, article_id: str) -> Dict[str, Any]:
        """获取文章详情"""
        uri = "/content_api/v1/article/detail"
        url = f"{self._host}{uri}"
        
        # 尝试不同的参数格式
        payload = {
            "article_id": article_id,
            "cursor": "0",
            "sort_type": 200
        }
        
        utils.logger.info(f"[JuejinClient.get_article_detail] 请求文章详情，article_id: {article_id}")
        utils.logger.info(f"[JuejinClient.get_article_detail] 请求参数: {payload}")
        
        try:
            response = await self.request("POST", url, json=payload, headers=self.headers)
            return response
        except DataFetchError as e:
            # 如果第一种格式失败，尝试简化的参数格式
            if "参数错误" in str(e):
                utils.logger.info(f"[JuejinClient.get_article_detail] 尝试简化参数格式")
                simple_payload = {"article_id": article_id}
                try:
                    response = await self.request("POST", url, json=simple_payload, headers=self.headers)
                    return response
                except DataFetchError:
                    # 如果还是失败，尝试GET方法
                    utils.logger.info(f"[JuejinClient.get_article_detail] 尝试GET方法")
                    get_url = f"{url}?article_id={article_id}"
                    try:
                        async with httpx.AsyncClient(proxies=self.proxies) as client:
                            response = await client.get(get_url, timeout=30.0, headers=self.headers)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("err_no") == 0:
                                return data.get("data", data)
                    except Exception:
                        pass
            
            utils.logger.error(f"[JuejinClient.get_article_detail] 获取文章详情失败: {e}")
            raise DataFetchError(f"获取文章详情失败: {e}")
        except Exception as ex:
            utils.logger.error(f"[JuejinClient.get_article_detail] 获取文章详情失败: {ex}")
            raise DataFetchError(f"获取文章详情失败: {ex}")

    async def get_article_comments(
        self, article_id: str, cursor: str = "0", limit: int = 20, max_count: int = 100
    ) -> List[Dict[str, Any]]:
        """获取文章评论"""
        uri = "/interact_api/v1/comment/list"
        url = f"{self._host}{uri}"
        
        comments = []
        current_cursor = cursor
        
        while len(comments) < max_count:
            payload = {
                "item_id": article_id,
                "item_type": 2,  # 文章类型
                "cursor": current_cursor,
                "limit": min(limit, max_count - len(comments)),
            }
            
            try:
                response = await self.request("POST", url, json=payload, headers=self.headers)
                comment_list = response.get("data", [])
                
                if not comment_list:
                    break
                    
                comments.extend(comment_list)
                
                # 检查是否有更多评论
                if not response.get("has_more", False):
                    break
                    
                current_cursor = response.get("cursor", "")
                
                # 添加延迟避免请求过快
                await asyncio.sleep(0.5)
                
            except Exception as ex:
                utils.logger.error(f"[JuejinClient.get_article_comments] 获取评论失败: {ex}")
                break
        
        return comments

    async def get_creator_info(self, user_id: str) -> Dict[str, Any]:
        """获取创作者信息"""
        uri = "/user_api/v1/user/get"
        url = f"{self._host}{uri}"
        
        payload = {
            "user_id": user_id,
        }
        
        try:
            response = await self.request("POST", url, json=payload, headers=self.headers)
            return response
        except Exception as ex:
            utils.logger.error(f"[JuejinClient.get_creator_info] 获取创作者信息失败: {ex}")
            raise DataFetchError(f"获取创作者信息失败: {ex}")

    async def get_all_articles_by_creator(
        self, user_id: str, callback=None
    ) -> List[Dict[str, Any]]:
        """获取创作者的所有文章"""
        uri = "/content_api/v1/article/query_list"
        url = f"{self._host}{uri}"
        
        all_articles = []
        cursor = "0"
        
        while True:
            payload = {
                "user_id": user_id,
                "sort_type": 2,  # 按时间排序
                "cursor": cursor,
                "limit": 20,
            }
            
            try:
                response = await self.request("POST", url, json=payload, headers=self.headers)
                articles = response.get("data", [])
                
                if not articles:
                    break
                
                all_articles.extend(articles)
                
                # 如果有回调函数，处理当前批次
                if callback:
                    await callback(articles)
                
                # 检查是否有更多文章
                if not response.get("has_more", False):
                    break
                    
                cursor = response.get("cursor", "")
                
                # 添加延迟
                await asyncio.sleep(1)
                
            except Exception as ex:
                utils.logger.error(f"[JuejinClient.get_all_articles_by_creator] 获取创作者文章失败: {ex}")
                break
        
        return all_articles

    async def get_user_articles(
        self, user_id: str, cursor: str = "0", sort_type: int = 2
    ) -> Dict[str, Any]:
        """获取用户文章列表"""
        uri = "/content_api/v1/article/query_list"
        url = f"{self._host}{uri}"
        
        payload = {
            "user_id": user_id,
            "sort_type": sort_type,  # 2: 按时间排序
            "cursor": cursor,
            "limit": 20,
        }
        
        try:
            response = await self.request("POST", url, json=payload, headers=self.headers)
            return response
        except Exception as ex:
            utils.logger.error(f"[JuejinClient.get_user_articles] 获取用户文章失败: {ex}")
            raise DataFetchError(f"获取用户文章失败: {ex}")

    async def get_tag_info(self, tag_id: str) -> Dict[str, Any]:
        """获取标签信息"""
        uri = "/tag_api/v1/query_tag_detail"
        url = f"{self._host}{uri}"
        
        payload = {
            "tag_id": tag_id,
        }
        
        try:
            response = await self.request("POST", url, json=payload, headers=self.headers)
            return response
        except Exception as ex:
            utils.logger.error(f"[JuejinClient.get_tag_info] 获取标签信息失败: {ex}")
            raise DataFetchError(f"获取标签信息失败: {ex}") 