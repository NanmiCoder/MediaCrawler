# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# 基础配置
PLATFORM = "dy"  # 平台，xhs | dy | ks | bili | wb | tieba | zhihu
KEYWORDS = "美食教程"  # 关键词搜索配置，以英文逗号分隔
LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
COOKIES = "__ac_referer=__ac_blank; douyin.com; enter_pc_once=1; UIFID_TEMP=94323c0887b37f94f50ac5417d2d415b74fcf5f1106c230e40c326c63b00b663e9e901823a551a186d7da837c76dbda0e5c00b5d2633877ad93b56936ee58155c212656496de46acab0318447dfe426e; hevc_supported=true; fpk1=U2FsdGVkX19w755WxCaD06GWNseRFz3a2jrh+5clj8HftXuOwXR6+RdD+lTArd0XfFm2ckcwC/pJ1ogrvdEarw==; fpk2=3ade46e10ab46df1d7d395ddaa715a24; UIFID=94323c0887b37f94f50ac5417d2d415b74fcf5f1106c230e40c326c63b00b663d4c6caa9093ddf5f8b6d2315052e13e2a4c86819d4e3dfb88282e07cf7adce93f1a37f4b1554bba2610ed971a654f7f97783feaf6806469853a1b59fc71d8c888ddcd1e54aa8717f6e572852326b4d801c99fab0f69e4d0238bb9ea0b6ed1785c76573753182fb9bb4670badc3b5e87528bc21f1ab894dd46f24be6db2756caf; bd_ticket_guard_client_web_domain=2; SEARCH_RESULT_LIST_TYPE=%22single%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; s_v_web_id=verify_miv73gwe_BFqiNTTI_Xctr_4S1t_BZHV_MQYd0RFsEwrB; passport_csrf_token=7e6122192f46f4176eecefa8b346971d; passport_csrf_token_default=7e6122192f46f4176eecefa8b346971d; _bd_ticket_crypt_doamin=2; __security_mc_1_s_sdk_cert_key=758a30bc-410a-9e5e; __security_mc_1_s_sdk_crypt_sdk=ad1be521-4d44-ae84; __security_server_data_status=1; my_rd=2; passport_assist_user=CjyB432I7DLBEcUC9OfGbzLN2n4kJYDPGyLJv9KbCEk4XoJx487mDFQZp3jeyUD6FeBkcyNe2C7tw9V4TDMaSgo8AAAAAAAAAAAAAE_vUnW1o0XTqY_EELNDnonjOiidHh6CzZhUYrYkZ0e_Mqxmons88NDSwNMrVD77iB-sEObAhg4Yia_WVCABIgEDaEHixw%3D%3D; __security_mc_1_s_sdk_sign_data_key_web_protect=f0ab27e5-4b3b-bae7; login_time=1768021174392; _bd_ticket_crypt_cookie=66a1238a1c381fcae080fb73c7e6956c; __ac_nonce=0696c4e6400d77678ff98; __ac_signature=_02B4Z6wo00f01WiiwrAAAIDDWzc08pS00GVogsYAADNIc1; douyin.com; device_web_cpu_core=10; device_web_memory_size=8; dy_swidth=1920; dy_sheight=1080; strategyABtestKey=%221768705642.498%22; SelfTabRedDotControl=%5B%7B%22id%22%3A%227271839510319597568%22%2C%22u%22%3A113%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227561856871770884130%22%2C%22u%22%3A54%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227519200230189828123%22%2C%22u%22%3A16%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227567363688647100425%22%2C%22u%22%3A5%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227492764736136677415%22%2C%22u%22%3A19%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227205972227387295804%22%2C%22u%22%3A47%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227297403611225524234%22%2C%22u%22%3A17%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227297403842897905714%22%2C%22u%22%3A11%2C%22c%22%3A0%7D%5D; publish_badge_show_info=%220%2C0%2C0%2C1768705643965%22; is_dash_user=1; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A10%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A200%7D%22; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTVZLbHJFSE9hRzBOYjZsNklHbzA5QUVxRzFuRnozR0NWS013dEZDMjJnaEV1cXVzNXRQSFMzZDhrMEZsMXZyaEJjQ3JuMEpjMlpQbmhtT1BGVUdlUlk9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAADnGHyHYRLHvqVVPUOMwEzzspbYrxXWuTAXLi8g9GAqo%2F1768752000000%2F0%2F0%2F1768707136611%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAADnGHyHYRLHvqVVPUOMwEzzspbYrxXWuTAXLi8g9GAqo%2F1768752000000%2F0%2F1768706536611%2F0%22; biz_trace_id=a9bb5ea9; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f27353d343031303335323d333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=-iX5aknpnwPftr4p2YayjHew1aVm9qL2_IGqcsJ5ex524mgbIb409PyuU24d9oRc4mU3QzKG_oVs92g249xQ3FoOVLkrg4wZNWJWQsDGkwbWhFxxhGU_ps2zfRK0ebYNIdouSgakPTdIljbrZHRjBYv33RbH8YJiuNGp8cv_of1gnvvsDG5jUy1rhx0LLZzZcGdhRBguYp_FqWKeHPjf1CvcBZiS4X2iKVjPnNStSEYSH4WAr3NBeGkb8wE5DP5Tx4PeWGEbeNdh8qW6eAZYwtDSSgMbyVM4mzF8ntYOk9caeE--ufs5FUPlrf0ugux8FtT6rpjteUsqz0KfBYjCnrW5D7Rv00oN2c_13oLg_r1KKNvvdNLIrqK29kYgsLQlFaKpPPabov8ajW6DPBloy_r39d-7uvM-EAty3nJD0edokubQU2yoxcYCvgg-LqjUHQsBR1LpPiXIpjTqVW_4-e_cheBjnuPLwZtj0v5jx_QKwuKrIE_fvykSp3Ff7-XUPoPbyCEynI7JL9fDC3PAiHWdiYdVC5amVwSW_NJN590%3D; gulu_source_res=eyJwX2luIjoiNGQyZWY5YTQ5ZWRjMWRkODFjNjhhNDYzMTkwZDk5YzJlMTJhY2U4OTdjODg1Yzc5M2YzYTE0ODE0ZDQ1NGJkNSJ9; passport_auth_mix_state=l99zpsucoof39bwf4kj4308ongi27pnl; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJNVktsckVIT2FHME5iNmw2SUdvMDlBRXFHMW5GejNHQ1ZLTXd0RkMyMmdoRXVxdXM1dFBIUzNkOGswRmwxdnJoQmNDcm4wSmMyWlBuaG1PUEZVR2VSWT0iLCJ0c19zaWduIjoidHMuMi45OTQ4OTc2OTBhOTMyYzMzYjZmNmJlNzY2ZjgwMzUwYzg4YTZmYjk3OWU5MjEzYTBhOGU0MmFhZWJkOWE4YzNiYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiI1MHhvMFpEa3RXdW83S24yK0NPb3Z1aFFXZURQam8wNEhYem5IclRhUExRPSIsInNlY190cyI6IiNSQVppcko0WHN6RHIzN1c2U2E4LzlBT3VrVG5FaDNhcTBQMTdmeFFhQUFITWhFN1JGOGJ3eTh4SldSSU4ifQ%3D%3D; download_guide=%222%2F20260118%2F0%22; IsDouyinActive=true"
CRAWLER_TYPE = (
    "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)
)
# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # kuaidaili | wandouhttp

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
# 抖音如果一直提示失败，打开浏览器看下是否扫码登录之后出现了手机号验证，如果出现了手动过一下再试。
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用CDP模式 - 使用用户现有的Chrome/Edge浏览器进行爬取，提供更好的反检测能力
# 启用后将自动检测并启动用户的Chrome/Edge浏览器，通过CDP协议进行控制
# 这种方式使用真实的浏览器环境，包括用户的扩展、Cookie和设置，大大降低被检测的风险
ENABLE_CDP_MODE = True

# CDP调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测Chrome/Edge的安装路径
# Windows示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# CDP模式下是否启用无头模式
# 注意：即使设置为True，某些反检测功能在无头模式下可能效果不佳
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 120

# 是否在程序结束时自动关闭浏览器
# 设置为False可以保持浏览器运行，便于调试
AUTO_CLOSE_BROWSER = False

# 数据保存类型选项配置,支持六种类型：csv、db、json、sqlite、excel、postgres, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "json"  # csv or db or json or sqlite or excel or postgres

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 3

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬媒体模式（包含图片或视频资源），默认不开启爬媒体
ENABLE_GET_MEIDAS = True

# 是否开启爬评论模式, 默认开启爬评论
ENABLE_GET_COMMENTS = True

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 是否开启爬二级评论模式, 默认不开启爬二级评论
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = False

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将“零几”识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取间隔时间
CRAWLER_MAX_SLEEP_SEC = 2

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
