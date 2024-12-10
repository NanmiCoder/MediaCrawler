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

