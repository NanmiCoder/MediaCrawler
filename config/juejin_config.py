# -*- coding: utf-8 -*-
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# 掘金平台配置

# 掘金主域名
JUEJIN_DOMAIN = "https://juejin.cn"

# 掘金搜索页面URL
JUEJIN_SEARCH_URL = "https://juejin.cn/search"

# 掘金API基础URL
JUEJIN_API_BASE_URL = "https://api.juejin.cn"

# 搜索API端点
JUEJIN_SEARCH_API = "/search_api/v1/search"

# 文章详情API端点
JUEJIN_ARTICLE_DETAIL_API = "/content_api/v1/article/detail"

# 用户信息API端点
JUEJIN_USER_INFO_API = "/user_api/v1/user/get"

# 评论列表API端点
JUEJIN_COMMENTS_API = "/interact_api/v1/comment/list"

# 登录页面URL
JUEJIN_LOGIN_URL = "https://juejin.cn/login"

# 排序方式
# comprehensive: 综合排序
# newest: 最新
# hottest: 最热
SORT_TYPE = "comprehensive"

# 搜索类型
# all: 全部
# article: 文章
# tag: 标签
# user: 用户
SEARCH_TYPE = "article"

# 指定文章URL列表
JUEJIN_SPECIFIED_ARTICLE_URL_LIST = [
    # "https://juejin.cn/post/7123456789012345678",
    # ........................
]

# 指定用户ID列表
JUEJIN_CREATOR_ID_LIST = [
    # "1234567890123456789",
    # ........................
]

# 请求头配置
JUEJIN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://juejin.cn/",
    "Origin": "https://juejin.cn",
}

# 分类映射
CATEGORY_MAPPING = {
    "frontend": "前端",
    "backend": "后端", 
    "android": "Android",
    "ios": "iOS",
    "ai": "人工智能",
    "freebie": "开发工具",
    "career": "代码人生",
    "article": "阅读"
} 