# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/24 17:37
# @Desc    :

import re
import urllib.parse
from typing import Dict, List
from playwright.async_api import Page


def filter_search_result_card(card_list: List[Dict]) -> List[Dict]:
    """
    过滤微博搜索的结果，只保留card_type为9类型的数据
    :param card_list:
    :return:
    """
    note_list: List[Dict] = []
    for card_item in card_list:
        if card_item.get("card_type") == 9:
            note_list.append(card_item)
        if len(card_item.get("card_group", [])) > 0:
            card_group = card_item.get("card_group")
            for card_group_item in card_group:
                if card_group_item.get("card_type") == 9:
                    note_list.append(card_group_item)

    return note_list


def validate_weibo_post_id(post_id: str) -> bool:
    """
    验证微博帖子ID的有效性
    微博帖子ID通常是10-20位数字
    Args:
        post_id: 要验证的帖子ID字符串
    Returns:
        bool: 帖子ID是否有效
    """
    if not post_id or not isinstance(post_id, str):
        return False
    
    # 微博帖子ID应该是纯数字，长度在10-20位之间
    if not re.match(r'^\d{10,20}$', post_id):
        return False
    
    return True


def validate_weibo_user_id(user_id: str) -> bool:
    """
    验证微博用户ID的有效性
    微博用户ID通常是7-15位数字
    Args:
        user_id: 要验证的用户ID字符串
    Returns:
        bool: 用户ID是否有效
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    # 微博用户ID应该是纯数字，长度在7-15位之间
    if not re.match(r'^\d{7,15}$', user_id):
        return False
    
    return True


def extract_post_id_from_url(url: str) -> str:
    """
    从微博帖子URL中提取post_id
    支持的格式：
    1. https://weibo.com/user_id/post_id
    2. https://m.weibo.cn/detail/post_id
    3. https://m.weibo.cn/status/post_id
    4. 直接的post_id
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从桌面版分享链接中提取 https://weibo.com/user_id/post_id
    # 分别处理不同的格式，确保精确匹配
    
    # 1a. 处理 weibo.com/u/user_id/post_id 格式
    u_desktop_pattern = r'weibo\.com/u/(?:\d+|[a-zA-Z0-9_-]+)/(\d{10,20})(?:\?|$|/)'
    match = re.search(u_desktop_pattern, url)
    if match:
        post_id = match.group(1)
        if validate_weibo_post_id(post_id):
            return post_id
    
    # 1b. 处理 weibo.com/user_id/post_id 格式（但要确保不是以/u/开头的用户主页）
    # 只有当路径明确包含两个部分且不以u开头时才匹配
    path_parts = urllib.parse.urlparse(url).path.strip('/').split('/')
    if 'weibo.com' in url and len(path_parts) == 2 and path_parts[0] != 'u':
        potential_post_id = path_parts[1]
        if validate_weibo_post_id(potential_post_id):
            return potential_post_id
    
    # 方式2: 从手机版URL中提取 https://m.weibo.cn/detail/post_id
    mobile_detail_pattern = r'm\.weibo\.cn/detail/(\d{10,20})'
    match = re.search(mobile_detail_pattern, url)
    if match:
        post_id = match.group(1)
        if validate_weibo_post_id(post_id):
            return post_id
    
    # 方式3: 从手机版状态URL中提取 https://m.weibo.cn/status/post_id
    mobile_status_pattern = r'm\.weibo\.cn/status/(\d{10,20})'
    match = re.search(mobile_status_pattern, url)
    if match:
        post_id = match.group(1)
        if validate_weibo_post_id(post_id):
            return post_id
    
    # 方式4: 从URL参数中提取
    if '?' in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'id' in params:
            post_id = params['id'][0]
            if validate_weibo_post_id(post_id):
                return post_id
        if 'mid' in params:
            post_id = params['mid'][0]
            if validate_weibo_post_id(post_id):
                return post_id
    
    # 方式5: 直接作为post_id处理（如果输入的就是纯ID）
    if validate_weibo_post_id(url):
        return url
    
    return ""


def extract_user_id_from_url(url: str) -> str:
    """
    从微博用户主页URL中提取user_id
    支持的格式：
    1. https://weibo.com/u/user_id
    2. https://weibo.com/user_id
    3. https://m.weibo.cn/u/user_id
    4. https://m.weibo.cn/profile/user_id
    5. 直接的user_id
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从 /u/user_id 格式中提取
    u_pattern = r'/u/(\d{7,15})'
    match = re.search(u_pattern, url)
    if match:
        user_id = match.group(1)
        if validate_weibo_user_id(user_id):
            return user_id
    
    # 方式2: 从 /profile/user_id 格式中提取
    profile_pattern = r'/profile/(\d{7,15})'
    match = re.search(profile_pattern, url)
    if match:
        user_id = match.group(1)
        if validate_weibo_user_id(user_id):
            return user_id
    
    # 方式3: 从桌面版主页URL中提取 https://weibo.com/user_id（但要排除帖子URL）
    if 'weibo.com' in url and '/u/' not in url and '/status/' not in url:
        # 检查是否是 https://weibo.com/user_id/post_id 格式
        path_parts = urllib.parse.urlparse(url).path.strip('/').split('/')
        if len(path_parts) == 1 and path_parts[0].isdigit():
            user_id = path_parts[0]
            if validate_weibo_user_id(user_id):
                return user_id
        elif len(path_parts) == 2:
            # 可能是 user_id/post_id 格式，只取user_id
            potential_user_id = path_parts[0]
            if validate_weibo_user_id(potential_user_id):
                return potential_user_id
    
    # 方式4: 从URL参数中提取
    if '?' in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'uid' in params:
            user_id = params['uid'][0]
            if validate_weibo_user_id(user_id):
                return user_id
        if 'user_id' in params:
            user_id = params['user_id'][0]
            if validate_weibo_user_id(user_id):
                return user_id
    
    # 方式5: 直接作为user_id处理（如果输入的就是纯ID）
    if validate_weibo_user_id(url):
        return url
    
    return ""


async def resolve_short_url(url: str, page: Page) -> str:
    """
    解析微博短链接，获取重定向后的长链接
    微博的短链接通常会重定向到手机版页面
    """
    if not url or not url.startswith("http"):
        return url
    
    try:
        import random
        import asyncio
        
        # 减少等待时间
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # 收集重定向URL
        redirect_urls = []
        final_url = None
        
        def handle_response(response):
            nonlocal final_url
            current_url = response.url
            redirect_urls.append(current_url)
            
            # 检查是否是我们需要的微博页面
            if 'm.weibo.cn' in current_url and ('/detail/' in current_url or '/status/' in current_url):
                final_url = current_url
                print(f"[resolve_short_url] 找到微博帖子页面: {current_url}")
            elif 'weibo.com' in current_url and ('/' in current_url.split('weibo.com/')[-1]):
                final_url = current_url
                print(f"[resolve_short_url] 找到微博页面: {current_url}")
        
        page.on('response', handle_response)
        
        # 设置用户代理
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 访问短链接
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=10000)
        except Exception as e:
            print(f"[resolve_short_url] 页面访问超时: {e}")
            return url
        
        # 短暂等待重定向完成
        await asyncio.sleep(random.uniform(1, 2))
        
        # 移除监听器
        page.remove_listener('response', handle_response)
        
        # 如果找到了微博页面URL
        if final_url:
            print(f"[resolve_short_url] 微博短链接解析成功: {url} -> {final_url}")
            return final_url
        
        # 检查当前页面URL
        current_url = page.url
        print(f"[resolve_short_url] 当前页面URL: {current_url}")
        
        if 'weibo.c' in current_url or 'm.weibo.cn' in current_url:
            print(f"[resolve_short_url] 从当前页面URL获取微博链接: {current_url}")
            return current_url
        
        # 打印调试信息
        print(f"[resolve_short_url] 重定向路径: {' -> '.join(redirect_urls)}")
        print(f"[resolve_short_url] 最终页面: {current_url}")
            
    except Exception as e:
        print(f"[resolve_short_url] 解析微博短链接失败: {e}")
        print(f"[resolve_short_url] 建议使用完整URL或直接post_id避免此问题")
    
    return url


async def resolve_any_post_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析微博帖子输入，支持多种格式
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接是post_id
    post_id = extract_post_id_from_url(input_str)
    if post_id:
        print(f"[resolve_any_post_url_to_id] 直接提取到post_id: {post_id}")
        return post_id
    
    # 情况2: 短链接 - 需要先重定向解析
    if input_str.startswith('http') and ('t.cn' in input_str or 'weibo.cn' in input_str):
        print(f"[resolve_any_post_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_post_url_to_id] 短链接解析结果: {resolved_url}")
            # 尝试从解析后的URL提取post_id
            post_id = extract_post_id_from_url(resolved_url)
            if post_id:
                print(f"[resolve_any_post_url_to_id] 从解析后的URL提取到post_id: {post_id}")
                return post_id
    
    # 情况3: 完整URL - 提取post_id
    if input_str.startswith('http') and ('weibo.com' in input_str or 'm.weibo.cn' in input_str):
        post_id = extract_post_id_from_url(input_str)
        if post_id:
            print(f"[resolve_any_post_url_to_id] 从完整URL提取到post_id: {post_id}")
            return post_id
    
    print(f"[resolve_any_post_url_to_id] 无法从输入中提取post_id: {input_str}")
    return ""


async def resolve_any_user_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析微博用户输入，支持多种格式
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接是user_id
    user_id = extract_user_id_from_url(input_str)
    if user_id:
        print(f"[resolve_any_user_url_to_id] 直接提取到user_id: {user_id}")
        return user_id
    
    # 情况2: 短链接 - 需要先重定向解析
    if input_str.startswith('http') and ('t.cn' in input_str or 'weibo.cn' in input_str):
        print(f"[resolve_any_user_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_user_url_to_id] 短链接解析结果: {resolved_url}")
            return extract_user_id_from_url(resolved_url)
    
    # 情况3: 完整URL - 提取user_id
    if input_str.startswith('http') and ('weibo.com' in input_str or 'm.weibo.cn' in input_str):
        user_id = extract_user_id_from_url(input_str)
        if user_id:
            print(f"[resolve_any_user_url_to_id] 从完整URL提取到user_id: {user_id}")
            return user_id
    
    print(f"[resolve_any_user_url_to_id] 无法从输入中提取user_id: {input_str}")
    return ""
