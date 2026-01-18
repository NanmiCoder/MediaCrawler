"""
爆款内容识别器

功能：
1. 多维度评分（点赞、收藏、评论、增长速度）
2. 爆款等级分类（普通、小爆款、爆款、超级爆款）
3. 批量识别和排序
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class HotLevel(Enum):
    """爆款等级"""
    NORMAL = "normal"       # 普通
    TRENDING = "trending"   # 小爆款
    HOT = "hot"             # 爆款
    VIRAL = "viral"         # 超级爆款


@dataclass
class HotThresholds:
    """爆款阈值配置"""
    # 点赞阈值
    likes_trending: int = 1000      # 小爆款点赞阈值
    likes_hot: int = 5000           # 爆款点赞阈值
    likes_viral: int = 20000        # 超级爆款点赞阈值

    # 增长速度阈值（点赞/小时）
    growth_trending: float = 100
    growth_hot: float = 500
    growth_viral: float = 2000

    # 互动率阈值
    engagement_trending: float = 0.05
    engagement_hot: float = 0.10


class HotContentDetector:
    """爆款内容识别器"""

    def __init__(self, thresholds: Optional[HotThresholds] = None):
        """
        初始化识别器

        Args:
            thresholds: 爆款阈值配置，默认使用标准阈值
        """
        self.thresholds = thresholds or HotThresholds()

    def detect(
        self,
        note: Dict,
        publish_hours: Optional[float] = None
    ) -> Tuple[HotLevel, Dict]:
        """
        识别单条内容的爆款等级

        Args:
            note: 笔记数据字典，需包含 liked_count, collected_count, comment_count 等字段
            publish_hours: 发布时长（小时），用于计算增长速度

        Returns:
            (爆款等级, 分析详情字典)
        """
        # 提取互动数据
        liked_count = self._parse_count(note.get("liked_count") or note.get("likes", 0))
        collected_count = self._parse_count(note.get("collected_count") or note.get("collects", 0))
        comment_count = self._parse_count(note.get("comment_count") or note.get("comments", 0))
        share_count = self._parse_count(note.get("share_count") or note.get("shares", 0))

        # 计算总互动数
        total_engagement = liked_count + collected_count + comment_count + share_count

        # 计算收藏/点赞比例（比例高说明内容有干货价值）
        collection_ratio = collected_count / max(liked_count, 1)

        # 计算增长速度（如果有发布时间）
        growth_rate = None
        if publish_hours and publish_hours > 0:
            growth_rate = liked_count / publish_hours

        # 综合评分
        score = self._calculate_score(
            liked_count=liked_count,
            collection_ratio=collection_ratio,
            comment_count=comment_count,
            growth_rate=growth_rate
        )

        # 判定爆款等级
        level = self._determine_level(liked_count, score, growth_rate)

        # 构建分析详情
        analysis = {
            "liked_count": liked_count,
            "collected_count": collected_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "total_engagement": total_engagement,
            "collection_ratio": round(collection_ratio, 3),
            "growth_rate": round(growth_rate, 2) if growth_rate else None,
            "hot_score": round(score, 2),
            "level": level.value,
            "is_hot": level in (HotLevel.HOT, HotLevel.VIRAL),
            "is_trending": level != HotLevel.NORMAL,
            "detected_at": datetime.now().isoformat()
        }

        return level, analysis

    def _calculate_score(
        self,
        liked_count: int,
        collection_ratio: float,
        comment_count: int,
        growth_rate: Optional[float]
    ) -> float:
        """
        计算爆款综合得分（0-100）

        算法权重：
        - 点赞数: 40%（对数归一化，避免超级爆款压制一般爆款）
        - 收藏/点赞比: 20%（高比例说明干货内容）
        - 评论数: 20%（高评论说明话题性强）
        - 增长速度: 20%（快速增长说明正在爆发）
        """
        # 点赞分数（对数归一化）
        # log10(10000) = 4, 对应满分40分
        like_score = min(40, math.log10(max(liked_count, 1)) * 10)

        # 收藏比例分数（0.3以上算高价值内容）
        # 比例0.3对应满分20分
        collection_score = min(20, collection_ratio * 66.67)

        # 评论分数（对数归一化）
        # log10(1000) = 3, 对应满分20分
        comment_score = min(20, math.log10(max(comment_count, 1)) * 6.67)

        # 增长速度分数
        growth_score = 0
        if growth_rate:
            # log10(1000) = 3, 对应满分20分
            growth_score = min(20, math.log10(max(growth_rate, 1)) * 6.67)

        return like_score + collection_score + comment_score + growth_score

    def _determine_level(
        self,
        liked_count: int,
        score: float,
        growth_rate: Optional[float]
    ) -> HotLevel:
        """
        根据多维度判定爆款等级

        判定逻辑：
        1. 超级爆款：点赞超高 OR 综合得分极高
        2. 爆款：点赞高 OR 综合得分高 OR 增长极快
        3. 小爆款：点赞中等 OR 综合得分中等 OR 增长较快
        4. 普通：其他
        """
        # 超级爆款
        if liked_count >= self.thresholds.likes_viral or score >= 80:
            return HotLevel.VIRAL

        # 爆款
        if (liked_count >= self.thresholds.likes_hot or
            score >= 60 or
            (growth_rate and growth_rate >= self.thresholds.growth_hot)):
            return HotLevel.HOT

        # 小爆款
        if (liked_count >= self.thresholds.likes_trending or
            score >= 40 or
            (growth_rate and growth_rate >= self.thresholds.growth_trending)):
            return HotLevel.TRENDING

        return HotLevel.NORMAL

    def _parse_count(self, value) -> int:
        """
        解析数量字段

        支持格式：
        - int: 直接返回
        - str: "1234" -> 1234
        - str: "1.2万" -> 12000
        - str: "1.2w" -> 12000
        - None: 0
        """
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            value = value.replace(",", "").replace(" ", "").strip()
            if "万" in value:
                return int(float(value.replace("万", "")) * 10000)
            if "w" in value.lower():
                return int(float(value.lower().replace("w", "")) * 10000)
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0
        return 0

    def batch_detect(
        self,
        notes: List[Dict],
        min_level: HotLevel = HotLevel.TRENDING
    ) -> List[Dict]:
        """
        批量识别爆款内容

        Args:
            notes: 笔记列表
            min_level: 最低爆款等级过滤，默认只返回小爆款及以上

        Returns:
            带有爆款分析的笔记列表，按得分排序
        """
        hot_notes = []
        level_order = [HotLevel.NORMAL, HotLevel.TRENDING, HotLevel.HOT, HotLevel.VIRAL]
        min_index = level_order.index(min_level)

        for note in notes:
            # 计算发布时长
            publish_hours = self._calculate_publish_hours(note)

            # 识别爆款等级
            level, analysis = self.detect(note, publish_hours)

            # 过滤低于最低等级的内容
            if level_order.index(level) >= min_index:
                note_with_analysis = note.copy()
                note_with_analysis["hot_analysis"] = analysis
                hot_notes.append(note_with_analysis)

        # 按爆款得分排序
        hot_notes.sort(
            key=lambda x: x.get("hot_analysis", {}).get("hot_score", 0),
            reverse=True
        )

        return hot_notes

    def _calculate_publish_hours(self, note: Dict) -> Optional[float]:
        """计算发布时长（小时）"""
        publish_time = (
            note.get("time") or
            note.get("create_time") or
            note.get("publish_time") or
            note.get("last_update_time")
        )

        if not publish_time:
            return None

        try:
            if isinstance(publish_time, (int, float)):
                # 时间戳（毫秒或秒）
                if publish_time > 1e12:  # 毫秒
                    publish_dt = datetime.fromtimestamp(publish_time / 1000)
                else:  # 秒
                    publish_dt = datetime.fromtimestamp(publish_time)
            elif isinstance(publish_time, str):
                # ISO 格式字符串
                publish_dt = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
            elif isinstance(publish_time, datetime):
                publish_dt = publish_time
            else:
                return None

            return (datetime.now() - publish_dt).total_seconds() / 3600
        except Exception:
            return None

    def get_level_stats(self, notes: List[Dict]) -> Dict:
        """
        获取笔记列表的爆款等级统计

        Returns:
            {
                "total": 100,
                "normal": 60,
                "trending": 25,
                "hot": 12,
                "viral": 3
            }
        """
        stats = {
            "total": len(notes),
            "normal": 0,
            "trending": 0,
            "hot": 0,
            "viral": 0
        }

        for note in notes:
            level, _ = self.detect(note)
            stats[level.value] += 1

        return stats
