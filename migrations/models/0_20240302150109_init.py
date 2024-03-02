from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "xhs_note" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64) NOT NULL  /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "ip_location" VARCHAR(255)   /* 评论时的IP地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "note_id" VARCHAR(64) NOT NULL  /* 笔记ID */,
    "type" VARCHAR(16)   /* 笔记类型(normal | video) */,
    "title" VARCHAR(255)   /* 笔记标题 */,
    "desc" TEXT   /* 笔记描述 */,
    "time" BIGINT NOT NULL  /* 笔记发布时间戳 */,
    "last_update_time" BIGINT NOT NULL  /* 笔记最后更新时间戳 */,
    "liked_count" VARCHAR(16)   /* 笔记点赞数 */,
    "collected_count" VARCHAR(16)   /* 笔记收藏数 */,
    "comment_count" VARCHAR(16)   /* 笔记评论数 */,
    "share_count" VARCHAR(16)   /* 笔记分享数 */,
    "image_list" TEXT   /* 笔记封面图片列表 */,
    "note_url" VARCHAR(255)   /* 笔记详情页的URL */
) /* 小红书笔记 */;
CREATE INDEX IF NOT EXISTS "idx_xhs_note_note_id_209457" ON "xhs_note" ("note_id");
CREATE INDEX IF NOT EXISTS "idx_xhs_note_time_eaa910" ON "xhs_note" ("time");
CREATE TABLE IF NOT EXISTS "xhs_note_comment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64) NOT NULL  /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "ip_location" VARCHAR(255)   /* 评论时的IP地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "comment_id" VARCHAR(64) NOT NULL  /* 评论ID */,
    "create_time" BIGINT NOT NULL  /* 评论时间戳 */,
    "note_id" VARCHAR(64) NOT NULL  /* 笔记ID */,
    "content" TEXT NOT NULL  /* 评论内容 */,
    "sub_comment_count" INT NOT NULL  /* 子评论数量 */
) /* 小红书笔记评论 */;
CREATE INDEX IF NOT EXISTS "idx_xhs_note_co_comment_8e8349" ON "xhs_note_comment" ("comment_id");
CREATE INDEX IF NOT EXISTS "idx_xhs_note_co_create__204f8d" ON "xhs_note_comment" ("create_time");
CREATE TABLE IF NOT EXISTS "douyin_aweme" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "sec_uid" VARCHAR(128)   /* 用户sec_uid */,
    "short_user_id" VARCHAR(64)   /* 用户短ID */,
    "user_unique_id" VARCHAR(64)   /* 用户唯一ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "user_signature" VARCHAR(500)   /* 用户签名 */,
    "ip_location" VARCHAR(255)   /* 评论时的IP地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "aweme_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "aweme_type" VARCHAR(16) NOT NULL  /* 视频类型 */,
    "title" VARCHAR(500)   /* 视频标题 */,
    "desc" TEXT   /* 视频描述 */,
    "create_time" BIGINT NOT NULL  /* 视频发布时间戳 */,
    "liked_count" VARCHAR(16)   /* 视频点赞数 */,
    "comment_count" VARCHAR(16)   /* 视频评论数 */,
    "share_count" VARCHAR(16)   /* 视频分享数 */,
    "collected_count" VARCHAR(16)   /* 视频收藏数 */,
    "aweme_url" VARCHAR(255)   /* 视频详情页URL */
) /* 抖音视频 */;
CREATE INDEX IF NOT EXISTS "idx_douyin_awem_aweme_i_6f7bc6" ON "douyin_aweme" ("aweme_id");
CREATE INDEX IF NOT EXISTS "idx_douyin_awem_create__299dfe" ON "douyin_aweme" ("create_time");
CREATE TABLE IF NOT EXISTS "douyin_aweme_comment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "sec_uid" VARCHAR(128)   /* 用户sec_uid */,
    "short_user_id" VARCHAR(64)   /* 用户短ID */,
    "user_unique_id" VARCHAR(64)   /* 用户唯一ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "user_signature" VARCHAR(500)   /* 用户签名 */,
    "ip_location" VARCHAR(255)   /* 评论时的IP地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "comment_id" VARCHAR(64) NOT NULL  /* 评论ID */,
    "aweme_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "content" TEXT   /* 评论内容 */,
    "create_time" BIGINT NOT NULL  /* 评论时间戳 */,
    "sub_comment_count" VARCHAR(16) NOT NULL  /* 评论回复数 */
) /* 抖音视频评论 */;
CREATE INDEX IF NOT EXISTS "idx_douyin_awem_comment_fcd7e4" ON "douyin_aweme_comment" ("comment_id");
CREATE INDEX IF NOT EXISTS "idx_douyin_awem_aweme_i_c50049" ON "douyin_aweme_comment" ("aweme_id");
CREATE TABLE IF NOT EXISTS "bilibili_video_comment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "comment_id" VARCHAR(64) NOT NULL  /* 评论ID */,
    "video_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "content" TEXT   /* 评论内容 */,
    "create_time" BIGINT NOT NULL  /* 评论时间戳 */,
    "sub_comment_count" VARCHAR(16) NOT NULL  /* 评论回复数 */
) /* B 站视频评论 */;
CREATE INDEX IF NOT EXISTS "idx_bilibili_vi_comment_41c34e" ON "bilibili_video_comment" ("comment_id");
CREATE INDEX IF NOT EXISTS "idx_bilibili_vi_video_i_f22873" ON "bilibili_video_comment" ("video_id");
CREATE TABLE IF NOT EXISTS "bilibili_video" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "video_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "video_type" VARCHAR(16) NOT NULL  /* 视频类型 */,
    "title" VARCHAR(500)   /* 视频标题 */,
    "desc" TEXT   /* 视频描述 */,
    "create_time" BIGINT NOT NULL  /* 视频发布时间戳 */,
    "liked_count" VARCHAR(16)   /* 视频点赞数 */,
    "video_play_count" VARCHAR(16)   /* 视频播放数量 */,
    "video_danmaku" VARCHAR(16)   /* 视频弹幕数量 */,
    "video_comment" VARCHAR(16)   /* 视频评论数量 */,
    "video_url" VARCHAR(512)   /* 视频详情URL */,
    "video_cover_url" VARCHAR(512)   /* 视频封面图 URL */
) /* B站视频 */;
CREATE INDEX IF NOT EXISTS "idx_bilibili_vi_video_i_31c36e" ON "bilibili_video" ("video_id");
CREATE INDEX IF NOT EXISTS "idx_bilibili_vi_create__73e0ec" ON "bilibili_video" ("create_time");
CREATE TABLE IF NOT EXISTS "kuaishou_video" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "video_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "video_type" VARCHAR(16) NOT NULL  /* 视频类型 */,
    "title" VARCHAR(500)   /* 视频标题 */,
    "desc" TEXT   /* 视频描述 */,
    "create_time" BIGINT NOT NULL  /* 视频发布时间戳 */,
    "liked_count" VARCHAR(16)   /* 视频点赞数 */,
    "viewd_count" VARCHAR(16)   /* 视频浏览数量 */,
    "video_url" VARCHAR(512)   /* 视频详情URL */,
    "video_cover_url" VARCHAR(512)   /* 视频封面图 URL */,
    "video_play_url" VARCHAR(512)   /* 视频播放 URL */
) /* 快手视频 */;
CREATE INDEX IF NOT EXISTS "idx_kuaishou_vi_video_i_c5c6a6" ON "kuaishou_video" ("video_id");
CREATE INDEX IF NOT EXISTS "idx_kuaishou_vi_create__a10dee" ON "kuaishou_video" ("create_time");
CREATE TABLE IF NOT EXISTS "kuaishou_video_comment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "comment_id" VARCHAR(64) NOT NULL  /* 评论ID */,
    "video_id" VARCHAR(64) NOT NULL  /* 视频ID */,
    "content" TEXT   /* 评论内容 */,
    "create_time" BIGINT NOT NULL  /* 评论时间戳 */,
    "sub_comment_count" VARCHAR(16) NOT NULL  /* 评论回复数 */
) /* 快手视频评论 */;
CREATE INDEX IF NOT EXISTS "idx_kuaishou_vi_comment_ed48fa" ON "kuaishou_video_comment" ("comment_id");
CREATE INDEX IF NOT EXISTS "idx_kuaishou_vi_video_i_e50914" ON "kuaishou_video_comment" ("video_id");
CREATE TABLE IF NOT EXISTS "weibo_note_comment" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "gender" VARCHAR(12)   /* 用户性别 */,
    "profile_url" VARCHAR(255)   /* 用户主页地址 */,
    "ip_location" VARCHAR(32)   DEFAULT '发布微博的地理信息',
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "comment_id" VARCHAR(64) NOT NULL  /* 评论ID */,
    "note_id" VARCHAR(64) NOT NULL  /* 帖子ID */,
    "content" TEXT   /* 评论内容 */,
    "create_time" BIGINT NOT NULL  /* 评论时间戳 */,
    "create_date_time" VARCHAR(32) NOT NULL  /* 评论日期时间 */,
    "comment_like_count" VARCHAR(16) NOT NULL  /* 评论点赞数量 */,
    "sub_comment_count" VARCHAR(16) NOT NULL  /* 评论回复数 */
) /* 微博帖子评论 */;
CREATE INDEX IF NOT EXISTS "idx_weibo_note__comment_c7611c" ON "weibo_note_comment" ("comment_id");
CREATE INDEX IF NOT EXISTS "idx_weibo_note__note_id_24f108" ON "weibo_note_comment" ("note_id");
CREATE INDEX IF NOT EXISTS "idx_weibo_note__create__667fe3" ON "weibo_note_comment" ("create_date_time");
CREATE TABLE IF NOT EXISTS "weibo_note" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64)   /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "gender" VARCHAR(12)   /* 用户性别 */,
    "profile_url" VARCHAR(255)   /* 用户主页地址 */,
    "ip_location" VARCHAR(32)   DEFAULT '发布微博的地理信息',
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "note_id" VARCHAR(64) NOT NULL  /* 帖子ID */,
    "content" TEXT   /* 帖子正文内容 */,
    "create_time" BIGINT NOT NULL  /* 帖子发布时间戳 */,
    "create_date_time" VARCHAR(32) NOT NULL  /* 帖子发布日期时间 */,
    "liked_count" VARCHAR(16)   /* 帖子点赞数 */,
    "comments_count" VARCHAR(16)   /* 帖子评论数量 */,
    "shared_count" VARCHAR(16)   /* 帖子转发数量 */,
    "note_url" VARCHAR(512)   /* 帖子详情URL */
) /* 微博帖子 */;
CREATE INDEX IF NOT EXISTS "idx_weibo_note_note_id_f95b1a" ON "weibo_note" ("note_id");
CREATE INDEX IF NOT EXISTS "idx_weibo_note_create__692709" ON "weibo_note" ("create_time");
CREATE INDEX IF NOT EXISTS "idx_weibo_note_create__d05ed2" ON "weibo_note" ("create_date_time");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
