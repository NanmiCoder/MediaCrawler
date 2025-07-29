# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

from typing import Dict

from .juejin_store_impl import JuejinStoreFactory

# 创建存储实例
juejin_store_instance = JuejinStoreFactory.create_store()


async def update_juejin_article(article_item: Dict):
    """
    更新掘金文章信息
    Args:
        article_item: 文章信息字典
    """
    await juejin_store_instance.store_content(article_item)


async def update_juejin_comment(comment_item: Dict):
    """
    更新掘金评论信息
    Args:
        comment_item: 评论信息字典
    """
    await juejin_store_instance.store_comment(comment_item)


async def save_creator(user_id: str, creator: Dict):
    """
    保存掘金创作者信息
    Args:
        user_id: 用户ID
        creator: 创作者信息字典
    """
    await juejin_store_instance.store_creator(creator)


__all__ = ["update_juejin_article", "update_juejin_comment", "save_creator"] 