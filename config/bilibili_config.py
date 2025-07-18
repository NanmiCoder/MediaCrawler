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
# bilili 平台配置

# 每天爬取视频/帖子的数量控制
MAX_NOTES_PER_DAY = 1

# 指定B站视频ID列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定B站用户ID列表
BILI_CREATOR_ID_LIST = [
    "20813884",
    # ........................
]

# 指定时间范围
START_DAY = "2024-01-01"
END_DAY = "2024-01-01"

# 搜索模式
BILI_SEARCH_MODE = "normal"

# 是否爬取用户信息
CREATOR_MODE = True

# 开始爬取用户信息页码
START_CONTACTS_PAGE = 1

# 单个视频/帖子最大爬取评论数
CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100

# 单个视频/帖子最大爬取动态数
CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50
