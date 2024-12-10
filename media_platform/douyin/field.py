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


class SearchChannelType(Enum):
    """search channel type"""
    GENERAL = "aweme_general"  # 综合
    VIDEO = "aweme_video_web"  # 视频
    USER = "aweme_user_web"  # 用户
    LIVE = "aweme_live"  # 直播


class SearchSortType(Enum):
    """search sort type"""
    GENERAL = 0  # 综合排序
    MOST_LIKE = 1  # 最多点赞
    LATEST = 2  # 最新发布

class PublishTimeType(Enum):
    """publish time type"""
    UNLIMITED = 0  # 不限
    ONE_DAY = 1  # 一天内
    ONE_WEEK = 7  # 一周内
    SIX_MONTH = 180  # 半年内
