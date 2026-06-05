# -*- coding: utf-8 -*-
"""一次完整调度周期：开始记录 → 计数前 → 跑爬虫 → 计数后 → 结束记录。"""

from typing import Optional

from insight import config, runner
from insight.db import InsightDB


def run_job(job: dict, db: Optional[InsightDB] = None) -> dict:
    db = db or InsightDB(config.DB_PATH)
    db.init_schema()

    run_id = db.start_run(job["name"], job["type"])
    notes_before = db.count_rows("xhs_note")
    comments_before = db.count_rows("xhs_note_comment")

    result = runner.run_crawl(job)

    notes_after = db.count_rows("xhs_note")
    comments_after = db.count_rows("xhs_note_comment")
    notes_delta = max(0, notes_after - notes_before)
    comments_delta = max(0, comments_after - comments_before)

    if result.timed_out:
        status = "timeout"
    elif result.exit_code == 0:
        status = "success"
    else:
        status = "error"

    db.finish_run(
        run_id,
        exit_code=result.exit_code,
        status=status,
        notes_crawled=notes_delta,
        comments_crawled=comments_delta,
        error_msg=None if status == "success" else (result.stderr_tail or status),
    )

    return {"run_id": run_id, "status": status, "notes": notes_delta, "comments": comments_delta}
