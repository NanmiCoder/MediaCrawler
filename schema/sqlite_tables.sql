-- SQLite版本的MediaCrawler数据库表结构
-- 从MySQL tables.sql转换而来，适配SQLite语法

-- ----------------------------
-- Table structure for bilibili_video
-- ----------------------------
DROP TABLE IF EXISTS bilibili_video;
CREATE TABLE bilibili_video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    video_id TEXT NOT NULL,
    video_type TEXT NOT NULL,
    title TEXT DEFAULT NULL,
    desc TEXT,
    create_time INTEGER NOT NULL,
    liked_count TEXT DEFAULT NULL,
    disliked_count TEXT DEFAULT NULL,
    video_play_count TEXT DEFAULT NULL,
    video_favorite_count TEXT DEFAULT NULL,
    video_share_count TEXT DEFAULT NULL,
    video_coin_count TEXT DEFAULT NULL,
    video_danmaku TEXT DEFAULT NULL,
    video_comment TEXT DEFAULT NULL,
    video_url TEXT DEFAULT NULL,
    video_cover_url TEXT DEFAULT NULL,
    source_keyword TEXT DEFAULT ''
);

CREATE INDEX idx_bilibili_vi_video_i_31c36e ON bilibili_video(video_id);
CREATE INDEX idx_bilibili_vi_create__73e0ec ON bilibili_video(create_time);

-- ----------------------------
-- Table structure for bilibili_video_comment
-- ----------------------------
DROP TABLE IF EXISTS bilibili_video_comment;
CREATE TABLE bilibili_video_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    sex TEXT DEFAULT NULL,
    sign TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    comment_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    content TEXT,
    create_time INTEGER NOT NULL,
    sub_comment_count TEXT NOT NULL,
    parent_comment_id TEXT DEFAULT NULL,
    like_count TEXT NOT NULL DEFAULT '0'
);

CREATE INDEX idx_bilibili_vi_comment_41c34e ON bilibili_video_comment(comment_id);
CREATE INDEX idx_bilibili_vi_video_i_f22873 ON bilibili_video_comment(video_id);

-- ----------------------------
-- Table structure for bilibili_up_info
-- ----------------------------
DROP TABLE IF EXISTS bilibili_up_info;
CREATE TABLE bilibili_up_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    sex TEXT DEFAULT NULL,
    sign TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    total_fans INTEGER DEFAULT NULL,
    total_liked INTEGER DEFAULT NULL,
    user_rank INTEGER DEFAULT NULL,
    is_official INTEGER DEFAULT NULL
);

CREATE INDEX idx_bilibili_vi_user_123456 ON bilibili_up_info(user_id);

-- ----------------------------
-- Table structure for bilibili_contact_info
-- ----------------------------
DROP TABLE IF EXISTS bilibili_contact_info;
CREATE TABLE bilibili_contact_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    up_id TEXT DEFAULT NULL,
    fan_id TEXT DEFAULT NULL,
    up_name TEXT DEFAULT NULL,
    fan_name TEXT DEFAULT NULL,
    up_sign TEXT DEFAULT NULL,
    fan_sign TEXT DEFAULT NULL,
    up_avatar TEXT DEFAULT NULL,
    fan_avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE INDEX idx_bilibili_contact_info_up_id ON bilibili_contact_info(up_id);
CREATE INDEX idx_bilibili_contact_info_fan_id ON bilibili_contact_info(fan_id);

-- ----------------------------
-- Table structure for bilibili_up_dynamic
-- ----------------------------
DROP TABLE IF EXISTS bilibili_up_dynamic;
CREATE TABLE bilibili_up_dynamic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynamic_id TEXT DEFAULT NULL,
    user_id TEXT DEFAULT NULL,
    user_name TEXT DEFAULT NULL,
    text TEXT DEFAULT NULL,
    type TEXT DEFAULT NULL,
    pub_ts INTEGER DEFAULT NULL,
    total_comments INTEGER DEFAULT NULL,
    total_forwards INTEGER DEFAULT NULL,
    total_liked INTEGER DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE INDEX idx_bilibili_up_dynamic_dynamic_id ON bilibili_up_dynamic(dynamic_id);

-- ----------------------------
-- Table structure for douyin_aweme
-- ----------------------------
DROP TABLE IF EXISTS douyin_aweme;
CREATE TABLE douyin_aweme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    sec_uid TEXT DEFAULT NULL,
    short_user_id TEXT DEFAULT NULL,
    user_unique_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    user_signature TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    aweme_id TEXT NOT NULL,
    aweme_type TEXT NOT NULL,
    title TEXT DEFAULT NULL,
    desc TEXT,
    create_time INTEGER NOT NULL,
    liked_count TEXT DEFAULT NULL,
    comment_count TEXT DEFAULT NULL,
    share_count TEXT DEFAULT NULL,
    collected_count TEXT DEFAULT NULL,
    aweme_url TEXT DEFAULT NULL,
    cover_url TEXT DEFAULT NULL,
    video_download_url TEXT DEFAULT NULL,
    music_download_url TEXT DEFAULT NULL,
    source_keyword TEXT DEFAULT ''
);

CREATE INDEX idx_douyin_awem_aweme_i_6f7bc6 ON douyin_aweme(aweme_id);
CREATE INDEX idx_douyin_awem_create__299dfe ON douyin_aweme(create_time);

-- ----------------------------
-- Table structure for douyin_aweme_comment
-- ----------------------------
DROP TABLE IF EXISTS douyin_aweme_comment;
CREATE TABLE douyin_aweme_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    sec_uid TEXT DEFAULT NULL,
    short_user_id TEXT DEFAULT NULL,
    user_unique_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    user_signature TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    comment_id TEXT NOT NULL,
    aweme_id TEXT NOT NULL,
    content TEXT,
    create_time INTEGER NOT NULL,
    sub_comment_count TEXT NOT NULL,
    parent_comment_id TEXT DEFAULT NULL,
    like_count TEXT NOT NULL DEFAULT '0',
    pictures TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_douyin_awem_comment_fcd7e4 ON douyin_aweme_comment(comment_id);
CREATE INDEX idx_douyin_awem_aweme_i_c50049 ON douyin_aweme_comment(aweme_id);

-- ----------------------------
-- Table structure for dy_creator
-- ----------------------------
DROP TABLE IF EXISTS dy_creator;
CREATE TABLE dy_creator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    desc TEXT,
    gender TEXT DEFAULT NULL,
    follows TEXT DEFAULT NULL,
    fans TEXT DEFAULT NULL,
    interaction TEXT DEFAULT NULL,
    videos_count TEXT DEFAULT NULL
);

-- ----------------------------
-- Table structure for kuaishou_video
-- ----------------------------
DROP TABLE IF EXISTS kuaishou_video;
CREATE TABLE kuaishou_video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    video_id TEXT NOT NULL,
    video_type TEXT NOT NULL,
    title TEXT DEFAULT NULL,
    desc TEXT,
    create_time INTEGER NOT NULL,
    liked_count TEXT DEFAULT NULL,
    viewd_count TEXT DEFAULT NULL,
    video_url TEXT DEFAULT NULL,
    video_cover_url TEXT DEFAULT NULL,
    video_play_url TEXT DEFAULT NULL,
    source_keyword TEXT DEFAULT ''
);

CREATE INDEX idx_kuaishou_vi_video_i_c5c6a6 ON kuaishou_video(video_id);
CREATE INDEX idx_kuaishou_vi_create__a10dee ON kuaishou_video(create_time);

-- ----------------------------
-- Table structure for kuaishou_video_comment
-- ----------------------------
DROP TABLE IF EXISTS kuaishou_video_comment;
CREATE TABLE kuaishou_video_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    comment_id TEXT NOT NULL,
    video_id TEXT NOT NULL,
    content TEXT,
    create_time INTEGER NOT NULL,
    sub_comment_count TEXT NOT NULL
);

CREATE INDEX idx_kuaishou_vi_comment_ed48fa ON kuaishou_video_comment(comment_id);
CREATE INDEX idx_kuaishou_vi_video_i_e50914 ON kuaishou_video_comment(video_id);

-- ----------------------------
-- Table structure for weibo_note
-- ----------------------------
DROP TABLE IF EXISTS weibo_note;
CREATE TABLE weibo_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    gender TEXT DEFAULT NULL,
    profile_url TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT '',
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    note_id TEXT NOT NULL,
    content TEXT,
    create_time INTEGER NOT NULL,
    create_date_time TEXT NOT NULL,
    liked_count TEXT DEFAULT NULL,
    comments_count TEXT DEFAULT NULL,
    shared_count TEXT DEFAULT NULL,
    note_url TEXT DEFAULT NULL,
    source_keyword TEXT DEFAULT ''
);

CREATE INDEX idx_weibo_note_note_id_f95b1a ON weibo_note(note_id);
CREATE INDEX idx_weibo_note_create__692709 ON weibo_note(create_time);
CREATE INDEX idx_weibo_note_create__d05ed2 ON weibo_note(create_date_time);

-- ----------------------------
-- Table structure for weibo_note_comment
-- ----------------------------
DROP TABLE IF EXISTS weibo_note_comment;
CREATE TABLE weibo_note_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT DEFAULT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    gender TEXT DEFAULT NULL,
    profile_url TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT '',
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    comment_id TEXT NOT NULL,
    note_id TEXT NOT NULL,
    content TEXT,
    create_time INTEGER NOT NULL,
    create_date_time TEXT NOT NULL,
    comment_like_count TEXT NOT NULL,
    sub_comment_count TEXT NOT NULL,
    parent_comment_id TEXT DEFAULT NULL
);

CREATE INDEX idx_weibo_note__comment_c7611c ON weibo_note_comment(comment_id);
CREATE INDEX idx_weibo_note__note_id_24f108 ON weibo_note_comment(note_id);
CREATE INDEX idx_weibo_note__create__667fe3 ON weibo_note_comment(create_date_time);

-- ----------------------------
-- Table structure for weibo_creator
-- ----------------------------
DROP TABLE IF EXISTS weibo_creator;
CREATE TABLE weibo_creator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    desc TEXT,
    gender TEXT DEFAULT NULL,
    follows TEXT DEFAULT NULL,
    fans TEXT DEFAULT NULL,
    tag_list TEXT
);

-- ----------------------------
-- Table structure for xhs_creator
-- ----------------------------
DROP TABLE IF EXISTS xhs_creator;
CREATE TABLE xhs_creator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    desc TEXT,
    gender TEXT DEFAULT NULL,
    follows TEXT DEFAULT NULL,
    fans TEXT DEFAULT NULL,
    interaction TEXT DEFAULT NULL,
    tag_list TEXT
);

-- ----------------------------
-- Table structure for xhs_note
-- ----------------------------
DROP TABLE IF EXISTS xhs_note;
CREATE TABLE xhs_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    note_id TEXT NOT NULL,
    type TEXT DEFAULT NULL,
    title TEXT DEFAULT NULL,
    desc TEXT,
    video_url TEXT,
    time INTEGER NOT NULL,
    last_update_time INTEGER NOT NULL,
    liked_count TEXT DEFAULT NULL,
    collected_count TEXT DEFAULT NULL,
    comment_count TEXT DEFAULT NULL,
    share_count TEXT DEFAULT NULL,
    image_list TEXT,
    tag_list TEXT,
    note_url TEXT DEFAULT NULL,
    source_keyword TEXT DEFAULT '',
    xsec_token TEXT DEFAULT NULL
);

CREATE INDEX idx_xhs_note_note_id_209457 ON xhs_note(note_id);
CREATE INDEX idx_xhs_note_time_eaa910 ON xhs_note(time);

-- ----------------------------
-- Table structure for xhs_note_comment
-- ----------------------------
DROP TABLE IF EXISTS xhs_note_comment;
CREATE TABLE xhs_note_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    comment_id TEXT NOT NULL,
    create_time INTEGER NOT NULL,
    note_id TEXT NOT NULL,
    content TEXT NOT NULL,
    sub_comment_count INTEGER NOT NULL,
    pictures TEXT DEFAULT NULL,
    parent_comment_id TEXT DEFAULT NULL,
    like_count TEXT DEFAULT NULL
);

CREATE INDEX idx_xhs_note_co_comment_8e8349 ON xhs_note_comment(comment_id);
CREATE INDEX idx_xhs_note_co_create__204f8d ON xhs_note_comment(create_time);

-- ----------------------------
-- Table structure for tieba_note
-- ----------------------------
DROP TABLE IF EXISTS tieba_note;
CREATE TABLE tieba_note (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id TEXT NOT NULL,
    title TEXT NOT NULL,
    desc TEXT,
    note_url TEXT NOT NULL,
    publish_time TEXT NOT NULL,
    user_link TEXT DEFAULT '',
    user_nickname TEXT DEFAULT '',
    user_avatar TEXT DEFAULT '',
    tieba_id TEXT DEFAULT '',
    tieba_name TEXT NOT NULL,
    tieba_link TEXT NOT NULL,
    total_replay_num INTEGER DEFAULT 0,
    total_replay_page INTEGER DEFAULT 0,
    ip_location TEXT DEFAULT '',
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    source_keyword TEXT DEFAULT ''
);

CREATE INDEX idx_tieba_note_note_id ON tieba_note(note_id);
CREATE INDEX idx_tieba_note_publish_time ON tieba_note(publish_time);

-- ----------------------------
-- Table structure for tieba_comment
-- ----------------------------
DROP TABLE IF EXISTS tieba_comment;
CREATE TABLE tieba_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id TEXT NOT NULL,
    parent_comment_id TEXT DEFAULT '',
    content TEXT NOT NULL,
    user_link TEXT DEFAULT '',
    user_nickname TEXT DEFAULT '',
    user_avatar TEXT DEFAULT '',
    tieba_id TEXT DEFAULT '',
    tieba_name TEXT NOT NULL,
    tieba_link TEXT NOT NULL,
    publish_time TEXT DEFAULT '',
    ip_location TEXT DEFAULT '',
    sub_comment_count INTEGER DEFAULT 0,
    note_id TEXT NOT NULL,
    note_url TEXT NOT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE INDEX idx_tieba_comment_comment_id ON tieba_comment(comment_id);
CREATE INDEX idx_tieba_comment_note_id ON tieba_comment(note_id);
CREATE INDEX idx_tieba_comment_publish_time ON tieba_comment(publish_time);

-- ----------------------------
-- Table structure for tieba_creator
-- ----------------------------
DROP TABLE IF EXISTS tieba_creator;
CREATE TABLE tieba_creator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    nickname TEXT DEFAULT NULL,
    avatar TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL,
    gender TEXT DEFAULT NULL,
    follows TEXT DEFAULT NULL,
    fans TEXT DEFAULT NULL,
    registration_duration TEXT DEFAULT NULL
);

-- ----------------------------
-- Table structure for zhihu_content
-- ----------------------------
DROP TABLE IF EXISTS zhihu_content;
CREATE TABLE zhihu_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    content_text TEXT,
    content_url TEXT NOT NULL,
    question_id TEXT DEFAULT NULL,
    title TEXT NOT NULL,
    desc TEXT,
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    voteup_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    source_keyword TEXT DEFAULT NULL,
    user_id TEXT NOT NULL,
    user_link TEXT NOT NULL,
    user_nickname TEXT NOT NULL,
    user_avatar TEXT NOT NULL,
    user_url_token TEXT NOT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE INDEX idx_zhihu_content_content_id ON zhihu_content(content_id);
CREATE INDEX idx_zhihu_content_created_time ON zhihu_content(created_time);

-- ----------------------------
-- Table structure for zhihu_comment
-- ----------------------------
DROP TABLE IF EXISTS zhihu_comment;
CREATE TABLE zhihu_comment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id TEXT NOT NULL,
    parent_comment_id TEXT DEFAULT NULL,
    content TEXT NOT NULL,
    publish_time TEXT NOT NULL,
    ip_location TEXT DEFAULT NULL,
    sub_comment_count INTEGER NOT NULL DEFAULT 0,
    like_count INTEGER NOT NULL DEFAULT 0,
    dislike_count INTEGER NOT NULL DEFAULT 0,
    content_id TEXT NOT NULL,
    content_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_link TEXT NOT NULL,
    user_nickname TEXT NOT NULL,
    user_avatar TEXT NOT NULL,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE INDEX idx_zhihu_comment_comment_id ON zhihu_comment(comment_id);
CREATE INDEX idx_zhihu_comment_content_id ON zhihu_comment(content_id);
CREATE INDEX idx_zhihu_comment_publish_time ON zhihu_comment(publish_time);

-- ----------------------------
-- Table structure for zhihu_creator
-- ----------------------------
DROP TABLE IF EXISTS zhihu_creator;
CREATE TABLE zhihu_creator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    user_link TEXT NOT NULL,
    user_nickname TEXT NOT NULL,
    user_avatar TEXT NOT NULL,
    url_token TEXT NOT NULL,
    gender TEXT DEFAULT NULL,
    ip_location TEXT DEFAULT NULL,
    follows INTEGER NOT NULL DEFAULT 0,
    fans INTEGER NOT NULL DEFAULT 0,
    anwser_count INTEGER NOT NULL DEFAULT 0,
    video_count INTEGER NOT NULL DEFAULT 0,
    question_count INTEGER NOT NULL DEFAULT 0,
    article_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    get_voteup_count INTEGER NOT NULL DEFAULT 0,
    add_ts INTEGER NOT NULL,
    last_modify_ts INTEGER NOT NULL
);

CREATE UNIQUE INDEX idx_zhihu_creator_user_id ON zhihu_creator(user_id);