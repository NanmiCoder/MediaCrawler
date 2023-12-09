# 基础配置
PLATFORM = "xhs"
KEYWORDS = "python,golang"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
CRAWLER_TYPE = "search"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 重试时间
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 10

# 抖音每个视频抓取评论最大条数 (为0则不限制)
DY_MAX_COMMENTS_PER_POST = 10

# 抖音评论关键词筛选(只会留下包含关键词的评论,为空不限制)
DY_COMMENT_KEYWORDS = [
    "我"
    # ........................
]

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
KS_SPECIFIED_ID_LIST = []

# 指定B站平台需要爬取的视频ID列表
BILI_SPECIFIED_ID_LIST = [
    "416252543",
    "976148468"
    # ........................
]
