# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/crawler_manager.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import subprocess
import signal
import os
import json
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from ..schemas import CrawlerStartRequest, LogEntry
from . import run_history


class CrawlerManager:
    """Crawler process manager"""

    def __init__(self):
        self._lock = asyncio.Lock()
        self.process: Optional[subprocess.Popen] = None
        self.status = "idle"
        self.started_at: Optional[datetime] = None
        self.current_config: Optional[CrawlerStartRequest] = None
        self._log_id = 0
        self._logs: List[LogEntry] = []
        self._read_task: Optional[asyncio.Task] = None
        # Project root directory
        self._project_root = Path(__file__).parent.parent.parent
        # Log queue - for pushing to WebSocket
        self._log_queue: Optional[asyncio.Queue] = None
        # 当前运行记录 id（start 时生成，_read_output finalize 时用）
        self._current_run_id: Optional[str] = None
        # stop() 主动停止标记，用于区分 failed 与 stopped
        self._stop_requested = False
        # 孤儿恢复：把上次 API 崩溃前残留的 running 记录标记为 failed
        try:
            recovered = run_history.recover_orphan_runs()
            if recovered:
                print(f"[CrawlerManager] Recovered {recovered} orphaned run(s) marked as failed")
        except Exception as e:
            print(f"[CrawlerManager] Run history orphan recovery failed: {e}")

    @property
    def logs(self) -> List[LogEntry]:
        return self._logs

    def get_log_queue(self) -> asyncio.Queue:
        """Get or create log queue"""
        if self._log_queue is None:
            self._log_queue = asyncio.Queue()
        return self._log_queue

    def _create_log_entry(self, message: str, level: str = "info") -> LogEntry:
        """Create log entry"""
        self._log_id += 1
        entry = LogEntry(
            id=self._log_id,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            level=level,
            message=message
        )
        self._logs.append(entry)
        # Keep last 500 logs
        if len(self._logs) > 500:
            self._logs = self._logs[-500:]
        return entry

    async def _push_log(self, entry: LogEntry):
        """Push log to queue"""
        if self._log_queue is not None:
            try:
                self._log_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _parse_log_level(self, line: str) -> str:
        """Parse log level"""
        line_upper = line.upper()
        if "ERROR" in line_upper or "FAILED" in line_upper:
            return "error"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            return "warning"
        elif "SUCCESS" in line_upper or "完成" in line or "成功" in line:
            return "success"
        elif "DEBUG" in line_upper:
            return "debug"
        return "info"

    async def start(self, config: CrawlerStartRequest) -> bool:
        """Start crawler process"""
        async with self._lock:
            if self.process and self.process.poll() is None:
                return False

            # Clear old logs
            self._logs = []
            self._log_id = 0

            # Clear pending queue (don't replace object to avoid WebSocket broadcast coroutine holding old queue reference)
            if self._log_queue is None:
                self._log_queue = asyncio.Queue()
            else:
                try:
                    while True:
                        self._log_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            # 先生成 run_id 并存实例状态，供 _build_command 拼接 --run_id 注入子进程
            run_id = run_history.generate_run_id()
            self._current_run_id = run_id

            # Build command line arguments
            cmd = self._build_command(config)

            # Log start information
            entry = self._create_log_entry(f"Starting crawler: {' '.join(cmd)}", "info")
            await self._push_log(entry)

            try:
                # Start subprocess
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    bufsize=1,
                    cwd=str(self._project_root),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"}
                )

                self.status = "running"
                self.started_at = datetime.now()
                self.current_config = config
                self._stop_requested = False

                # 记录本次运行到历史清单
                keywords_field = ""
                if config.crawler_type.value == "search":
                    keywords_field = config.keywords
                elif config.crawler_type.value == "detail":
                    keywords_field = config.specified_ids
                elif config.crawler_type.value == "creator":
                    keywords_field = config.creator_ids
                try:
                    run_history.append_run({
                        "run_id": run_id,
                        "platform": config.platform.value,
                        "crawler_type": config.crawler_type.value,
                        "save_option": config.save_option.value,
                        "keywords": keywords_field,
                        "started_at": self.started_at.isoformat(),
                        "ended_at": None,
                        "status": "running",
                        "exit_code": None,
                        "record_count": None,
                        "error_message": None,
                    })
                except Exception as e:
                    print(f"[CrawlerManager] Failed to append run history: {e}")

                entry = self._create_log_entry(
                    f"Crawler started on platform: {config.platform.value}, type: {config.crawler_type.value}",
                    "success"
                )
                await self._push_log(entry)

                # Start log reading task
                self._read_task = asyncio.create_task(self._read_output())

                return True
            except Exception as e:
                self.status = "error"
                entry = self._create_log_entry(f"Failed to start crawler: {str(e)}", "error")
                await self._push_log(entry)
                return False

    async def stop(self) -> bool:
        """Stop crawler process"""
        async with self._lock:
            if not self.process or self.process.poll() is not None:
                return False

            self.status = "stopping"
            self._stop_requested = True
            entry = self._create_log_entry("Sending SIGTERM to crawler process...", "warning")
            await self._push_log(entry)

            try:
                self.process.send_signal(signal.SIGTERM)

                # Wait for graceful exit (up to 15 seconds)
                for _ in range(30):
                    if self.process.poll() is not None:
                        break
                    await asyncio.sleep(0.5)

                # If still not exited, force kill
                if self.process.poll() is None:
                    entry = self._create_log_entry("Process not responding, sending SIGKILL...", "warning")
                    await self._push_log(entry)
                    self.process.kill()

                entry = self._create_log_entry("Crawler process terminated", "info")
                await self._push_log(entry)

            except Exception as e:
                entry = self._create_log_entry(f"Error stopping crawler: {str(e)}", "error")
                await self._push_log(entry)

            self.status = "idle"
            self.current_config = None

            # Cancel log reading task
            if self._read_task:
                self._read_task.cancel()
                self._read_task = None

            return True

    def get_status(self) -> dict:
        """Get current status"""
        return {
            "status": self.status,
            "platform": self.current_config.platform.value if self.current_config else None,
            "crawler_type": self.current_config.crawler_type.value if self.current_config else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error_message": None,
            "run_id": self._current_run_id,
        }

    def _build_command(self, config: CrawlerStartRequest) -> list:
        """Build main.py command line arguments"""
        cmd = ["uv", "run", "python", "main.py"]

        cmd.extend(["--platform", config.platform.value])
        cmd.extend(["--lt", config.login_type.value])
        cmd.extend(["--type", config.crawler_type.value])
        cmd.extend(["--save_data_option", config.save_option.value])

        # Pass different arguments based on crawler type
        if config.crawler_type.value == "search" and config.keywords:
            cmd.extend(["--keywords", config.keywords])
        elif config.crawler_type.value == "detail" and config.specified_ids:
            cmd.extend(["--specified_id", config.specified_ids])
        elif config.crawler_type.value == "creator" and config.creator_ids:
            cmd.extend(["--creator_id", config.creator_ids])

        if config.start_page != 1:
            cmd.extend(["--start", str(config.start_page)])

        cmd.extend(["--get_comment", "true" if config.enable_comments else "false"])
        cmd.extend(["--get_sub_comment", "true" if config.enable_sub_comments else "false"])
        cmd.extend(["--enable_get_bgm", "true" if config.enable_bgm else "false"])

        if config.max_notes_count is not None:
            cmd.extend(["--crawler_max_notes_count", str(config.max_notes_count)])

        if config.max_comments_count is not None:
            cmd.extend(["--max_comments_count_singlenotes", str(config.max_comments_count)])

        if config.cookies:
            cmd.extend(["--cookies", config.cookies])

        cmd.extend(["--headless", "true" if config.headless else "false"])

        # 注入 run_id，供子进程把 run_id 写进数据行/文件名后缀（按 run 分组的前提）
        if self._current_run_id:
            cmd.extend(["--run_id", self._current_run_id])

        return cmd

    async def _read_output(self):
        """Asynchronously read process output"""
        loop = asyncio.get_event_loop()

        try:
            while self.process and self.process.poll() is None:
                # Read a line in thread pool
                line = await loop.run_in_executor(
                    None, self.process.stdout.readline
                )
                if line:
                    line = line.strip()
                    if line:
                        level = self._parse_log_level(line)
                        entry = self._create_log_entry(line, level)
                        await self._push_log(entry)

            # Read remaining output
            if self.process and self.process.stdout:
                remaining = await loop.run_in_executor(
                    None, self.process.stdout.read
                )
                if remaining:
                    for line in remaining.strip().split('\n'):
                        if line.strip():
                            level = self._parse_log_level(line)
                            entry = self._create_log_entry(line.strip(), level)
                            await self._push_log(entry)

            # Process ended
            if self.status == "running":
                exit_code = self.process.returncode if self.process else -1
                if exit_code == 0:
                    entry = self._create_log_entry("Crawler completed successfully", "success")
                else:
                    entry = self._create_log_entry(f"Crawler exited with code: {exit_code}", "warning")
                await self._push_log(entry)
                self.status = "idle"
                self._finalize_run(exit_code)

        except asyncio.CancelledError:
            # stop() 取消读任务时也要 finalize（标记为 stopped）
            if self._stop_requested and self._current_run_id:
                self._finalize_run(-1, stopped=True)
            pass
        except Exception as e:
            entry = self._create_log_entry(f"Error reading output: {str(e)}", "error")
            await self._push_log(entry)

    def _finalize_run(self, exit_code: int, stopped: bool = False) -> None:
        """运行结束时回写历史清单：ended_at / status / exit_code / record_count。"""
        if not self._current_run_id:
            return
        # 判定最终状态：主动停止→stopped，exit 0→success，否则 failed
        if stopped or self._stop_requested:
            final_status = "stopped"
        elif exit_code == 0:
            final_status = "success"
        else:
            final_status = "failed"
        patch = {
            "ended_at": datetime.now().isoformat(),
            "status": final_status,
            "exit_code": exit_code,
            "record_count": self._count_recent_records(),
        }
        try:
            run_history.update_run(self._current_run_id, patch)
        except Exception as e:
            print(f"[CrawlerManager] Failed to finalize run history: {e}")
        # 清理当前运行标记
        self._current_run_id = None
        self._stop_requested = False

    def _count_recent_records(self) -> int:
        """
        统计本次运行产生的记录数（近似）。

        扫描 data 目录下属于当前平台、且在 started_at 之后修改的数据文件，
        求和其记录数。由于文件是追加模式，同日多次运行会混在同一文件，此值为
        「运行结束时文件内累计记录数」，非本次增量。
        """
        if not self.started_at or not self.current_config:
            return 0
        data_dir = self._project_root / "data"
        if not data_dir.exists():
            return 0
        # 平台短名 → 存储目录名映射（存储层用长名）
        platform_map = {"dy": "douyin", "xhs": "xhs", "ks": "kuaishou",
                        "bili": "bilibili", "wb": "weibo", "tieba": "tieba", "zhihu": "zhihu"}
        platform_dir = platform_map.get(self.current_config.platform.value, "")
        if not platform_dir:
            return 0
        started_ts = self.started_at.timestamp()
        supported = {".json", ".jsonl", ".csv", ".xlsx", ".xls"}
        total = 0
        for root, _dirs, filenames in os.walk(data_dir):
            root_path = Path(root)
            # 仅统计当前平台目录下的文件
            try:
                rel = root_path.relative_to(data_dir)
            except ValueError:
                continue
            if platform_dir not in str(rel).lower():
                continue
            for filename in filenames:
                file_path = root_path / filename
                if file_path.suffix.lower() not in supported:
                    continue
                try:
                    stat = file_path.stat()
                    if stat.st_mtime < started_ts:
                        continue  # 运行开始前就存在的文件，跳过
                    total += self._count_records_in_file(file_path)
                except Exception:
                    continue
        return total

    @staticmethod
    def _count_records_in_file(file_path: Path) -> int:
        """统计单个数据文件的记录数（json 数组长度 / jsonl 非空行 / csv 行数-1）。"""
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data) if isinstance(data, list) else 0
            elif suffix == ".jsonl":
                with open(file_path, "r", encoding="utf-8") as f:
                    return sum(1 for line in f if line.strip())
            elif suffix == ".csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    return max(0, sum(1 for _ in f) - 1)
        except Exception:
            return 0
        return 0


# Global singleton
crawler_manager = CrawlerManager()
