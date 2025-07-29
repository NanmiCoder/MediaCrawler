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
from typing import Optional, List

from pydantic import BaseModel, Field


class JuejinArticle(BaseModel):
    """
    掘金文章
    """
    article_id: str = Field(default="", description="文章ID")
    article_url: str = Field(default="", description="文章链接")
    title: str = Field(default="", description="文章标题")
    brief_content: str = Field(default="", description="文章摘要")
    content: str = Field(default="", description="文章内容")
    cover_image: str = Field(default="", description="封面图片")
    category_name: str = Field(default="", description="分类名称")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    view_count: int = Field(default=0, description="阅读数")
    digg_count: int = Field(default=0, description="点赞数")
    comment_count: int = Field(default=0, description="评论数")
    collect_count: int = Field(default=0, description="收藏数")
    created_time: int = Field(default=0, description="创建时间戳")
    updated_time: int = Field(default=0, description="更新时间戳")
    source_keyword: str = Field(default="", description="来源关键词")
    
    # 作者信息
    author_id: str = Field(default="", description="作者ID")
    author_name: str = Field(default="", description="作者昵称")
    author_avatar: str = Field(default="", description="作者头像")
    author_description: str = Field(default="", description="作者简介")
    author_level: int = Field(default=0, description="作者等级")
    author_job_title: str = Field(default="", description="作者职位")
    author_company: str = Field(default="", description="作者公司")


class JuejinComment(BaseModel):
    """
    掘金评论
    """
    comment_id: str = Field(default="", description="评论ID")
    parent_comment_id: str = Field(default="", description="父评论ID，为空表示一级评论")
    article_id: str = Field(default="", description="所属文章ID")
    content: str = Field(default="", description="评论内容")
    digg_count: int = Field(default=0, description="点赞数")
    reply_count: int = Field(default=0, description="回复数")
    created_time: int = Field(default=0, description="创建时间戳")
    ip_location: Optional[str] = Field(default="", description="IP地理位置")
    
    # 评论者信息
    user_id: str = Field(default="", description="评论者ID")
    user_name: str = Field(default="", description="评论者昵称")
    user_avatar: str = Field(default="", description="评论者头像")
    user_level: int = Field(default=0, description="评论者等级")
    user_job_title: str = Field(default="", description="评论者职位")


class JuejinCreator(BaseModel):
    """
    掘金创作者/用户
    """
    user_id: str = Field(default="", description="用户ID")
    user_name: str = Field(default="", description="用户昵称")
    user_avatar: str = Field(default="", description="用户头像")
    user_description: str = Field(default="", description="用户简介")
    user_level: int = Field(default=0, description="用户等级")
    job_title: str = Field(default="", description="职位")
    company: str = Field(default="", description="公司")
    homepage: str = Field(default="", description="个人主页")
    github_url: str = Field(default="", description="GitHub链接")
    
    # 统计信息
    followers_count: int = Field(default=0, description="关注者数量")
    following_count: int = Field(default=0, description="关注数量")
    post_article_count: int = Field(default=0, description="发布文章数")
    digg_article_count: int = Field(default=0, description="点赞文章数")
    got_digg_count: int = Field(default=0, description="获得点赞数")
    got_view_count: int = Field(default=0, description="获得阅读数")
    
    # 时间信息
    created_time: int = Field(default=0, description="注册时间戳")
    last_active_time: int = Field(default=0, description="最后活跃时间戳")


class JuejinTag(BaseModel):
    """
    掘金标签
    """
    tag_id: str = Field(default="", description="标签ID")
    tag_name: str = Field(default="", description="标签名称")
    color: str = Field(default="", description="标签颜色")
    icon: str = Field(default="", description="标签图标")
    concern_user_count: int = Field(default=0, description="关注用户数")
    post_article_count: int = Field(default=0, description="文章数量")


class JuejinSearchResult(BaseModel):
    """
    掘金搜索结果
    """
    keyword: str = Field(default="", description="搜索关键词")
    total_count: int = Field(default=0, description="总结果数")
    articles: List[JuejinArticle] = Field(default_factory=list, description="文章列表")
    users: List[JuejinCreator] = Field(default_factory=list, description="用户列表")
    tags: List[JuejinTag] = Field(default_factory=list, description="标签列表") 