# -*- coding: utf-8 -*-
"""一次完整调度周期：开始记录 → 计数前 → 跑爬虫 → 计数后 → 结束记录。

finish_run 放在 try/finally 里，保证 KeyboardInterrupt / SIGTERM 等外部信号
也会让 db 记录进入终态（之前卡在 'running' 不会自动收尾）。
"""

from typing import Optional

from insight import config, runner
from insight.db import InsightDB


def run_job(job: dict, db: Optional[InsightDB] = None) -> dict:
    db = db or InsightDB(config.DB_PATH)
    db.init_schema()

    run_id = db.start_run(job["name"], job["type"])
    notes_before = db.count_rows("xhs_note")
    comments_before = db.count_rows("xhs_note_comment")

    status = "interrupted"
    exit_code: Optional[int] = None
    notes_delta = 0
    comments_delta = 0
    error_msg: Optional[str] = "interrupted before crawl finished"

    try:
        result = runner.run_crawl(job)

        notes_after = db.count_rows("xhs_note")
        comments_after = db.count_rows("xhs_note_comment")
        notes_delta = max(0, notes_after - notes_before)
        comments_delta = max(0, comments_after - comments_before)
        exit_code = result.exit_code

        if result.timed_out:
            status = "timeout"
            error_msg = "subprocess timed out"
        elif result.exit_code == 0:
            status = "success"
            error_msg = None
        else:
            status = "error"
            error_msg = result.stderr_tail or status

        return {
            "run_id": run_id,
            "status": status,
            "notes": notes_delta,
            "comments": comments_delta,
        }
    finally:
        # 无论 try 块是否抛异常、是否被信号中断，都把状态写入 db
        try:
            db.finish_run(
                run_id,
                exit_code=exit_code,
                status=status,
                notes_crawled=notes_delta,
                comments_crawled=comments_delta,
                error_msg=error_msg,
            )
        except Exception:
            # finish_run 自身失败也不能让上层再抛
            pass
