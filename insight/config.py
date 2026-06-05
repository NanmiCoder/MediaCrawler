# -*- coding: utf-8 -*-
"""insight 包的配置。纯数据，不含逻辑。"""

import os

# 项目根目录（insight/ 的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 爬虫写入的 SQLite 文件，必须与 config/db_config.py 的 SQLITE_DB_PATH 一致
DB_PATH = os.path.join(PROJECT_ROOT, "database", "sqlite_tables.db")

# 单次爬虫子进程的最大运行秒数，超时则杀死并记为 timeout
SUBPROCESS_TIMEOUT = 1800

# APScheduler 容忍的最大迟到秒数（睡眠/停机后仍补跑）
MISFIRE_GRACE_TIME = 3600

# 定时任务列表。每个 job 映射为一次爬虫调用。
# 必填键：name、type（"search"|"detail"|"creator"）、hour（0-23）
#   search  额外需要 "keywords"（英文逗号分隔的字符串）
#   detail  额外需要 "note_ids"（笔记 ID 或 URL 的列表）
#   creator 额外需要 "creator_ids"（创作者 ID 或 URL 的列表）
# 可选键：minute（默认 0）、max_notes（int）、max_comments（int）、get_sub_comment（bool）
JOBS = [
    {"name": "kw_daily", "type": "search", "keywords": "编程副业,编程兼职", "hour": 2, "minute": 0, "max_notes": 20},
    {"name": "watch_notes", "type": "detail", "note_ids": ["请替换为真实笔记ID"], "hour": 3, "minute": 0},
    {"name": "creator_daily", "type": "creator", "creator_ids": ["请替换为真实创作者ID"], "hour": 4, "minute": 0},
]
