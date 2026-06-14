# -*- coding: utf-8 -*-
"""爬虫子进程入口。

读取 INSIGHT_MAX_NOTES 等无 CLI 参数的覆盖项写入上游 config，
然后把其余 CLI 参数交给上游 main 处理。本文件位于 insight 包内，
不修改任何上游文件。

用法（由 insight.runner 以子进程调用）：
    python -m insight.crawl_entry --platform xhs --type search --keywords ... --save_data_option sqlite
"""

import os


def apply_overrides() -> None:
    """把没有 CLI 参数的配置项从环境变量写入上游 config。"""
    import config  # 上游配置模块

    max_notes = os.environ.get("INSIGHT_MAX_NOTES")
    if max_notes:
        config.CRAWLER_MAX_NOTES_COUNT = int(max_notes)


def main_entry() -> None:
    apply_overrides()
    # 复用上游的协程入口与清理逻辑（sys.argv 由上游 cmd_arg 解析）
    from main import main as crawler_main, async_cleanup
    from tools.app_runner import run

    run(crawler_main, async_cleanup, cleanup_timeout_seconds=15.0)


if __name__ == "__main__":
    main_entry()
