import argparse

from tools.utils import str2bool

# 读取command arg
parser = argparse.ArgumentParser(description='Media crawler program.')
parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks | bili | wb)',
                    choices=["xhs", "dy", "ks", "bili", "wb"])
parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                    choices=["qrcode", "phone", "cookie"])
parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                    choices=["search", "detail", "creator"])
parser.add_argument('--start', type=int,
                    help='number of start page')
parser.add_argument('--keywords', type=str,
                    help='please input keywords')
parser.add_argument('--get_comment', type=str2bool,
                    help='whether to crawl level one comment')
parser.add_argument('--get_sub_comment', type=str2bool,
                    help='whether to crawl level two comment')


args = parser.parse_args()

# 基础配置
PLATFORM = args.platform if args.platform else "xhs"
KEYWORDS = args.keywords if args.keywords else "python,golang"
LOGIN_TYPE = args.lt if args.lt else "qrcode"  # qrcode or phone or cookie
COOKIES = ""
# 具体值参见media_platform.xxx.field下的枚举值，展示只支持小红书
SORT_TYPE = "popularity_descending"
# 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)
CRAWLER_TYPE = args.type if args.type else "search"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
# 抖音如果一直提示失败，打开浏览器看下是否扫码登录之后出现了手机号验证，如果出现了手动过一下再试。
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "json"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = args.start if args.start else 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 4

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = args.get_comment if args.get_comment else False

# 是否开启爬二级评论模式, 默认不开启爬二级评论, 目前仅支持 xhs
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = args.get_sub_comment if args.get_sub_comment else False

# 指定小红书需要爬虫的笔记ID列表
XHS_SPECIFIED_ID_LIST = [
    "6422c2750000000027000d88",
    "64ca1b73000000000b028dd2",
    "630d5b85000000001203ab41",
    # ........................
]

# 指定抖音需要爬取的ID列表
DY_SPECIFIED_ID_LIST = [
    "7280854932641664319",
    "7202432992642387233"
    # ........................
]

# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = [
    "3xf8enb8dbj6uig",
    "3x6zz972bchmvqe"
]

# 指定B站平台需要爬取的视频bvid列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定微博平台需要爬取的帖子列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# 指定小红书创作者ID列表
XHS_CREATOR_ID_LIST = [
    "63e36c9a000000002703502b",
    # ........................
]

# 指定Dy创作者ID列表(sec_id)
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    # ........................
]
