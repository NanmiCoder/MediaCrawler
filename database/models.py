# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/models.py
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

from sqlalchemy import create_engine, Column, Integer, Text, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class BilibiliVideo(Base):
    __tablename__ = 'bilibili_video'
    id = Column(Integer, primary_key=True, comment='主键ID')
    video_id = Column(BigInteger, nullable=False, index=True, unique=True, comment='视频ID')
    video_url = Column(Text, nullable=False, comment='视频URL')
    user_id = Column(BigInteger, index=True, comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    liked_count = Column(Integer, comment='点赞数')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    video_type = Column(Text, comment='视频类型')
    title = Column(Text, comment='视频标题')
    desc = Column(Text, comment='视频描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    disliked_count = Column(Text, comment='点踩数')
    video_play_count = Column(Text, comment='播放数')
    video_favorite_count = Column(Text, comment='收藏数')
    video_share_count = Column(Text, comment='分享数')
    video_coin_count = Column(Text, comment='硬币数')
    video_danmaku = Column(Text, comment='弹幕数')
    video_comment = Column(Text, comment='评论数')
    video_cover_url = Column(Text, comment='视频封面URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class BilibiliVideoComment(Base):
    __tablename__ = 'bilibili_video_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    sex = Column(Text, comment='性别')
    sign = Column(Text, comment='签名')
    avatar = Column(Text, comment='头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(BigInteger, index=True, comment='评论ID')
    video_id = Column(BigInteger, index=True, comment='视频ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, default='0', comment='点赞数')

class BilibiliUpInfo(Base):
    __tablename__ = 'bilibili_up_info'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(BigInteger, index=True, comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    sex = Column(Text, comment='性别')
    sign = Column(Text, comment='签名')
    avatar = Column(Text, comment='头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    total_fans = Column(Integer, comment='总粉丝数')
    total_liked = Column(Integer, comment='总获赞数')
    user_rank = Column(Integer, comment='用户等级')
    is_official = Column(Integer, comment='是否官方认证')

class BilibiliContactInfo(Base):
    __tablename__ = 'bilibili_contact_info'
    id = Column(Integer, primary_key=True, comment='主键ID')
    up_id = Column(BigInteger, index=True, comment='UP主ID')
    fan_id = Column(BigInteger, index=True, comment='粉丝ID')
    up_name = Column(Text, comment='UP主名称')
    fan_name = Column(Text, comment='粉丝名称')
    up_sign = Column(Text, comment='UP主签名')
    fan_sign = Column(Text, comment='粉丝签名')
    up_avatar = Column(Text, comment='UP主头像')
    fan_avatar = Column(Text, comment='粉丝头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class BilibiliUpDynamic(Base):
    __tablename__ = 'bilibili_up_dynamic'
    id = Column(Integer, primary_key=True, comment='主键ID')
    dynamic_id = Column(BigInteger, index=True, comment='动态ID')
    user_id = Column(String(255), comment='用户ID')
    user_name = Column(Text, comment='用户名称')
    text = Column(Text, comment='动态内容')
    type = Column(Text, comment='动态类型')
    pub_ts = Column(BigInteger, comment='发布时间戳')
    total_comments = Column(Integer, comment='总评论数')
    total_forwards = Column(Integer, comment='总转发数')
    total_liked = Column(Integer, comment='总点赞数')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class DouyinAweme(Base):
    __tablename__ = 'douyin_aweme'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    sec_uid = Column(String(255), comment='安全用户ID')
    short_user_id = Column(String(255), comment='短用户ID')
    user_unique_id = Column(String(255), comment='用户唯一ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    user_signature = Column(Text, comment='用户签名')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    aweme_id = Column(BigInteger, index=True, comment='作品ID')
    aweme_type = Column(Text, comment='作品类型')
    title = Column(Text, comment='作品标题')
    desc = Column(Text, comment='作品描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    liked_count = Column(Text, comment='点赞数')
    comment_count = Column(Text, comment='评论数')
    share_count = Column(Text, comment='分享数')
    collected_count = Column(Text, comment='收藏数')
    aweme_url = Column(Text, comment='作品URL')
    cover_url = Column(Text, comment='封面URL')
    video_download_url = Column(Text, comment='视频下载URL')
    music_download_url = Column(Text, comment='音乐下载URL')
    note_download_url = Column(Text, comment='笔记下载URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class DouyinAwemeComment(Base):
    __tablename__ = 'douyin_aweme_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    sec_uid = Column(String(255), comment='安全用户ID')
    short_user_id = Column(String(255), comment='短用户ID')
    user_unique_id = Column(String(255), comment='用户唯一ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    user_signature = Column(Text, comment='用户签名')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(BigInteger, index=True, comment='评论ID')
    aweme_id = Column(BigInteger, index=True, comment='作品ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, default='0', comment='点赞数')
    pictures = Column(Text, default='', comment='图片')

class DyCreator(Base):
    __tablename__ = 'dy_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    desc = Column(Text, comment='描述')
    gender = Column(Text, comment='性别')
    follows = Column(Text, comment='关注数')
    fans = Column(Text, comment='粉丝数')
    interaction = Column(Text, comment='互动数')
    videos_count = Column(String(255), comment='视频数量')

class KuaishouVideo(Base):
    __tablename__ = 'kuaishou_video'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(64), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    video_id = Column(String(255), index=True, comment='视频ID')
    video_type = Column(Text, comment='视频类型')
    title = Column(Text, comment='视频标题')
    desc = Column(Text, comment='视频描述')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    liked_count = Column(Text, comment='点赞数')
    viewd_count = Column(Text, comment='观看数')
    video_url = Column(Text, comment='视频URL')
    video_cover_url = Column(Text, comment='视频封面URL')
    video_play_url = Column(Text, comment='视频播放URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class KuaishouVideoComment(Base):
    __tablename__ = 'kuaishou_video_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(Text, comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(BigInteger, index=True, comment='评论ID')
    video_id = Column(String(255), index=True, comment='视频ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    sub_comment_count = Column(Text, comment='子评论数')

class WeiboNote(Base):
    __tablename__ = 'weibo_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    gender = Column(Text, comment='性别')
    profile_url = Column(Text, comment='个人主页URL')
    ip_location = Column(Text, default='', comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    note_id = Column(BigInteger, index=True, comment='笔记ID')
    content = Column(Text, comment='笔记内容')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    create_date_time = Column(String(255), index=True, comment='创建日期时间')
    liked_count = Column(Text, comment='点赞数')
    comments_count = Column(Text, comment='评论数')
    shared_count = Column(Text, comment='分享数')
    note_url = Column(Text, comment='笔记URL')
    source_keyword = Column(Text, default='', comment='来源关键词')

class WeiboNoteComment(Base):
    __tablename__ = 'weibo_note_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    gender = Column(Text, comment='性别')
    profile_url = Column(Text, comment='个人主页URL')
    ip_location = Column(Text, default='', comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(BigInteger, index=True, comment='评论ID')
    note_id = Column(BigInteger, index=True, comment='笔记ID')
    content = Column(Text, comment='评论内容')
    create_time = Column(BigInteger, comment='创建时间戳')
    create_date_time = Column(String(255), index=True, comment='创建日期时间')
    comment_like_count = Column(Text, comment='评论点赞数')
    sub_comment_count = Column(Text, comment='子评论数')
    parent_comment_id = Column(String(255), comment='父评论ID')

class WeiboCreator(Base):
    __tablename__ = 'weibo_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    desc = Column(Text, comment='描述')
    gender = Column(Text, comment='性别')
    follows = Column(Text, comment='关注数')
    fans = Column(Text, comment='粉丝数')
    tag_list = Column(Text, comment='标签列表')

class XhsCreator(Base):
    __tablename__ = 'xhs_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    desc = Column(Text, comment='描述')
    gender = Column(Text, comment='性别')
    follows = Column(Text, comment='关注数')
    fans = Column(Text, comment='粉丝数')
    interaction = Column(Text, comment='互动数')
    tag_list = Column(Text, comment='标签列表')

class XhsNote(Base):
    __tablename__ = 'xhs_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    note_id = Column(String(255), index=True, comment='笔记ID')
    type = Column(Text, comment='笔记类型')
    title = Column(Text, comment='笔记标题')
    desc = Column(Text, comment='笔记描述')
    video_url = Column(Text, comment='视频URL')
    time = Column(BigInteger, index=True, comment='时间戳')
    last_update_time = Column(BigInteger, comment='最后更新时间戳')
    liked_count = Column(Text, comment='点赞数')
    collected_count = Column(Text, comment='收藏数')
    comment_count = Column(Text, comment='评论数')
    share_count = Column(Text, comment='分享数')
    image_list = Column(Text, comment='图片列表')
    tag_list = Column(Text, comment='标签列表')
    note_url = Column(Text, comment='笔记URL')
    source_keyword = Column(Text, default='', comment='来源关键词')
    xsec_token = Column(Text, comment='Xsec Token')

class XhsNoteComment(Base):
    __tablename__ = 'xhs_note_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(255), index=True, comment='评论ID')
    create_time = Column(BigInteger, index=True, comment='创建时间戳')
    note_id = Column(String(255), comment='笔记ID')
    content = Column(Text, comment='评论内容')
    sub_comment_count = Column(Integer, comment='子评论数')
    pictures = Column(Text, comment='图片')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, comment='点赞数')

class TiebaNote(Base):
    __tablename__ = 'tieba_note'
    id = Column(Integer, primary_key=True, comment='主键ID')
    note_id = Column(String(644), index=True, comment='笔记ID')
    title = Column(Text, comment='笔记标题')
    desc = Column(Text, comment='笔记描述')
    note_url = Column(Text, comment='笔记URL')
    publish_time = Column(String(255), index=True, comment='发布时间')
    user_link = Column(Text, default='', comment='用户链接')
    user_nickname = Column(Text, default='', comment='用户昵称')
    user_avatar = Column(Text, default='', comment='用户头像')
    tieba_id = Column(String(255), default='', comment='贴吧ID')
    tieba_name = Column(Text, comment='贴吧名称')
    tieba_link = Column(Text, comment='贴吧链接')
    total_replay_num = Column(Integer, default=0, comment='总回复数')
    total_replay_page = Column(Integer, default=0, comment='总回复页数')
    ip_location = Column(Text, default='', comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    source_keyword = Column(Text, default='', comment='来源关键词')

class TiebaComment(Base):
    __tablename__ = 'tieba_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    comment_id = Column(String(255), index=True, comment='评论ID')
    parent_comment_id = Column(String(255), default='', comment='父评论ID')
    content = Column(Text, comment='评论内容')
    user_link = Column(Text, default='', comment='用户链接')
    user_nickname = Column(Text, default='', comment='用户昵称')
    user_avatar = Column(Text, default='', comment='用户头像')
    tieba_id = Column(String(255), default='', comment='贴吧ID')
    tieba_name = Column(Text, comment='贴吧名称')
    tieba_link = Column(Text, comment='贴吧链接')
    publish_time = Column(String(255), index=True, comment='发布时间')
    ip_location = Column(Text, default='', comment='IP地址位置')
    sub_comment_count = Column(Integer, default=0, comment='子评论数')
    note_id = Column(String(255), index=True, comment='笔记ID')
    note_url = Column(Text, comment='笔记URL')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class TiebaCreator(Base):
    __tablename__ = 'tieba_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(64), comment='用户ID')
    user_name = Column(Text, comment='用户名')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    gender = Column(Text, comment='性别')
    follows = Column(Text, comment='关注数')
    fans = Column(Text, comment='粉丝数')
    registration_duration = Column(Text, comment='注册时长')

class ZhihuContent(Base):
    __tablename__ = 'zhihu_content'
    id = Column(Integer, primary_key=True, comment='主键ID')
    content_id = Column(String(64), index=True, comment='内容ID')
    content_type = Column(Text, comment='内容类型')
    content_text = Column(Text, comment='内容文本')
    content_url = Column(Text, comment='内容URL')
    question_id = Column(String(255), comment='问题ID')
    title = Column(Text, comment='标题')
    desc = Column(Text, comment='描述')
    created_time = Column(String(32), index=True, comment='创建时间')
    updated_time = Column(Text, comment='更新时间')
    voteup_count = Column(Integer, default=0, comment='赞同数')
    comment_count = Column(Integer, default=0, comment='评论数')
    source_keyword = Column(Text, comment='来源关键词')
    user_id = Column(String(255), comment='用户ID')
    user_link = Column(Text, comment='用户链接')
    user_nickname = Column(Text, comment='用户昵称')
    user_avatar = Column(Text, comment='用户头像')
    user_url_token = Column(Text, comment='用户URL Token')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

    # persist-1<persist1@126.com>
    # Reason: Fixed ORM model definition error, ensuring consistency with database table structure.
    # Side effects: None
    # Rollback strategy: Restore this line

class ZhihuComment(Base):
    __tablename__ = 'zhihu_comment'
    id = Column(Integer, primary_key=True, comment='主键ID')
    comment_id = Column(String(64), index=True, comment='评论ID')
    parent_comment_id = Column(String(64), comment='父评论ID')
    content = Column(Text, comment='评论内容')
    publish_time = Column(String(32), index=True, comment='发布时间')
    ip_location = Column(Text, comment='IP地址位置')
    sub_comment_count = Column(Integer, default=0, comment='子评论数')
    like_count = Column(Integer, default=0, comment='点赞数')
    dislike_count = Column(Integer, default=0, comment='点踩数')
    content_id = Column(String(64), index=True, comment='内容ID')
    content_type = Column(Text, comment='内容类型')
    user_id = Column(String(64), comment='用户ID')
    user_link = Column(Text, comment='用户链接')
    user_nickname = Column(Text, comment='用户昵称')
    user_avatar = Column(Text, comment='用户头像')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')

class ZhihuCreator(Base):
    __tablename__ = 'zhihu_creator'
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(64), unique=True, index=True, comment='用户ID')
    user_link = Column(Text, comment='用户链接')
    user_nickname = Column(Text, comment='用户昵称')
    user_avatar = Column(Text, comment='用户头像')
    url_token = Column(Text, comment='URL Token')
    gender = Column(Text, comment='性别')
    ip_location = Column(Text, comment='IP地址位置')
    follows = Column(Integer, default=0, comment='关注数')
    fans = Column(Integer, default=0, comment='粉丝数')
    anwser_count = Column(Integer, default=0, comment='回答数')
    video_count = Column(Integer, default=0, comment='视频数')
    question_count = Column(Integer, default=0, comment='问题数')
    article_count = Column(Integer, default=0, comment='文章数')
    column_count = Column(Integer, default=0, comment='专栏数')
    get_voteup_count = Column(Integer, default=0, comment='获赞数')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
