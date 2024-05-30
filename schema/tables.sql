-- ----------------------------
-- Table structure for bilibili_video
-- ----------------------------
DROP TABLE IF EXISTS `bilibili_video`;
CREATE TABLE `bilibili_video` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `video_id` varchar(64) NOT NULL COMMENT '视频ID',
  `video_type` varchar(16) NOT NULL COMMENT '视频类型',
  `title` varchar(500) DEFAULT NULL COMMENT '视频标题',
  `desc` longtext COMMENT '视频描述',
  `create_time` bigint NOT NULL COMMENT '视频发布时间戳',
  `liked_count` varchar(16) DEFAULT NULL COMMENT '视频点赞数',
  `video_play_count` varchar(16) DEFAULT NULL COMMENT '视频播放数量',
  `video_danmaku` varchar(16) DEFAULT NULL COMMENT '视频弹幕数量',
  `video_comment` varchar(16) DEFAULT NULL COMMENT '视频评论数量',
  `video_url` varchar(512) DEFAULT NULL COMMENT '视频详情URL',
  `video_cover_url` varchar(512) DEFAULT NULL COMMENT '视频封面图 URL',
  PRIMARY KEY (`id`),
  KEY `idx_bilibili_vi_video_i_31c36e` (`video_id`),
  KEY `idx_bilibili_vi_create__73e0ec` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='B站视频';

-- ----------------------------
-- Table structure for bilibili_video_comment
-- ----------------------------
DROP TABLE IF EXISTS `bilibili_video_comment`;
CREATE TABLE `bilibili_video_comment` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `comment_id` varchar(64) NOT NULL COMMENT '评论ID',
  `video_id` varchar(64) NOT NULL COMMENT '视频ID',
  `content` longtext COMMENT '评论内容',
  `create_time` bigint NOT NULL COMMENT '评论时间戳',
  `sub_comment_count` varchar(16) NOT NULL COMMENT '评论回复数',
  PRIMARY KEY (`id`),
  KEY `idx_bilibili_vi_comment_41c34e` (`comment_id`),
  KEY `idx_bilibili_vi_video_i_f22873` (`video_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='B 站视频评论';

-- ----------------------------
-- Table structure for douyin_aweme
-- ----------------------------
DROP TABLE IF EXISTS `douyin_aweme`;
CREATE TABLE `douyin_aweme` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `sec_uid` varchar(128) DEFAULT NULL COMMENT '用户sec_uid',
  `short_user_id` varchar(64) DEFAULT NULL COMMENT '用户短ID',
  `user_unique_id` varchar(64) DEFAULT NULL COMMENT '用户唯一ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `user_signature` varchar(500) DEFAULT NULL COMMENT '用户签名',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `aweme_id` varchar(64) NOT NULL COMMENT '视频ID',
  `aweme_type` varchar(16) NOT NULL COMMENT '视频类型',
  `title` varchar(500) DEFAULT NULL COMMENT '视频标题',
  `desc` longtext COMMENT '视频描述',
  `create_time` bigint NOT NULL COMMENT '视频发布时间戳',
  `liked_count` varchar(16) DEFAULT NULL COMMENT '视频点赞数',
  `comment_count` varchar(16) DEFAULT NULL COMMENT '视频评论数',
  `share_count` varchar(16) DEFAULT NULL COMMENT '视频分享数',
  `collected_count` varchar(16) DEFAULT NULL COMMENT '视频收藏数',
  `aweme_url` varchar(255) DEFAULT NULL COMMENT '视频详情页URL',
  PRIMARY KEY (`id`),
  KEY `idx_douyin_awem_aweme_i_6f7bc6` (`aweme_id`),
  KEY `idx_douyin_awem_create__299dfe` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='抖音视频';

-- ----------------------------
-- Table structure for douyin_aweme_comment
-- ----------------------------
DROP TABLE IF EXISTS `douyin_aweme_comment`;
CREATE TABLE `douyin_aweme_comment` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `sec_uid` varchar(128) DEFAULT NULL COMMENT '用户sec_uid',
  `short_user_id` varchar(64) DEFAULT NULL COMMENT '用户短ID',
  `user_unique_id` varchar(64) DEFAULT NULL COMMENT '用户唯一ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `user_signature` varchar(500) DEFAULT NULL COMMENT '用户签名',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `comment_id` varchar(64) NOT NULL COMMENT '评论ID',
  `aweme_id` varchar(64) NOT NULL COMMENT '视频ID',
  `content` longtext COMMENT '评论内容',
  `create_time` bigint NOT NULL COMMENT '评论时间戳',
  `sub_comment_count` varchar(16) NOT NULL COMMENT '评论回复数',
  PRIMARY KEY (`id`),
  KEY `idx_douyin_awem_comment_fcd7e4` (`comment_id`),
  KEY `idx_douyin_awem_aweme_i_c50049` (`aweme_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='抖音视频评论';

-- ----------------------------
-- Table structure for dy_creator
-- ----------------------------
DROP TABLE IF EXISTS `dy_creator`;
CREATE TABLE `dy_creator` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(128) NOT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `desc` longtext COMMENT '用户描述',
  `gender` varchar(1) DEFAULT NULL COMMENT '性别',
  `follows` varchar(16) DEFAULT NULL COMMENT '关注数',
  `fans` varchar(16) DEFAULT NULL COMMENT '粉丝数',
  `interaction` varchar(16) DEFAULT NULL COMMENT '获赞数',
  `videos_count` varchar(16) DEFAULT NULL COMMENT '作品数',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='抖音博主信息';

-- ----------------------------
-- Table structure for kuaishou_video
-- ----------------------------
DROP TABLE IF EXISTS `kuaishou_video`;
CREATE TABLE `kuaishou_video` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `video_id` varchar(64) NOT NULL COMMENT '视频ID',
  `video_type` varchar(16) NOT NULL COMMENT '视频类型',
  `title` varchar(500) DEFAULT NULL COMMENT '视频标题',
  `desc` longtext COMMENT '视频描述',
  `create_time` bigint NOT NULL COMMENT '视频发布时间戳',
  `liked_count` varchar(16) DEFAULT NULL COMMENT '视频点赞数',
  `viewd_count` varchar(16) DEFAULT NULL COMMENT '视频浏览数量',
  `video_url` varchar(512) DEFAULT NULL COMMENT '视频详情URL',
  `video_cover_url` varchar(512) DEFAULT NULL COMMENT '视频封面图 URL',
  `video_play_url` varchar(512) DEFAULT NULL COMMENT '视频播放 URL',
  PRIMARY KEY (`id`),
  KEY `idx_kuaishou_vi_video_i_c5c6a6` (`video_id`),
  KEY `idx_kuaishou_vi_create__a10dee` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='快手视频';

-- ----------------------------
-- Table structure for kuaishou_video_comment
-- ----------------------------
DROP TABLE IF EXISTS `kuaishou_video_comment`;
CREATE TABLE `kuaishou_video_comment` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `comment_id` varchar(64) NOT NULL COMMENT '评论ID',
  `video_id` varchar(64) NOT NULL COMMENT '视频ID',
  `content` longtext COMMENT '评论内容',
  `create_time` bigint NOT NULL COMMENT '评论时间戳',
  `sub_comment_count` varchar(16) NOT NULL COMMENT '评论回复数',
  PRIMARY KEY (`id`),
  KEY `idx_kuaishou_vi_comment_ed48fa` (`comment_id`),
  KEY `idx_kuaishou_vi_video_i_e50914` (`video_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='快手视频评论';


-- ----------------------------
-- Table structure for weibo_note
-- ----------------------------
DROP TABLE IF EXISTS `weibo_note`;
CREATE TABLE `weibo_note` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `gender` varchar(12) DEFAULT NULL COMMENT '用户性别',
  `profile_url` varchar(255) DEFAULT NULL COMMENT '用户主页地址',
  `ip_location` varchar(32) DEFAULT '发布微博的地理信息',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `note_id` varchar(64) NOT NULL COMMENT '帖子ID',
  `content` longtext COMMENT '帖子正文内容',
  `create_time` bigint NOT NULL COMMENT '帖子发布时间戳',
  `create_date_time` varchar(32) NOT NULL COMMENT '帖子发布日期时间',
  `liked_count` varchar(16) DEFAULT NULL COMMENT '帖子点赞数',
  `comments_count` varchar(16) DEFAULT NULL COMMENT '帖子评论数量',
  `shared_count` varchar(16) DEFAULT NULL COMMENT '帖子转发数量',
  `note_url` varchar(512) DEFAULT NULL COMMENT '帖子详情URL',
  PRIMARY KEY (`id`),
  KEY `idx_weibo_note_note_id_f95b1a` (`note_id`),
  KEY `idx_weibo_note_create__692709` (`create_time`),
  KEY `idx_weibo_note_create__d05ed2` (`create_date_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='微博帖子';

-- ----------------------------
-- Table structure for weibo_note_comment
-- ----------------------------
DROP TABLE IF EXISTS `weibo_note_comment`;
CREATE TABLE `weibo_note_comment` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) DEFAULT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `gender` varchar(12) DEFAULT NULL COMMENT '用户性别',
  `profile_url` varchar(255) DEFAULT NULL COMMENT '用户主页地址',
  `ip_location` varchar(32) DEFAULT '发布微博的地理信息',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `comment_id` varchar(64) NOT NULL COMMENT '评论ID',
  `note_id` varchar(64) NOT NULL COMMENT '帖子ID',
  `content` longtext COMMENT '评论内容',
  `create_time` bigint NOT NULL COMMENT '评论时间戳',
  `create_date_time` varchar(32) NOT NULL COMMENT '评论日期时间',
  `comment_like_count` varchar(16) NOT NULL COMMENT '评论点赞数量',
  `sub_comment_count` varchar(16) NOT NULL COMMENT '评论回复数',
  PRIMARY KEY (`id`),
  KEY `idx_weibo_note__comment_c7611c` (`comment_id`),
  KEY `idx_weibo_note__note_id_24f108` (`note_id`),
  KEY `idx_weibo_note__create__667fe3` (`create_date_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='微博帖子评论';

-- ----------------------------
-- Table structure for xhs_creator
-- ----------------------------
DROP TABLE IF EXISTS `xhs_creator`;
CREATE TABLE `xhs_creator` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `desc` longtext COMMENT '用户描述',
  `gender` varchar(1) DEFAULT NULL COMMENT '性别',
  `follows` varchar(16) DEFAULT NULL COMMENT '关注数',
  `fans` varchar(16) DEFAULT NULL COMMENT '粉丝数',
  `interaction` varchar(16) DEFAULT NULL COMMENT '获赞和收藏数',
  `tag_list` longtext COMMENT '标签列表',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='小红书博主';

-- ----------------------------
-- Table structure for xhs_note
-- ----------------------------
DROP TABLE IF EXISTS `xhs_note`;
CREATE TABLE `xhs_note` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `note_id` varchar(64) NOT NULL COMMENT '笔记ID',
  `type` varchar(16) DEFAULT NULL COMMENT '笔记类型(normal | video)',
  `title` varchar(255) DEFAULT NULL COMMENT '笔记标题',
  `desc` longtext COMMENT '笔记描述',
  `video_url` longtext COMMENT '视频地址',
  `time` bigint NOT NULL COMMENT '笔记发布时间戳',
  `last_update_time` bigint NOT NULL COMMENT '笔记最后更新时间戳',
  `liked_count` varchar(16) DEFAULT NULL COMMENT '笔记点赞数',
  `collected_count` varchar(16) DEFAULT NULL COMMENT '笔记收藏数',
  `comment_count` varchar(16) DEFAULT NULL COMMENT '笔记评论数',
  `share_count` varchar(16) DEFAULT NULL COMMENT '笔记分享数',
  `image_list` longtext COMMENT '笔记封面图片列表',
  `tag_list` longtext COMMENT '标签列表',
  `note_url` varchar(255) DEFAULT NULL COMMENT '笔记详情页的URL',
  PRIMARY KEY (`id`),
  KEY `idx_xhs_note_note_id_209457` (`note_id`),
  KEY `idx_xhs_note_time_eaa910` (`time`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='小红书笔记';

-- ----------------------------
-- Table structure for xhs_note_comment
-- ----------------------------
DROP TABLE IF EXISTS `xhs_note_comment`;
CREATE TABLE `xhs_note_comment` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增ID',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `nickname` varchar(64) DEFAULT NULL COMMENT '用户昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '用户头像地址',
  `ip_location` varchar(255) DEFAULT NULL COMMENT '评论时的IP地址',
  `add_ts` bigint NOT NULL COMMENT '记录添加时间戳',
  `last_modify_ts` bigint NOT NULL COMMENT '记录最后修改时间戳',
  `comment_id` varchar(64) NOT NULL COMMENT '评论ID',
  `create_time` bigint NOT NULL COMMENT '评论时间戳',
  `note_id` varchar(64) NOT NULL COMMENT '笔记ID',
  `content` longtext NOT NULL COMMENT '评论内容',
  `sub_comment_count` int NOT NULL COMMENT '子评论数量',
  `pictures` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_xhs_note_co_comment_8e8349` (`comment_id`),
  KEY `idx_xhs_note_co_create__204f8d` (`create_time`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='小红书笔记评论';

-- ----------------------------
-- alter table xhs_note_comment to support parent_comment_id
-- ----------------------------
ALTER TABLE `xhs_note_comment`
ADD COLUMN `parent_comment_id` VARCHAR(64) DEFAULT NULL COMMENT '父评论ID';


SET FOREIGN_KEY_CHECKS = 1;
