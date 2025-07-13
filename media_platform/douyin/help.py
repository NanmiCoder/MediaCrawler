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
# @Name    : 程序员阿江-Relakkes
# @Time    : 2024/6/10 02:24
# @Desc    : 获取 a_bogus 参数, 学习交流使用，请勿用作商业用途，侵权联系作者删除

import random

import execjs
from playwright.async_api import Page

douyin_sign_obj = execjs.compile(open('libs/douyin.js', encoding='utf-8-sig').read())

def get_web_id():
    """
    生成随机的webid
    Returns:

    """

    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        else:
            return ''.join(
                [str(int(1e7)), '-', str(int(1e3)), '-', str(int(4e3)), '-', str(int(8e3)), '-', str(int(1e11))]
            )

    web_id = ''.join(
        e(int(x)) if x in '018' else x for x in e(None)
    )
    return web_id.replace('-', '')[:19]



async def get_a_bogus(url: str, params: str, post_data: dict, user_agent: str, page: Page = None):
    """
    获取 a_bogus 参数, 目前不支持post请求类型的签名
    """
    return get_a_bogus_from_js(url, params, user_agent)

def get_a_bogus_from_js(url: str, params: str, user_agent: str):
    """
    通过js获取 a_bogus 参数
    Args:
        url:
        params:
        user_agent:

    Returns:

    """
    sign_js_name = "sign_datail"
    if "/reply" in url:
        sign_js_name = "sign_reply"
    return douyin_sign_obj.call(sign_js_name, params, user_agent)



async def get_a_bogus_from_playright(params: str, post_data: dict, user_agent: str, page: Page):
    """
    通过playright获取 a_bogus 参数
    playwright版本已失效
    Returns:

    """
    if not post_data:
        post_data = ""
    a_bogus = await page.evaluate(
        "([params, post_data, ua]) => window.bdms.init._v[2].p[42].apply(null, [0, 1, 8, params, post_data, ua])",
        [params, post_data, user_agent])

    return a_bogus


def extract_sec_user_id_from_url(url: str) -> str:
    """
    从抖音主页URL中提取sec_user_id
    支持的URL格式:
    1. https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE
    2. https://www.douyin.com/@username (需要特殊处理)
    3. https://v.douyin.com/iXXXXXX/ (短链接，需要进一步解析)
    
    Args:
        url: 抖音用户主页URL
        
    Returns:
        str: sec_user_id 或空字符串（如果是@username格式则返回原始格式）
    """
    import re
    import urllib.parse
    
    if not url or not isinstance(url, str):
        return ""
    
    # 清理URL
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /user/sec_user_id 格式
    user_pattern = r'/user/([A-Za-z0-9_-]+)'
    match = re.search(user_pattern, url)
    if match:
        return match.group(1)
    
    # 方式2: 处理 /@username 格式 - 这种格式需要特殊处理
    # 注意：/@username 格式无法直接获取sec_user_id，需要通过API转换
    at_pattern = r'/@([A-Za-z0-9_.-]+)'
    match = re.search(at_pattern, url)
    if match:
        # 返回特殊标记，让调用方知道这需要进一步处理
        return f"@{match.group(1)}"
    
    # 方式3: 从URL参数中提取 sec_uid
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'sec_uid' in params:
        return params['sec_uid'][0]
    
    # 方式4: 直接作为sec_user_id处理（如果输入的就是sec_user_id）
    # sec_user_id通常是43位字符，以MS4wLjABAAAA开头
    sec_uid_pattern = r'^MS4wLjABAAAA[A-Za-z0-9_-]+$'
    if re.match(sec_uid_pattern, url):
        return url
    
    return ""


async def resolve_any_url_to_sec_user_id(input_str: str, page: Page, dy_client) -> str:
    """
    统一处理所有输入格式，解析出sec_user_id
    支持三种输入格式：
    1. 直接的sec_user_id: MS4wLjABAAAA...
    2. 完整URL: https://www.douyin.com/user/MS4wLjABAAAA... 或 https://www.douyin.com/@username
    3. 短链接: https://v.douyin.com/iXXXXXX/
    
    Args:
        input_str: 用户输入的任意格式
        page: playwright页面对象 
        dy_client: 抖音客户端对象
        
    Returns:
        str: sec_user_id 或空字符串
    """
    import asyncio
    from tools import utils
    
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    utils.logger.info(f"[resolve_any_url_to_sec_user_id] 开始处理输入: {input_str}")
    
    try:
        import re
        
        # 情况1: 直接是sec_user_id
        sec_uid_pattern = r'^MS4wLjABAAAA[A-Za-z0-9_-]+$'
        if re.match(sec_uid_pattern, input_str):
            utils.logger.info(f"[resolve_any_url_to_sec_user_id] 识别为sec_user_id: {input_str}")
            return input_str
        
        # 情况2: 短链接 - 需要先重定向解析
        if 'v.douyin.com' in input_str:
            utils.logger.info(f"[resolve_any_url_to_sec_user_id] 识别为短链接，开始重定向解析: {input_str}")
            resolved_url = await resolve_short_url(input_str, page)
            utils.logger.info(f"[resolve_any_url_to_sec_user_id] 重定向解析结果: {resolved_url}")
            input_str = resolved_url
        
        # 情况3: 完整URL - 提取sec_user_id
        sec_user_id = extract_sec_user_id_from_url(input_str)
        if not sec_user_id:
            utils.logger.error(f"[resolve_any_url_to_sec_user_id] 无法从URL提取sec_user_id: {input_str}")
            return ""
        
        # 处理@username格式
        if sec_user_id.startswith('@'):
            username = sec_user_id[1:]
            utils.logger.info(f"[resolve_any_url_to_sec_user_id] 识别为@username格式，通过API解析: {username}")
            actual_sec_user_id = await dy_client.resolve_username_to_sec_user_id(username)
            if not actual_sec_user_id:
                utils.logger.error(f"[resolve_any_url_to_sec_user_id] 无法解析用户名: {username}")
                return ""
            sec_user_id = actual_sec_user_id
        
        utils.logger.info(f"[resolve_any_url_to_sec_user_id] 最终解析结果: {sec_user_id}")
        return sec_user_id
        
    except Exception as e:
        utils.logger.error(f"[resolve_any_url_to_sec_user_id] 解析失败: {e}")
        return ""


def extract_video_id_from_url(url: str) -> str:
    """
    从抖音视频URL中提取video_id
    支持的URL格式:
    1. https://www.douyin.com/video/7525082444551310602
    2. https://v.douyin.com/iXXXXXX/ (短链接，需要进一步解析)
    
    Args:
        url: 抖音视频URL
        
    Returns:
        str: video_id 或空字符串
    """
    import re
    import urllib.parse
    
    if not url or not isinstance(url, str):
        return ""
    
    # 清理URL
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /video/video_id 格式
    video_pattern = r'/video/(\d+)'
    match = re.search(video_pattern, url)
    if match:
        return match.group(1)
    
    # 方式2: 从URL参数中提取 video_id 或 aweme_id
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'video_id' in params:
        return params['video_id'][0]
    if 'aweme_id' in params:
        return params['aweme_id'][0]
    
    # 方式3: 直接作为video_id处理（如果输入的就是纯数字ID）
    video_id_pattern = r'^\d{19}$'  # 抖音video_id通常是19位数字
    if re.match(video_id_pattern, url):
        return url
    
    return ""


async def resolve_any_video_url_to_id(input_str: str, page: Page) -> str:
    """
    统一处理所有视频输入格式，解析出video_id
    支持三种输入格式：
    1. 直接的video_id: 7525082444551310602
    2. 完整视频URL: https://www.douyin.com/video/7525082444551310602
    3. 短链接: https://v.douyin.com/iXXXXXX/
    
    Args:
        input_str: 用户输入的任意格式
        page: playwright页面对象
        
    Returns:
        str: video_id 或空字符串
    """
    import asyncio
    from tools import utils
    
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    utils.logger.info(f"[resolve_any_video_url_to_id] 开始处理视频输入: {input_str}")
    
    try:
        import re
        
        # 情况1: 直接是video_id（19位数字）
        video_id_pattern = r'^\d{19}$'
        if re.match(video_id_pattern, input_str):
            utils.logger.info(f"[resolve_any_video_url_to_id] 识别为video_id: {input_str}")
            return input_str
        
        # 情况2: 短链接 - 需要先重定向解析
        if 'v.douyin.com' in input_str:
            utils.logger.info(f"[resolve_any_video_url_to_id] 识别为短链接，开始重定向解析: {input_str}")
            resolved_url = await resolve_short_url(input_str, page)
            utils.logger.info(f"[resolve_any_video_url_to_id] 重定向解析结果: {resolved_url}")
            input_str = resolved_url
        
        # 情况3: 完整视频URL - 提取video_id
        video_id = extract_video_id_from_url(input_str)
        if not video_id:
            utils.logger.error(f"[resolve_any_video_url_to_id] 无法从URL提取video_id: {input_str}")
            return ""
        
        utils.logger.info(f"[resolve_any_video_url_to_id] 最终解析结果: {video_id}")
        return video_id
        
    except Exception as e:
        utils.logger.error(f"[resolve_any_video_url_to_id] 解析失败: {e}")
        return ""


async def resolve_short_url(short_url: str, page: Page) -> str:
    """
    解析抖音短链接，获取完整的用户主页URL
    
    Args:
        short_url: 短链接 如 https://v.douyin.com/iXXXXXX/
        page: playwright页面对象
        
    Returns:
        str: 完整的用户主页URL
    """
    import asyncio
    from tools import utils
    
    try:
        if not short_url or 'v.douyin.com' not in short_url:
            return short_url
        
        utils.logger.info(f"[resolve_short_url] 开始解析短链接: {short_url}")
        
        # 清理URL，确保格式正确
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
            
        # 设置页面拦截，监听重定向
        redirected_url = None
        
        async def handle_response(response):
            nonlocal redirected_url
            url = response.url
            # 检查是否是抖音用户主页的重定向
            if 'douyin.com/user/' in url or 'douyin.com/@' in url:
                redirected_url = url
                utils.logger.info(f"[resolve_short_url] 捕获到重定向URL: {url}")
        
        # 设置响应监听器
        page.on('response', handle_response)
        
        try:
            # 访问短链接，等待页面加载完成
            utils.logger.info(f"[resolve_short_url] 正在访问短链接...")
            response = await page.goto(short_url, wait_until='domcontentloaded', timeout=15000)
            
            # 等待一下让重定向完成
            await asyncio.sleep(2)
            
            # 获取最终的URL
            final_url = page.url
            utils.logger.info(f"[resolve_short_url] 页面最终URL: {final_url}")
            
            # 优先使用监听到的重定向URL
            if redirected_url:
                utils.logger.info(f"[resolve_short_url] 使用重定向URL: {redirected_url}")
                return redirected_url
            
            # 如果页面URL包含用户信息，直接使用
            if 'douyin.com/user/' in final_url or 'douyin.com/@' in final_url:
                utils.logger.info(f"[resolve_short_url] 解析成功: {final_url}")
                return final_url
            
            # 尝试从页面内容中提取用户链接
            try:
                # 等待页面完全加载
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # 查找页面中的用户链接
                user_links = await page.query_selector_all('a[href*="/user/"]')
                if user_links:
                    for link in user_links:
                        href = await link.get_attribute('href')
                        if href and '/user/' in href:
                            full_url = f"https://www.douyin.com{href}" if href.startswith('/') else href
                            utils.logger.info(f"[resolve_short_url] 从页面提取到用户链接: {full_url}")
                            return full_url
                
                # 尝试查找当前页面的canonical链接
                canonical = await page.query_selector('link[rel="canonical"]')
                if canonical:
                    href = await canonical.get_attribute('href')
                    if href and ('/user/' in href or '/@' in href):
                        utils.logger.info(f"[resolve_short_url] 从canonical标签获取: {href}")
                        return href
                        
            except Exception as e:
                utils.logger.warning(f"[resolve_short_url] 从页面提取链接失败: {e}")
            
            utils.logger.warning(f"[resolve_short_url] 无法解析短链接，返回最终URL: {final_url}")
            return final_url
            
        finally:
            # 移除事件监听器
            page.remove_listener('response', handle_response)
            
    except Exception as e:
        utils.logger.error(f"[resolve_short_url] 解析短链接失败: {e}")
        return short_url

