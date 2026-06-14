# -*- coding: utf-8 -*-
"""APScheduler 守护进程：按 cron 触发每个 job。"""

from typing import List, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from insight import config
from insight.orchestrator import run_job


def build_scheduler(jobs: Optional[List[dict]] = None, scheduler: Optional[BlockingScheduler] = None) -> BlockingScheduler:
    jobs = jobs if jobs is not None else config.JOBS
    scheduler = scheduler if scheduler is not None else BlockingScheduler()
    for job in jobs:
        trigger = CronTrigger(hour=job["hour"], minute=job.get("minute", 0))
        scheduler.add_job(
            run_job,
            trigger=trigger,
            args=[job],
            id=job["name"],
            misfire_grace_time=config.MISFIRE_GRACE_TIME,
            replace_existing=True,
        )
    return scheduler


def main() -> None:
    scheduler = build_scheduler()
    print(f"[insight] scheduler started with {len(scheduler.get_jobs())} job(s). Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[insight] scheduler stopped.")


if __name__ == "__main__":
    main()
