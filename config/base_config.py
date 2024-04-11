# 基础配置
PLATFORM = "xhs"
KEYWORDS = "杭州春花、杭州春天、杭州樱花、杭州油菜花、杭州桃花、杭州杜鹃花、太子湾郁金香、杭州玉兰花、杭州揪树《东岳庙古揪树)、西溪花朝节"
# LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
LOGIN_TYPE = "cookie"
COOKIES = "yYdJq8SK8ixjyYdJq8S2Yi4d4jVEWWyKyv2kyl9iET87JSq8ITv92h888yyq4qq8qy24f0KY"
SORT_TYPE = "time_descending"  # 具体值参见media_platform.xxx.field下的枚举值，展示只支持小红书
CRAWLER_TYPE = "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "jishuhttp"

# 设置为True不会打开浏览器（无头浏览器），设置False会打开一个浏览器（小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码）
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "json"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 200

# 爬取开始页数
START_PAGE = 10

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 4

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = True

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
