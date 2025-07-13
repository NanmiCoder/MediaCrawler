# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import re
import urllib.parse
from playwright.async_api import Page


def validate_kuaishou_id(id_str: str, id_type: str = "auto") -> bool:
    """
    验证快手ID的有效性
    Args:
        id_str: 要验证的ID字符串
        id_type: ID类型 ("video", "user", "auto")
    Returns:
        bool: ID是否有效
    """
    if not id_str or not isinstance(id_str, str):
        return False
    
    # 基础格式验证：10-20位字母数字组合
    if not re.match(r'^[a-zA-Z0-9_-]{10,20}$', id_str):
        return False
    
    # 必须包含字母和数字
    has_letter = any(c.isalpha() for c in id_str)
    has_digit = any(c.isdigit() for c in id_str)
    
    if not (has_letter and has_digit):
        return False
    
    # 特殊模式验证（根据观察到的快手ID特征）
    if id_type == "video":
        # 视频ID通常以特定模式开始
        return len(id_str) >= 11
    elif id_type == "user":
        # 用户ID通常以特定模式开始
        return len(id_str) >= 10
    else:
        # 自动模式：基础验证即可
        return True


def distinguish_id_type(id_str: str, url_context: str = "") -> str:
    """
    根据上下文区分ID类型
    Args:
        id_str: ID字符串
        url_context: URL上下文
    Returns:
        str: "video" 或 "user" 或 "unknown"
    """
    if not id_str:
        return "unknown"
    
    # 根据URL路径判断
    if "/short-video/" in url_context or "/video/" in url_context:
        return "video"
    elif "/profile/" in url_context or "/u/" in url_context:
        return "user"
    
    # 根据ID特征判断（这里可以根据实际观察到的模式调整）
    if len(id_str) >= 15:
        return "video"  # 视频ID通常较长
    elif len(id_str) <= 12:
        return "user"   # 用户ID通常较短
    
    return "unknown"


def extract_video_id_from_url(url: str) -> str:
    """
    从快手视频URL中提取video_id
    快手视频ID特点：通常是字母数字组合，长度10-20位
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /short-video/video_id 格式
    video_pattern = r'/short-video/([a-zA-Z0-9_-]+)'
    match = re.search(video_pattern, url)
    if match:
        video_id = match.group(1)
        # 使用新的验证函数
        if validate_kuaishou_id(video_id, "video"):
            return video_id
    
    # 方式2: 从URL参数中提取 video_id 或 photoId
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'photoId' in params:
        photo_id = params['photoId'][0]
        if validate_kuaishou_id(photo_id, "video"):
            return photo_id
    if 'video_id' in params:
        video_id = params['video_id'][0]
        if validate_kuaishou_id(video_id, "video"):
            return video_id
    
    # 方式3: 直接作为video_id处理（如果输入的就是纯ID）
    if validate_kuaishou_id(url, "video"):
        return url
    
    return ""


def extract_creator_id_from_url(url: str) -> str:
    """
    从快手创作者主页URL中提取creator_id
    快手用户ID特点：通常是字母数字组合，长度10-20位，与视频ID格式相似但用途不同
    支持格式：
    - https://www.kuaishou.com/profile/creator_id
    - https://live.kuaishou.com/profile/creator_id
    - https://www.kuaishou.com/u/creator_id
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /profile/creator_id 格式（支持www和live子域名）
    creator_pattern = r'/profile/([a-zA-Z0-9_-]+)'
    match = re.search(creator_pattern, url)
    if match:
        creator_id = match.group(1)
        if validate_kuaishou_id(creator_id, "user"):
            return creator_id
    
    # 方式2: 从完整URL中提取 /u/creator_id 格式（另一种可能的格式）
    user_pattern = r'/u/([a-zA-Z0-9_-]+)'
    match = re.search(user_pattern, url)
    if match:
        creator_id = match.group(1)
        if validate_kuaishou_id(creator_id, "user"):
            return creator_id
    
    # 方式3: 从URL参数中提取 user_id
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'user_id' in params:
        user_id = params['user_id'][0]
        if validate_kuaishou_id(user_id, "user"):
            return user_id
    
    # 方式4: 直接作为creator_id处理（如果输入的就是纯ID）
    if validate_kuaishou_id(url, "user"):
        return url
    
    return ""


async def resolve_short_url(url: str, page: Page) -> str:
    """
    解析快手短链接，获取重定向后的长链接
    快手的短链接可能会有多次重定向，需要特殊处理
    """
    if not url or not url.startswith("http"):
        return url
    
    try:
        import random
        import asyncio
        
        # 减少等待时间，避免触发检测
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # 收集所有重定向URL
        redirect_urls = []
        final_url = None
        profile_url = None  # 专门保存用户主页URL
        
        def handle_response(response):
            nonlocal final_url, profile_url
            current_url = response.url
            redirect_urls.append(current_url)
            
            # 检查是否是我们需要的视频页面
            if 'kuaishou.com' in current_url and '/short-video/' in current_url:
                final_url = current_url
                print(f"[resolve_short_url] 找到视频页面: {current_url}")
            elif 'kuaishou.com' in current_url and 'photoId=' in current_url:
                final_url = current_url
                print(f"[resolve_short_url] 找到带photoId的页面: {current_url}")
            elif 'kuaishou.com' in current_url and '/profile/' in current_url:
                if '/live_api/' not in current_url:
                    # 这是用户主页URL，优先保存
                    profile_url = current_url
                    final_url = current_url
                    print(f"[resolve_short_url] 找到创作者主页: {current_url}")
                else:
                    # 这是API URL，只有在没有主页URL时才使用
                    if not profile_url:
                        print(f"[resolve_short_url] 找到API接口: {current_url}")
        
        def handle_request(request):
            # 监听请求，可能能捕获到重定向信息
            nonlocal final_url, profile_url
            if 'kuaishou.com' in request.url and '/short-video/' in request.url:
                if not final_url:
                    final_url = request.url
                    print(f"[resolve_short_url] 从请求中找到视频页面: {request.url}")
            elif 'kuaishou.com' in request.url and '/profile/' in request.url:
                if '/live_api/' not in request.url:
                    # 优先选择用户主页URL，排除API接口URL
                    if not profile_url:
                        profile_url = request.url
                        final_url = request.url
                        print(f"[resolve_short_url] 从请求中找到创作者主页: {request.url}")
        
        page.on('response', handle_response)
        page.on('request', handle_request)
        
        # 设置更真实的用户代理
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 访问短链接，使用更保守的设置
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=10000)
        except Exception as e:
            print(f"[resolve_short_url] 页面访问超时: {e}")
            return url
        
        # 短暂等待重定向完成
        await asyncio.sleep(random.uniform(1, 2))
        
        # 移除监听器
        page.remove_listener('response', handle_response)
        page.remove_listener('request', handle_request)
        
        # 如果找到了页面URL，优先返回用户主页URL
        if profile_url:
            print(f"[resolve_short_url] 快手短链接解析成功（用户主页）: {url} -> {profile_url}")
            return profile_url
        elif final_url:
            print(f"[resolve_short_url] 快手短链接解析成功: {url} -> {final_url}")
            return final_url
        
        # 如果没有找到，检查当前页面URL
        current_url = page.url
        print(f"[resolve_short_url] 当前页面URL: {current_url}")
        
        if '/short-video/' in current_url:
            print(f"[resolve_short_url] 从当前页面URL获取视频链接: {current_url}")
            return current_url
        elif 'photoId=' in current_url:
            print(f"[resolve_short_url] 从当前页面URL获取带photoId的链接: {current_url}")
            return current_url
        elif '/profile/' in current_url and '/live_api/' not in current_url:
            print(f"[resolve_short_url] 从当前页面URL获取创作者主页链接: {current_url}")
            return current_url
        
        # 尝试从页面内容中提取
        try:
            # 检查页面是否包含视频信息或创作者信息
            content = await page.content()
            if 'photoId' in content or 'short-video' in content:
                # 尝试从页面内容中提取photoId
                import re
                photo_id_match = re.search(r'photoId["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)', content)
                if photo_id_match:
                    photo_id = photo_id_match.group(1)
                    if validate_kuaishou_id(photo_id, "video"):
                        constructed_url = f"https://www.kuaishou.com/short-video/{photo_id}"
                        print(f"[resolve_short_url] 从页面内容提取photoId构造URL: {constructed_url}")
                        return constructed_url
            elif 'profile' in content or 'userId' in content:
                # 尝试从页面内容中提取userId
                import re
                user_id_match = re.search(r'userId["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)', content)
                if user_id_match:
                    user_id = user_id_match.group(1)
                    if validate_kuaishou_id(user_id, "user"):
                        constructed_url = f"https://www.kuaishou.com/profile/{user_id}"
                        print(f"[resolve_short_url] 从页面内容提取userId构造URL: {constructed_url}")
                        return constructed_url
        except Exception as e:
            print(f"[resolve_short_url] 页面内容解析失败: {e}")
        
        # 最后尝试：从所有重定向URL中寻找合适的用户主页URL
        for redirect_url in redirect_urls:
            if '/profile/' in redirect_url and '/live_api/' not in redirect_url and 'kuaishou.com' in redirect_url:
                print(f"[resolve_short_url] 从重定向历史中找到用户主页: {redirect_url}")
                return redirect_url
        
        # 打印调试信息
        print(f"[resolve_short_url] 重定向路径: {' -> '.join(redirect_urls)}")
        print(f"[resolve_short_url] 最终页面: {current_url}")
            
    except Exception as e:
        print(f"[resolve_short_url] 解析快手短链接失败: {e}")
        print(f"[resolve_short_url] 建议使用完整URL或直接video_id避免此问题")
    
    return url


async def resolve_any_video_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析快手视频输入，支持多种格式
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接是video_id
    video_id = extract_video_id_from_url(input_str)
    if video_id:
        print(f"[resolve_any_video_url_to_id] 直接提取到video_id: {video_id}")
        return video_id
    
    # 情况2: 短链接 - 需要先重定向解析
    if 'v.kuaishou.com' in input_str or 'chenzhongtech.com' in input_str:
        print(f"[resolve_any_video_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_video_url_to_id] 短链接解析结果: {resolved_url}")
            # 尝试从解析后的URL提取video_id
            video_id = extract_video_id_from_url(resolved_url)
            if video_id:
                print(f"[resolve_any_video_url_to_id] 从解析后的URL提取到video_id: {video_id}")
                return video_id
            
            # 如果标准提取失败，尝试从URL参数中提取photoId
            import urllib.parse
            parsed = urllib.parse.urlparse(resolved_url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'photoId' in params:
                photo_id = params['photoId'][0]
                if validate_kuaishou_id(photo_id, "video"):
                    print(f"[resolve_any_video_url_to_id] 从URL参数提取到photoId: {photo_id}")
                    return photo_id
    
    # 情况3: 完整URL - 提取video_id
    if 'kuaishou.com' in input_str:
        video_id = extract_video_id_from_url(input_str)
        if video_id:
            print(f"[resolve_any_video_url_to_id] 从完整URL提取到video_id: {video_id}")
            return video_id
    
    print(f"[resolve_any_video_url_to_id] 无法从输入中提取video_id: {input_str}")
    return ""


async def resolve_any_creator_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析快手创作者输入，支持多种格式
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接是creator_id
    creator_id = extract_creator_id_from_url(input_str)
    if creator_id:
        print(f"[resolve_any_creator_url_to_id] 直接提取到creator_id: {creator_id}")
        return creator_id
    
    # 情况2: 短链接 - 需要先重定向解析
    if 'v.kuaishou.com' in input_str or 'chenzhongtech.com' in input_str:
        print(f"[resolve_any_creator_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_creator_url_to_id] 短链接解析结果: {resolved_url}")
            creator_id = extract_creator_id_from_url(resolved_url)
            if creator_id:
                print(f"[resolve_any_creator_url_to_id] 从解析后的URL提取到creator_id: {creator_id}")
                return creator_id
    
    # 情况3: 完整URL - 提取creator_id
    if 'kuaishou.com' in input_str:
        creator_id = extract_creator_id_from_url(input_str)
        if creator_id:
            print(f"[resolve_any_creator_url_to_id] 从完整URL提取到creator_id: {creator_id}")
            return creator_id
    
    print(f"[resolve_any_creator_url_to_id] 无法从输入中提取creator_id: {input_str}")
    return ""