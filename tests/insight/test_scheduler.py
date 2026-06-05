# -*- coding: utf-8 -*-
from apscheduler.schedulers.blocking import BlockingScheduler

from insight.scheduler.daemon import build_scheduler


def test_build_scheduler_registers_one_job_per_config():
    jobs = [
        {"name": "kw_daily", "type": "search", "keywords": "x", "hour": 2, "minute": 0},
        {"name": "watch", "type": "detail", "note_ids": ["n1"], "hour": 3, "minute": 30},
    ]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    ids = {j.id for j in sched.get_jobs()}
    assert ids == {"kw_daily", "watch"}


def test_build_scheduler_sets_cron_hour_and_minute():
    jobs = [{"name": "watch", "type": "detail", "note_ids": ["n1"], "hour": 3, "minute": 30}]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    job = sched.get_job("watch")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "3"
    assert fields["minute"] == "30"


def test_build_scheduler_defaults_minute_to_zero():
    jobs = [{"name": "kw", "type": "search", "keywords": "x", "hour": 5}]
    sched = build_scheduler(jobs=jobs, scheduler=BlockingScheduler())
    job = sched.get_job("kw")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["minute"] == "0"
