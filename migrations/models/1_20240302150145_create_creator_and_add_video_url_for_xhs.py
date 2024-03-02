from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "xhs_note" ADD "video_url" TEXT   /* 视频地址 */;
        ALTER TABLE "xhs_note" ADD "tag_list" TEXT   /* 标签列表 */;
        CREATE TABLE IF NOT EXISTS "xhs_creator" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 自增ID */,
    "user_id" VARCHAR(64) NOT NULL  /* 用户ID */,
    "nickname" VARCHAR(64)   /* 用户昵称 */,
    "avatar" VARCHAR(255)   /* 用户头像地址 */,
    "ip_location" VARCHAR(255)   /* 评论时的IP地址 */,
    "add_ts" BIGINT NOT NULL  /* 记录添加时间戳 */,
    "last_modify_ts" BIGINT NOT NULL  /* 记录最后修改时间戳 */,
    "desc" TEXT   /* 用户描述 */,
    "gender" VARCHAR(1)   /* 性别 */,
    "follows" VARCHAR(16)   /* 关注数 */,
    "fans" VARCHAR(16)   /* 粉丝数 */,
    "interaction" VARCHAR(16)   /* 获赞和收藏数 */,
    "tag_list" TEXT   /* 标签列表 */
) /* 小红书博主 */;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "xhs_note" DROP COLUMN "video_url";
        ALTER TABLE "xhs_note" DROP COLUMN "tag_list";
        DROP TABLE IF EXISTS "xhs_creator";"""
