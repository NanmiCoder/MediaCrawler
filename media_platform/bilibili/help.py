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
from hashlib import md5
from typing import Dict
from playwright.async_api import Page

from tools import utils


class BilibiliSign:
    def __init__(self, img_key: str, sub_key: str):
        self.img_key = img_key
        self.sub_key = sub_key
        self.map_table = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
            33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
            61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
            36, 20, 34, 44, 52
        ]

    def get_salt(self) -> str:
        """
        获取加盐的 key
        :return:
        """
        salt = ""
        mixin_key = self.img_key + self.sub_key
        for mt in self.map_table:
            salt += mixin_key[mt]
        return salt[:32]

    def sign(self, req_data: Dict) -> Dict:
        """
        请求参数中加上当前时间戳对请求参数中的key进行字典序排序
        再将请求参数进行 url 编码集合 salt 进行 md5 就可以生成w_rid参数了
        :param req_data:
        :return:
        """
        current_ts = utils.get_unix_timestamp()
        req_data.update({"wts": current_ts})
        req_data = dict(sorted(req_data.items()))
        req_data = {
            # 过滤 value 中的 "!'()*" 字符
            k: ''.join(filter(lambda ch: ch not in "!'()*", str(v)))
            for k, v
            in req_data.items()
        }
        query = urllib.parse.urlencode(req_data)
        salt = self.get_salt()
        wbi_sign = md5((query + salt).encode()).hexdigest()  # 计算 w_rid
        req_data['w_rid'] = wbi_sign
        return req_data


def validate_bilibili_id(id_str: str, id_type: str = "auto") -> bool:
    """
    验证B站ID的有效性
    Args:
        id_str: 要验证的ID字符串
        id_type: ID类型 ("bvid", "aid", "uid", "auto")
    Returns:
        bool: ID是否有效
    """
    if not id_str or not isinstance(id_str, str):
        return False
    
    id_str = id_str.strip()
    
    if id_type == "bvid":
        # BVID格式验证：BV + 10位字母数字组合
        return bool(re.match(r'^BV[a-zA-Z0-9]{10}$', id_str))
    elif id_type == "aid":
        # AID格式验证：纯数字，通常6-11位
        return bool(re.match(r'^\d{6,11}$', id_str))
    elif id_type == "uid":
        # 用户ID格式验证：纯数字，通常6-15位
        return bool(re.match(r'^\d{6,15}$', id_str))
    else:
        # 自动判断
        if re.match(r'^BV[a-zA-Z0-9]{10}$', id_str):
            return True
        elif re.match(r'^\d{6,15}$', id_str):
            return True
        return False


def distinguish_id_type(id_str: str, url_context: str = "") -> str:
    """
    根据上下文区分ID类型
    Args:
        id_str: ID字符串
        url_context: URL上下文
    Returns:
        str: "bvid", "aid", "uid" 或 "unknown"
    """
    if not id_str:
        return "unknown"
    
    # 根据格式判断
    if re.match(r'^BV[a-zA-Z0-9]{10}$', id_str):
        return "bvid"
    elif re.match(r'^\d+$', id_str):
        # 根据URL路径判断
        if "/video/" in url_context:
            return "aid"
        elif "/space/" in url_context or "/u/" in url_context:
            return "uid"
        else:
            # 根据长度推测
            if len(id_str) >= 8:
                return "aid"  # 视频ID通常较长
            else:
                return "uid"  # 用户ID通常较短
    
    return "unknown"


def extract_bvid_from_url(url: str) -> str:
    """
    从B站视频URL中提取BVID
    支持格式：
    - https://www.bilibili.com/video/BV1Q2MXzgEgW
    - https://m.bilibili.com/video/BV1Q2MXzgEgW
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /video/BVXXXXXXXX 格式
    bvid_pattern = r'/video/(BV[a-zA-Z0-9]{10})'
    match = re.search(bvid_pattern, url)
    if match:
        bvid = match.group(1)
        if validate_bilibili_id(bvid, "bvid"):
            return bvid
    
    # 方式2: 从URL参数中提取 bvid
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'bvid' in params:
        bvid = params['bvid'][0]
        if validate_bilibili_id(bvid, "bvid"):
            return bvid
    
    # 方式3: 直接作为BVID处理（如果输入的就是纯BVID）
    if validate_bilibili_id(url, "bvid"):
        return url
    
    return ""


def extract_aid_from_url(url: str) -> str:
    """
    从B站视频URL中提取AID
    支持格式：
    - https://www.bilibili.com/video/av12345678
    - URL参数中的aid
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从完整URL中提取 /video/av数字 格式
    aid_pattern = r'/video/av(\d+)'
    match = re.search(aid_pattern, url)
    if match:
        aid = match.group(1)
        if validate_bilibili_id(aid, "aid"):
            return aid
    
    # 方式2: 从URL参数中提取 aid
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    if 'aid' in params:
        aid = params['aid'][0]
        if validate_bilibili_id(aid, "aid"):
            return aid
    
    # 方式3: 直接作为AID处理（如果输入的就是纯数字）
    if validate_bilibili_id(url, "aid"):
        return url
    
    return ""


def extract_uid_from_url(url: str) -> str:
    """
    从B站用户空间URL中提取UID
    支持格式：
    - https://space.bilibili.com/449342345
    - https://m.bilibili.com/space/449342345
    """
    if not url or not isinstance(url, str):
        return ""
    
    url = url.strip()
    
    # 方式1: 从完整URL中提取 space.bilibili.com/数字 或 /space/数字 格式
    uid_patterns = [
        r'space\.bilibili\.com/(\d+)',  # https://space.bilibili.com/449342345
        r'/space/(\d+)'                 # https://m.bilibili.com/space/449342345
    ]
    
    for uid_pattern in uid_patterns:
        match = re.search(uid_pattern, url)
        if match:
            uid = match.group(1)
            if validate_bilibili_id(uid, "uid"):
                return uid
    
    # 方式2: 从URL参数中提取 mid 或 uid
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    for param_name in ['mid', 'uid', 'up_id']:
        if param_name in params:
            uid = params[param_name][0]
            if validate_bilibili_id(uid, "uid"):
                return uid
    
    # 方式3: 直接作为UID处理（如果输入的就是纯数字）
    if validate_bilibili_id(url, "uid"):
        return url
    
    return ""


async def resolve_short_url(url: str, page: Page) -> str:
    """
    解析B站短链接，获取重定向后的长链接
    B站的短链接格式：https://b23.tv/XXXXXXX
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
        
        def handle_response(response):
            nonlocal final_url
            current_url = response.url
            redirect_urls.append(current_url)
            
            # 检查是否是我们需要的B站页面
            if 'bilibili.com' in current_url and '/video/' in current_url:
                # 验证URL中是否包含有效的BVID或AID
                bvid_from_url = extract_bvid_from_url(current_url)
                aid_from_url = extract_aid_from_url(current_url)
                if bvid_from_url or aid_from_url:
                    final_url = current_url
                    video_id = bvid_from_url or aid_from_url
                    print(f"[resolve_short_url] 找到有效视频页面: {current_url} (video_id: {video_id})")
                else:
                    print(f"[resolve_short_url] 跳过无效视频页面: {current_url}")
            elif 'bilibili.com' in current_url and '/space/' in current_url:
                # 验证URL中是否包含有效的UID
                uid_from_url = extract_uid_from_url(current_url)
                if uid_from_url:
                    final_url = current_url
                    print(f"[resolve_short_url] 找到有效用户空间: {current_url} (uid: {uid_from_url})")
                else:
                    print(f"[resolve_short_url] 跳过无效用户空间: {current_url}")
        
        def handle_request(request):
            # 监听请求，可能能捕获到重定向信息
            nonlocal final_url
            if 'bilibili.com' in request.url and '/video/' in request.url:
                # 验证URL中是否包含有效的BVID或AID
                bvid_from_url = extract_bvid_from_url(request.url)
                aid_from_url = extract_aid_from_url(request.url)
                if (bvid_from_url or aid_from_url) and not final_url:
                    final_url = request.url
                    video_id = bvid_from_url or aid_from_url
                    print(f"[resolve_short_url] 从请求中找到有效视频页面: {request.url} (video_id: {video_id})")
                else:
                    print(f"[resolve_short_url] 从请求中跳过无效视频页面: {request.url}")
            elif 'bilibili.com' in request.url and '/space/' in request.url:
                # 验证URL中是否包含有效的UID
                uid_from_url = extract_uid_from_url(request.url)
                if uid_from_url and not final_url:
                    final_url = request.url
                    print(f"[resolve_short_url] 从请求中找到有效用户空间: {request.url} (uid: {uid_from_url})")
                else:
                    print(f"[resolve_short_url] 从请求中跳过无效用户空间: {request.url}")
        
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
        
        # 如果找到了页面URL，返回
        if final_url:
            print(f"[resolve_short_url] B站短链接解析成功: {url} -> {final_url}")
            return final_url
        
        # 如果没有找到，检查当前页面URL
        current_url = page.url
        print(f"[resolve_short_url] 当前页面URL: {current_url}")
        
        if '/video/' in current_url:
            # 验证当前页面URL中的video_id
            bvid_from_current = extract_bvid_from_url(current_url)
            aid_from_current = extract_aid_from_url(current_url)
            if bvid_from_current or aid_from_current:
                video_id = bvid_from_current or aid_from_current
                print(f"[resolve_short_url] 从当前页面URL获取有效视频链接: {current_url} (video_id: {video_id})")
                return current_url
            else:
                print(f"[resolve_short_url] 当前页面URL包含无效video_id，跳过: {current_url}")
        elif '/space/' in current_url:
            # 验证当前页面URL中的uid
            uid_from_current = extract_uid_from_url(current_url)
            if uid_from_current:
                print(f"[resolve_short_url] 从当前页面URL获取有效用户空间链接: {current_url} (uid: {uid_from_current})")
                return current_url
            else:
                print(f"[resolve_short_url] 当前页面URL包含无效uid，跳过: {current_url}")
        
        # 最后尝试：从所有重定向URL中寻找合适的URL
        for redirect_url in redirect_urls:
            if 'bilibili.com' in redirect_url:
                if '/video/' in redirect_url:
                    # 验证重定向URL中的video_id
                    bvid_from_redirect = extract_bvid_from_url(redirect_url)
                    aid_from_redirect = extract_aid_from_url(redirect_url)
                    if bvid_from_redirect or aid_from_redirect:
                        video_id = bvid_from_redirect or aid_from_redirect
                        print(f"[resolve_short_url] 从重定向历史中找到有效视频页面: {redirect_url} (video_id: {video_id})")
                        return redirect_url
                    else:
                        print(f"[resolve_short_url] 重定向历史中的视频URL无效，跳过: {redirect_url}")
                elif '/space/' in redirect_url:
                    # 验证重定向URL中的uid
                    uid_from_redirect = extract_uid_from_url(redirect_url)
                    if uid_from_redirect:
                        print(f"[resolve_short_url] 从重定向历史中找到有效用户空间: {redirect_url} (uid: {uid_from_redirect})")
                        return redirect_url
                    else:
                        print(f"[resolve_short_url] 重定向历史中的用户空间URL无效，跳过: {redirect_url}")
        
        # 打印调试信息
        print(f"[resolve_short_url] 重定向路径: {' -> '.join(redirect_urls)}")
        print(f"[resolve_short_url] 最终页面: {current_url}")
            
    except Exception as e:
        print(f"[resolve_short_url] 解析B站短链接失败: {e}")
        print(f"[resolve_short_url] 建议使用完整URL或直接BVID/AID避免此问题")
    
    return url


async def resolve_any_video_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析B站视频输入，支持多种格式
    返回BVID（优先）或AID
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接提取BVID或AID
    bvid = extract_bvid_from_url(input_str)
    if bvid:
        print(f"[resolve_any_video_url_to_id] 直接提取到BVID: {bvid}")
        return bvid
    
    aid = extract_aid_from_url(input_str)
    if aid:
        print(f"[resolve_any_video_url_to_id] 直接提取到AID: {aid}")
        return aid
    
    # 情况2: 短链接 - 需要先重定向解析
    if 'b23.tv' in input_str:
        print(f"[resolve_any_video_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_video_url_to_id] 短链接解析结果: {resolved_url}")
            # 尝试从解析后的URL提取video_id
            bvid_resolved = extract_bvid_from_url(resolved_url)
            if bvid_resolved:
                print(f"[resolve_any_video_url_to_id] 从解析后的URL提取到BVID: {bvid_resolved}")
                return bvid_resolved
            
            aid_resolved = extract_aid_from_url(resolved_url)
            if aid_resolved:
                print(f"[resolve_any_video_url_to_id] 从解析后的URL提取到AID: {aid_resolved}")
                return aid_resolved
    
    # 情况3: 完整URL - 提取video_id
    if 'bilibili.com' in input_str:
        bvid = extract_bvid_from_url(input_str)
        if bvid:
            print(f"[resolve_any_video_url_to_id] 从完整URL提取到BVID: {bvid}")
            return bvid
        
        aid = extract_aid_from_url(input_str)
        if aid:
            print(f"[resolve_any_video_url_to_id] 从完整URL提取到AID: {aid}")
            return aid
    
    print(f"[resolve_any_video_url_to_id] 无法从输入中提取video_id: {input_str}")
    return ""


async def resolve_any_user_url_to_id(input_str: str, page: Page) -> str:
    """
    智能解析B站用户输入，支持多种格式
    返回UID
    """
    if not input_str or not isinstance(input_str, str):
        return ""
    
    input_str = input_str.strip()
    
    # 情况1: 直接是UID
    uid = extract_uid_from_url(input_str)
    if uid:
        print(f"[resolve_any_user_url_to_id] 直接提取到UID: {uid}")
        return uid
    
    # 情况2: 短链接 - 需要先重定向解析
    if 'b23.tv' in input_str:
        print(f"[resolve_any_user_url_to_id] 检测到短链接，开始解析: {input_str}")
        resolved_url = await resolve_short_url(input_str, page)
        if resolved_url and resolved_url != input_str:
            print(f"[resolve_any_user_url_to_id] 短链接解析结果: {resolved_url}")
            uid = extract_uid_from_url(resolved_url)
            if uid:
                print(f"[resolve_any_user_url_to_id] 从解析后的URL提取到UID: {uid}")
                return uid
    
    # 情况3: 完整URL - 提取UID
    if 'bilibili.com' in input_str:
        uid = extract_uid_from_url(input_str)
        if uid:
            print(f"[resolve_any_user_url_to_id] 从完整URL提取到UID: {uid}")
            return uid
    
    print(f"[resolve_any_user_url_to_id] 无法从输入中提取UID: {input_str}")
    return ""


if __name__ == '__main__':
    _img_key = "7cd084941338484aae1ad9425b84077c"
    _sub_key = "4932caff0ff746eab6f01bf08b70ac45"
    _search_url = "__refresh__=true&_extra=&ad_resource=5654&category_id=&context=&dynamic_offset=0&from_source=&from_spmid=333.337&gaia_vtoken=&highlight=1&keyword=python&order=click&page=1&page_size=20&platform=pc&qv_id=OQ8f2qtgYdBV1UoEnqXUNUl8LEDAdzsD&search_type=video&single_column=0&source_tag=3&web_location=1430654"
    _req_data = dict()
    for params in _search_url.split("&"):
        kvalues = params.split("=")
        key = kvalues[0]
        value = kvalues[1]
        _req_data[key] = value
    print("pre req_data", _req_data)
    _req_data = BilibiliSign(img_key=_img_key, sub_key=_sub_key).sign(req_data={"aid":170001})
    print(_req_data)