"""
定时任务调度器

功能：
1. 定时抓取监控账号的新内容
2. 定时更新爆款评分
3. 定时清理过期数据
"""

import asyncio
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from database.mongodb_store_base import MongoDBStoreBase
from tools import utils

from config.monitor_config import (
    MONITOR_INTERVAL_MINUTES,
    MONITOR_DATA_RETENTION_DAYS,
    SCHEDULER_JOBS
)
from .hot_content_detector import HotContentDetector, HotLevel


class MonitorScheduler:
    """
    监控定时任务调度器

    使用 APScheduler 实现异步定时任务。
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                'coalesce': True,  # 错过的任务合并执行
                'max_instances': 1,  # 同一任务最多1个实例
                'misfire_grace_time': 60  # 错过60秒内仍执行
            }
        )
        self._monitor = None
        self._hot_detector = HotContentDetector()
        self._mongo_store = MongoDBStoreBase(collection_prefix="monitor")
        self._is_running = False
        self._callbacks: Dict[str, Callable] = {}

    async def _get_monitor(self):
        """延迟获取监控器实例"""
        if self._monitor is None:
            from .account_monitor import get_monitor
            self._monitor = await get_monitor()
        return self._monitor

    def add_account_monitor_job(
        self,
        interval_minutes: int = None,
        job_id: str = "account_monitor",
        callback: Optional[Callable] = None
    ):
        """
        添加账号监控定时任务

        Args:
            interval_minutes: 监控间隔（分钟），默认使用配置值
            job_id: 任务ID
            callback: 发现新内容时的回调函数
        """
        interval = interval_minutes or MONITOR_INTERVAL_MINUTES

        if callback:
            self._callbacks[job_id] = callback

        async def monitor_task():
            try:
                utils.logger.info(f"[Scheduler] Running monitor task: {job_id}")

                # 获取监控账号列表
                accounts = await self._mongo_store.find_many(
                    "accounts",
                    {"is_active": True}
                )

                if not accounts:
                    utils.logger.info("[Scheduler] No active accounts to monitor")
                    return

                account_urls = [acc.get("url") for acc in accounts if acc.get("url")]

                if not account_urls:
                    utils.logger.info("[Scheduler] No valid account URLs")
                    return

                utils.logger.info(f"[Scheduler] Monitoring {len(account_urls)} accounts")

                # 执行监控
                monitor = await self._get_monitor()
                new_notes = await monitor.monitor_accounts(
                    account_urls=account_urls,
                    only_new=True
                )

                if new_notes:
                    utils.logger.info(f"[Scheduler] Found {len(new_notes)} new notes")

                    # 识别爆款
                    hot_notes = self._hot_detector.batch_detect(
                        new_notes,
                        min_level=HotLevel.TRENDING
                    )

                    if hot_notes:
                        utils.logger.info(f"[Scheduler] Detected {len(hot_notes)} hot notes")

                    # 执行回调
                    if job_id in self._callbacks:
                        cb = self._callbacks[job_id]
                        if asyncio.iscoroutinefunction(cb):
                            await cb(new_notes=new_notes, hot_notes=hot_notes)
                        else:
                            cb(new_notes=new_notes, hot_notes=hot_notes)
                else:
                    utils.logger.info("[Scheduler] No new content found")

            except Exception as e:
                utils.logger.error(f"[Scheduler] Monitor task error: {e}")

        # 添加定时任务
        self.scheduler.add_job(
            monitor_task,
            trigger=IntervalTrigger(minutes=interval),
            id=job_id,
            replace_existing=True
        )

        utils.logger.info(
            f"[Scheduler] Added monitor job: {job_id}, interval: {interval} minutes"
        )

    def add_trending_update_job(
        self,
        interval_hours: int = 1,
        job_id: str = "update_trending"
    ):
        """
        添加爆款评分更新任务

        定时重新计算笔记的爆款评分（因为点赞数等会变化）

        Args:
            interval_hours: 更新间隔（小时）
            job_id: 任务ID
        """
        async def update_task():
            try:
                utils.logger.info("[Scheduler] Updating trending scores...")

                # 获取最近7天的笔记
                seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()

                collection = await self._mongo_store.get_collection("notes")
                cursor = collection.find({
                    "crawled_at": {"$gte": seven_days_ago}
                })

                notes = await cursor.to_list(length=1000)
                updated_count = 0

                for note in notes:
                    level, analysis = self._hot_detector.detect(note)

                    # 更新爆款分析
                    await self._mongo_store.save_or_update(
                        "notes",
                        {"note_id": note.get("note_id")},
                        {"hot_analysis": analysis}
                    )

                    # 如果是爆款，更新爆款集合
                    if level != HotLevel.NORMAL:
                        await self._mongo_store.save_or_update(
                            "hot_notes",
                            {"note_id": note.get("note_id")},
                            {
                                "hot_level": level.value,
                                "hot_score": analysis.get("hot_score"),
                                "updated_at": datetime.now().isoformat()
                            }
                        )

                    updated_count += 1

                utils.logger.info(f"[Scheduler] Updated {updated_count} notes' trending scores")

            except Exception as e:
                utils.logger.error(f"[Scheduler] Update trending error: {e}")

        self.scheduler.add_job(
            update_task,
            trigger=IntervalTrigger(hours=interval_hours),
            id=job_id,
            replace_existing=True
        )

        utils.logger.info(f"[Scheduler] Added trending update job: {job_id}")

    def add_cleanup_job(
        self,
        retention_days: int = None,
        hour: int = 3,
        job_id: str = "cleanup"
    ):
        """
        添加数据清理任务

        定时清理过期的数据

        Args:
            retention_days: 数据保留天数
            hour: 每天执行的小时（0-23）
            job_id: 任务ID
        """
        days = retention_days or MONITOR_DATA_RETENTION_DAYS

        async def cleanup_task():
            try:
                utils.logger.info(f"[Scheduler] Cleaning up data older than {days} days...")

                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

                # 清理抓取历史
                history_collection = await self._mongo_store.get_collection("crawl_history")
                result = await history_collection.delete_many({
                    "crawled_at": {"$lt": cutoff_date}
                })
                utils.logger.info(f"[Scheduler] Deleted {result.deleted_count} crawl history records")

                # 清理旧的非爆款笔记
                notes_collection = await self._mongo_store.get_collection("notes")
                result = await notes_collection.delete_many({
                    "crawled_at": {"$lt": cutoff_date},
                    "hot_analysis.is_hot": {"$ne": True}
                })
                utils.logger.info(f"[Scheduler] Deleted {result.deleted_count} old notes")

            except Exception as e:
                utils.logger.error(f"[Scheduler] Cleanup error: {e}")

        self.scheduler.add_job(
            cleanup_task,
            trigger=CronTrigger(hour=hour, minute=0),
            id=job_id,
            replace_existing=True
        )

        utils.logger.info(f"[Scheduler] Added cleanup job: {job_id}, runs daily at {hour}:00")

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,
        job_id: str
    ):
        """
        添加自定义 Cron 任务

        Args:
            func: 异步任务函数
            cron_expression: Cron 表达式，如 "0 9,18 * * *" (每天9点和18点)
            job_id: 任务ID
        """
        parts = cron_expression.split()

        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )
        else:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True
        )

        utils.logger.info(f"[Scheduler] Added cron job: {job_id}, cron: {cron_expression}")

    def start(self):
        """启动调度器"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            utils.logger.info("[Scheduler] Scheduler started")

    def stop(self):
        """停止调度器"""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            utils.logger.info("[Scheduler] Scheduler stopped")

    def pause(self):
        """暂停调度器"""
        if self._is_running:
            self.scheduler.pause()
            utils.logger.info("[Scheduler] Scheduler paused")

    def resume(self):
        """恢复调度器"""
        if self._is_running:
            self.scheduler.resume()
            utils.logger.info("[Scheduler] Scheduler resumed")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def get_jobs(self) -> List[Dict]:
        """获取所有任务信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    def get_job(self, job_id: str) -> Optional[Dict]:
        """获取指定任务信息"""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        return None

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        try:
            self.scheduler.remove_job(job_id)
            utils.logger.info(f"[Scheduler] Removed job: {job_id}")
            return True
        except Exception:
            return False

    async def trigger_now(self, job_id: str = "account_monitor") -> Dict[str, Any]:
        """
        立即触发一次任务

        Args:
            job_id: 任务ID

        Returns:
            执行结果
        """
        try:
            utils.logger.info(f"[Scheduler] Manually triggering job: {job_id}")

            # 获取监控账号列表
            accounts = await self._mongo_store.find_many(
                "accounts",
                {"is_active": True}
            )

            if not accounts:
                return {"success": False, "message": "No active accounts"}

            account_urls = [acc.get("url") for acc in accounts if acc.get("url")]

            if not account_urls:
                return {"success": False, "message": "No valid account URLs"}

            # 执行监控
            monitor = await self._get_monitor()
            new_notes = await monitor.monitor_accounts(
                account_urls=account_urls,
                only_new=True
            )

            # 识别爆款
            hot_notes = self._hot_detector.batch_detect(
                new_notes,
                min_level=HotLevel.TRENDING
            )

            return {
                "success": True,
                "new_notes_count": len(new_notes),
                "hot_notes_count": len(hot_notes),
                "hot_notes": [
                    {
                        "note_id": n.get("note_id"),
                        "title": n.get("title"),
                        "hot_score": n.get("hot_analysis", {}).get("hot_score")
                    }
                    for n in hot_notes[:10]  # 只返回前10个
                ]
            }

        except Exception as e:
            utils.logger.error(f"[Scheduler] Trigger error: {e}")
            return {"success": False, "message": str(e)}


# 全局单例
monitor_scheduler = MonitorScheduler()
