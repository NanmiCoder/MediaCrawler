"""
监控模块配置
"""
import os

# ==================== 监控配置 ====================

# 默认监控间隔（分钟）
MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "30"))

# 每个账号每次最多抓取笔记数
MONITOR_MAX_NOTES_PER_ACCOUNT = int(os.getenv("MONITOR_MAX_NOTES_PER_ACCOUNT", "20"))

# 请求间隔（秒）
MONITOR_REQUEST_INTERVAL = float(os.getenv("MONITOR_REQUEST_INTERVAL", "2.0"))

# 是否启用增量抓取（只抓新内容）
MONITOR_INCREMENTAL = os.getenv("MONITOR_INCREMENTAL", "true").lower() == "true"

# 是否自动启动监控（服务启动时）
MONITOR_AUTO_START = os.getenv("MONITOR_AUTO_START", "false").lower() == "true"

# 数据保留天数（超过此天数的数据会被清理）
MONITOR_DATA_RETENTION_DAYS = int(os.getenv("MONITOR_DATA_RETENTION_DAYS", "30"))


# ==================== 爆款阈值配置 ====================

# 爆款等级阈值
HOT_LEVEL_THRESHOLDS = {
    "trending": {
        "likes": int(os.getenv("HOT_TRENDING_LIKES", "1000")),
        "growth_rate": float(os.getenv("HOT_TRENDING_GROWTH", "100")),  # 点赞/小时
    },
    "hot": {
        "likes": int(os.getenv("HOT_HOT_LIKES", "5000")),
        "growth_rate": float(os.getenv("HOT_HOT_GROWTH", "500")),
    },
    "viral": {
        "likes": int(os.getenv("HOT_VIRAL_LIKES", "20000")),
        "growth_rate": float(os.getenv("HOT_VIRAL_GROWTH", "2000")),
    }
}

# 爆款评分权重
HOT_SCORE_WEIGHTS = {
    "likes": 0.4,      # 点赞权重 40%
    "collects": 0.2,   # 收藏比例权重 20%
    "comments": 0.2,   # 评论权重 20%
    "growth": 0.2      # 增长速度权重 20%
}


# ==================== MongoDB 集合配置 ====================

# 监控数据集合前缀
MONITOR_COLLECTION_PREFIX = "monitor"

# 集合名称
MONITOR_COLLECTIONS = {
    "accounts": f"{MONITOR_COLLECTION_PREFIX}_accounts",      # 监控账号
    "notes": f"{MONITOR_COLLECTION_PREFIX}_notes",            # 监控到的笔记
    "hot_notes": f"{MONITOR_COLLECTION_PREFIX}_hot_notes",    # 爆款笔记
    "crawl_history": f"{MONITOR_COLLECTION_PREFIX}_history",  # 抓取历史
    "keywords": f"{MONITOR_COLLECTION_PREFIX}_keywords"       # 关键词配置
}


# ==================== 定时任务配置 ====================

# 默认定时任务
SCHEDULER_JOBS = [
    {
        "id": "crawl_accounts",
        "trigger": "interval",
        "hours": 6,  # 每6小时抓取一次
        "description": "定时抓取监控账号的新内容"
    },
    {
        "id": "update_trending",
        "trigger": "interval",
        "hours": 1,  # 每小时更新爆款分数
        "description": "更新爆款评分"
    },
    {
        "id": "cleanup_old_data",
        "trigger": "cron",
        "hour": 3,  # 每天凌晨3点
        "description": "清理过期数据"
    }
]
