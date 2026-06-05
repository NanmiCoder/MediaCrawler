# -*- coding: utf-8 -*-
"""insight 命令行入口：crawl-once / run-daemon / status。"""

import argparse
from typing import Optional, Sequence

from insight import config
from insight.db import InsightDB
from insight.orchestrator import run_job


def _find_job(name: str) -> dict:
    for job in config.JOBS:
        if job["name"] == name:
            return job
    raise SystemExit(f"job not found: {name!r}. Known jobs: {[j['name'] for j in config.JOBS]}")


def cmd_crawl_once(args: argparse.Namespace) -> None:
    job = _find_job(args.name)
    result = run_job(job)
    print(result)


def cmd_run_daemon(args: argparse.Namespace) -> None:
    # 惰性导入：只有 run-daemon 需要 apscheduler
    from insight.scheduler.daemon import main as run_daemon
    run_daemon()


def cmd_status(args: argparse.Namespace) -> None:
    db = InsightDB(config.DB_PATH)
    db.init_schema()
    runs = db.recent_runs(args.limit)
    if not runs:
        print("(no runs yet)")
        return
    for run in runs:
        print(
            f"#{run['id']} {run['job_name']} [{run['crawler_type']}] "
            f"status={run['status']} exit={run['exit_code']} "
            f"notes={run['notes_crawled']} comments={run['comments_crawled']}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="insight")
    sub = parser.add_subparsers(dest="command", required=True)

    p_once = sub.add_parser("crawl-once", help="立即运行某个 job")
    p_once.add_argument("name", help="config.JOBS 中的 job 名")
    p_once.set_defaults(func=cmd_crawl_once)

    p_daemon = sub.add_parser("run-daemon", help="启动定时守护进程")
    p_daemon.set_defaults(func=cmd_run_daemon)

    p_status = sub.add_parser("status", help="查看最近的运行记录")
    p_status.add_argument("--limit", type=int, default=20)
    p_status.set_defaults(func=cmd_status)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
