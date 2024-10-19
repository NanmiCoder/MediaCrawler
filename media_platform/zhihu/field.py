# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


from enum import Enum
from typing import NamedTuple

from constant import zhihu as zhihu_constant


class SearchTime(Enum):
    """
    搜索时间范围
    """
    DEFAULT = ""  # 不限时间
    ONE_DAY = "a_day"  # 一天内
    ONE_WEEK = "a_week"  # 一周内
    ONE_MONTH = "a_month"  # 一个月内
    THREE_MONTH = "three_months"  # 三个月内
    HALF_YEAR = "half_a_year"  # 半年内
    ONE_YEAR = "a_year"  # 一年内


class SearchType(Enum):
    """
    搜索结果类型
    """
    DEFAULT = ""  # 不限类型
    ANSWER = zhihu_constant.ANSWER_NAME  # 只看回答
    ARTICLE = zhihu_constant.ARTICLE_NAME  # 只看文章
    VIDEO = zhihu_constant.VIDEO_NAME  # 只看视频


class SearchSort(Enum):
    """
    搜索结果排序
    """
    DEFAULT = ""  # 综合排序
    UPVOTED_COUNT = "upvoted_count"  # 最多赞同
    CREATE_TIME = "created_time"  # 最新发布
