"""
douyin_scraper.core — 核心采集引擎
===================================
v5 核心：DouyinScraper 类，统一入口，状态内部管理。

对外 API：
  - DouyinScraper(config) → 初始化
  - .setup() → 环境准备
  - .search() → 搜索采集
  - .fetch_comments() → 评论采集
  - .extract_scripts() → 文案提取
  - .merge() → 合并数据
  - .run_all() → 一键执行
  - .get_status() → 状态查询
  - .reset_step() → 重置步骤

v4 → v5 关键变更：
  - 全局变量 → 实例属性
  - print → logging
  - 独立脚本 → 类方法
  - 手动管理路径 → self._paths 自动管理
  - 无配置验证 → ScraperConfig.validate()
"""

import csv
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Union

from douyin_scraper.config import ScraperConfig
from douyin_scraper.exceptions import (
    ConfigError,
    FatalError,
    NonRetryableError,
    RetryableError,
    ScraperError,
)
from douyin_scraper.models import Comment, Script, Video
from douyin_scraper.state import StateManager
from douyin_scraper.utils import (
    EXIT_FATAL,
    EXIT_NON_RETRYABLE,
    EXIT_RETRYABLE,
    append_record,
    check_disk_space_enforced,
    check_port_in_use,
    classify_error,
    ensure_dir_writable,
    kill_process_on_port,
    parse_count,
    retry,
    retry_with_degradation,
    safe_write_line,
    setup_env_vars,
    setup_ffmpeg,
    setup_log_rotation,
)

logger = logging.getLogger("douyin_scraper")


class DouyinScraper:
    """
    抖音关键词批量采集工具 — 主入口类。

    用法:
        scraper = DouyinScraper({"project_dir": "G:/MediaCrawler"})
        scraper.setup()
        scraper.search(keywords=["短视频运营"])
        scraper.fetch_comments()
        scraper.extract_scripts()
        scraper.merge()

    或者一键运行:
        scraper = DouyinScraper()
        result = scraper.run_all()
    """

    # 步骤名称常量
    STEP_CLONE = "clone_repo"
    STEP_SETUP_ENV = "setup_env"
    STEP_CONFIG = "config_douyin"
    STEP_SEARCH = "run_search"
    STEP_COMMENTS = "fetch_comments"
    STEP_FFMPEG = "install_ffmpeg"
    STEP_WHISPER = "install_whisper"
    STEP_EXTRACT = "run_extract"
    STEP_MERGE = "merge_csv"

    ALL_STEPS = [
        STEP_CLONE,
        STEP_SETUP_ENV,
        STEP_CONFIG,
        STEP_SEARCH,
        STEP_COMMENTS,
        STEP_FFMPEG,
        STEP_WHISPER,
        STEP_EXTRACT,
        STEP_MERGE,
    ]

    def __init__(
        self,
        config: Optional[Union[str, Path, dict]] = None,
    ) -> None:
        # 加载配置
        self._config = ScraperConfig(config)
        # 不在这里 validate，因为 keywords 等参数是后续通过 search() 传入的
        # validate 将在 search() 方法中调用

        # 初始化状态管理
        self._state = StateManager(self._config.state_dir)

        # 确保关键目录存在
        self._config.project_dir.mkdir(parents=True, exist_ok=True)

        # 内部路径管理（★ 替代 v4 的 handoff.md ★）
        self._paths: Dict[str, Path] = {}

        # 可中断等待事件（★ 替代 time.sleep 实现可取消等待 ★）
        self._cancel_event = threading.Event()

        # 日志轮转（★ v5: 自动调用 ★）
        log_path = self._config.state_dir / "execution_log.jsonl"
        setup_log_rotation(log_path)

        # 配置 logging 输出到控制台
        if not any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            for h in logger.handlers
        ):
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            console.setLevel(getattr(logging, self._config.log_level, logging.INFO))
            logger.addHandler(console)

        logger.info("DouyinScraper 初始化完成, project_dir=%s", self._config.project_dir)

    def __del__(self) -> None:
        """析构时确保去重索引已刷盘"""
        try:
            if hasattr(self, '_state') and self._state is not None:
                self._state.flush_dedupe()
        except Exception:
            pass

    def cancel(self) -> None:
        """取消正在执行的操作，中断等待中的 sleep。"""
        self._cancel_event.set()
        logger.info("收到取消请求，正在中断等待…")

    @property
    def is_cancelled(self) -> bool:
        """是否已被取消"""
        return self._cancel_event.is_set()

    @property
    def config(self) -> ScraperConfig:
        return self._config

    @property
    def state(self) -> StateManager:
        return self._state

    # ═══════════════════════════════════════════════════════════════
    # 公共 API
    # ═══════════════════════════════════════════════════════════════

    def setup(self) -> bool:
        """
        环境准备：克隆仓库、安装依赖、检查 Chrome CDP。
        幂等：重复调用不会重复操作。
        failed 状态的步骤会重新尝试（修复逻辑反转：原来 failed 被跳过）。
        """
        steps = [self.STEP_CLONE, self.STEP_SETUP_ENV, self.STEP_CONFIG]
        for step_name in steps:
            status = self._state.get_step_status(step_name)
            # completed → 跳过; in_progress → 重试; failed → 重试; pending → 执行
            if status == "completed":
                logger.info("[%s] 步骤已完成，跳过", step_name)
                continue
            self._state.mark_step_started(step_name)
            try:
                if step_name == self.STEP_CLONE:
                    self._do_clone()
                elif step_name == self.STEP_SETUP_ENV:
                    self._do_setup_env()
                elif step_name == self.STEP_CONFIG:
                    self._do_config()
                self._state.mark_step_completed(step_name)
            except ScraperError as e:
                self._state.mark_step_failed(
                    step_name, error_summary=str(e), exit_code=e.exit_code
                )
                return False
            except Exception as e:
                exit_code = classify_error(e)
                self._state.mark_step_failed(
                    step_name, error_summary=str(e)[:200], exit_code=exit_code
                )
                return False
        return True

    def search(
        self,
        keywords: Optional[List[str]] = None,
        max_count: Optional[int] = None,
    ) -> Path:
        """
        执行搜索采集，返回视频元数据 JSONL 路径。

        Args:
            keywords: 搜索关键词列表（默认使用配置中的 keywords）
            max_count: 每个关键词最大采集数（默认使用配置值）
        """
        step = self.STEP_SEARCH
        self._require_step_ready(step)

        if keywords:
            self._config.keywords = keywords
        if max_count:
            self._config.max_videos_per_keyword = max_count

        # ★ Fix 1: validate 在 keywords/max_count 设置之后再校验 ★
        self._config.validate()

        logger.info("DouyinScraper.search keywords=%r max_count=%s",
                    self._config.keywords, self._config.max_videos_per_keyword)

        self._state.mark_step_started(step)
        try:
            output_path = self._do_search()
            result_jsonl_path, result_csv_path = self._prepare_standard_search_outputs(
                output_path
            )

            title_clean_csv = self._prepare_title_clean_outputs(
                result_csv_path, result_jsonl_path
            )

            self._prepare_script_source_outputs(
                result_csv_path, result_jsonl_path, title_clean_csv
            )

            self._state.mark_step_completed(
                step, detail=f"output={output_path}"
            )
            return output_path
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise

    def _prepare_standard_search_outputs(self, output_path: Path) -> tuple[Path, Path]:
        """Create and register the standard search_result JSONL/CSV outputs."""
        outputs_dir = self._current_task_workspace_dir() / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        result_jsonl_path = outputs_dir / "search_result.jsonl"
        result_csv_path = outputs_dir / "search_result.csv"

        if Path(output_path).resolve() != result_jsonl_path.resolve():
            shutil.copy2(output_path, result_jsonl_path)

        source_keyword = (
            self._config.keywords[0] if self._config.keywords else "unknown"
        )
        csv_stats = self._convert_jsonl_to_standard_csv(
            jsonl_path=str(result_jsonl_path),
            csv_path=str(result_csv_path),
            source_keyword=source_keyword,
        )
        logger.info("CSV conversion stats: %s", csv_stats)

        self._paths["video_jsonl"] = result_jsonl_path
        self._paths["video_csv"] = result_csv_path
        self._paths["csv_stats"] = csv_stats
        return result_jsonl_path, result_csv_path


    def _prepare_title_clean_outputs(
        self,
        result_csv_path: Path,
        result_jsonl_path: Path,
    ) -> Path:
        """Create and register search_title_clean outputs."""
        clean_jsonl, clean_csv, stats = self._do_clean_search_titles(
            result_csv_path, result_jsonl_path
        )
        self._paths["title_clean_jsonl"] = clean_jsonl
        self._paths["title_clean_csv"] = clean_csv
        self._paths["title_clean_stats"] = stats
        return clean_csv


    def _prepare_script_source_outputs(
        self,
        result_csv_path: Path,
        result_jsonl_path: Path,
        title_clean_csv: Optional[Path],
    ) -> None:
        """Create and register script_sources outputs."""
        sources_jsonl, sources_csv, stats = self._do_build_script_sources(
            result_csv_path, result_jsonl_path, title_clean_csv
        )
        self._paths["script_sources_jsonl"] = sources_jsonl
        self._paths["script_sources_csv"] = sources_csv
        self._paths["script_sources_stats"] = stats


    def fetch_comments(
        self,
        video_jsonl: Optional[Path] = None,
        video_ids: Optional[List[str]] = None,
        source_task_id: Optional[str] = None,
        max_comments_per_video: int = 200,
    ) -> Path:
        """
        对已有视频采集评论，返回评论 JSONL 路径。
        """
        step = self.STEP_COMMENTS
        self._require_step_ready(step)

        input_path = video_jsonl or self._paths.get("video_jsonl")
        if input_path and not input_path.exists():
            raise NonRetryableError(
                f"视频 JSONL 不存在: {input_path}",
                step=step,
            )
        if not input_path and not video_ids:
            raise NonRetryableError(
                "评论采集缺少输入：请提供 task_id/search_result 文件或 video_ids",
                step=step,
            )

        self._state.mark_step_started(step)
        try:
            output_path = self._do_fetch_comments(
                input_path=input_path,
                video_ids=video_ids,
                source_task_id=source_task_id,
                max_comments_per_video=max_comments_per_video,
            )
            clean_jsonl_path, clean_csv_path, clean_stats = self._do_clean_comments(output_path)
            self._state.mark_step_completed(
                step, detail=f"output={output_path}"
            )
            self._register_comments_outputs(
                output_path,
                clean_jsonl_path,
                clean_csv_path,
                clean_stats,
            )
            return output_path
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise

    def _register_comments_outputs(
        self,
        raw_jsonl: Path,
        clean_jsonl: Path,
        clean_csv: Path,
        clean_stats: Dict[str, Any],
    ) -> None:
        """Register comments_raw/comments_clean outputs for get_paths()."""
        self._paths["comments_jsonl"] = raw_jsonl
        self._paths["comments_raw_jsonl"] = raw_jsonl
        self._paths["comments_clean_jsonl"] = clean_jsonl
        self._paths["comments_clean_csv"] = clean_csv
        self._paths["clean_stats"] = clean_stats


    def extract_scripts(
        self,
        video_jsonl: Optional[Path] = None,
        model: str = "small",
    ) -> Path:
        """
        提取文案，返回带文案的 JSONL 路径。
        """
        step = self.STEP_EXTRACT
        self._require_step_ready(step)

        input_path = video_jsonl or self._paths.get("video_jsonl")
        if not input_path or not input_path.exists():
            raise NonRetryableError(
                f"视频 JSONL 不存在: {input_path}",
                step=step,
            )

        # 前置依赖检查
        setup_env_vars()
        if not setup_ffmpeg():
            raise NonRetryableError("ffmpeg 不可用", step=step)

        self._state.mark_step_started(step)
        try:
            output_path = self._do_extract_scripts(input_path, model)
            self._state.mark_step_completed(
                step, detail=f"output={output_path}"
            )
            self._paths["scripts_jsonl"] = output_path
            return output_path
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise

    def extract_script_raw(
        self,
        script_sources_jsonl: Optional[Path] = None,
        script_sources_csv: Optional[Path] = None,
        model: str = "small",
        max_items: Optional[int] = None,
        title_clean_csv: Optional[Path] = None,
    ) -> Path:
        """Build script_raw outputs from standardized script_sources."""
        step = self.STEP_EXTRACT
        self._require_step_ready(step)

        output_dir = self._current_task_workspace_dir() / "outputs"
        if script_sources_jsonl is None:
            candidate = output_dir / "script_sources.jsonl"
            if candidate.exists():
                script_sources_jsonl = candidate
        if script_sources_csv is None:
            candidate = output_dir / "script_sources.csv"
            if candidate.exists():
                script_sources_csv = candidate
        if title_clean_csv is None:
            for source_path in (script_sources_jsonl, script_sources_csv):
                if source_path is None:
                    continue
                candidate = source_path.parent / "search_title_clean.csv"
                if candidate.exists():
                    title_clean_csv = candidate
                    break
        if title_clean_csv is None:
            candidate = output_dir / "search_title_clean.csv"
            if candidate.exists():
                title_clean_csv = candidate

        if not script_sources_jsonl and not script_sources_csv:
            raise NonRetryableError(
                "script_sources.jsonl/csv 不存在，无法生成 script_raw",
                step=step,
            )

        setup_env_vars()
        self._state.mark_step_started(step)
        try:
            raw_jsonl, raw_csv, stats = self._do_build_script_raw(
                script_sources_jsonl=script_sources_jsonl,
                script_sources_csv=script_sources_csv,
                model_name=model,
                max_items=max_items,
            )
            clean_jsonl, clean_csv, clean_stats = self._do_build_script_clean(
                script_sources_jsonl=script_sources_jsonl,
                script_sources_csv=script_sources_csv,
                script_raw_jsonl=raw_jsonl,
                script_raw_csv=raw_csv,
                title_clean_csv=title_clean_csv,
            )
            self._state.mark_step_completed(step, detail=f"output={raw_jsonl}")
            self._register_script_outputs(
                raw_jsonl,
                raw_csv,
                stats,
                clean_jsonl,
                clean_csv,
                clean_stats,
            )
            return raw_jsonl
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise


    def _register_script_outputs(
        self,
        raw_jsonl: Path,
        raw_csv: Path,
        raw_stats: Dict[str, Any],
        clean_jsonl: Path,
        clean_csv: Path,
        clean_stats: Dict[str, Any],
    ) -> None:
        """Register script_raw/script_clean outputs for get_paths()."""
        self._paths["script_raw_jsonl"] = raw_jsonl
        self._paths["script_raw_csv"] = raw_csv
        self._paths["script_raw_stats"] = raw_stats
        self._paths["script_clean_jsonl"] = clean_jsonl
        self._paths["script_clean_csv"] = clean_csv
        self._paths["script_clean_stats"] = clean_stats


    def merge(
        self,
        video_jsonl: Optional[Path] = None,
        comments_jsonl: Optional[Path] = None,
        scripts_jsonl: Optional[Path] = None,
        output_csv: Optional[Path] = None,
    ) -> Path:
        """
        合并数据生成 CSV，返回 CSV 路径。
        """
        step = self.STEP_MERGE
        self._require_step_ready(step)

        v_path = video_jsonl or self._paths.get("video_jsonl")
        c_path = comments_jsonl or self._paths.get("comments_jsonl")
        s_path = scripts_jsonl or self._paths.get("scripts_jsonl")

        self._state.mark_step_started(step)
        try:
            csv_path = self._do_merge(v_path, c_path, s_path, output_csv)
            self._state.mark_step_completed(
                step, detail=f"output={csv_path}"
            )
            return csv_path
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise

    def run_all(
        self,
        steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        按顺序执行全部或指定步骤，返回结果摘要。
        """
        target_steps = steps or self.ALL_STEPS
        results: Dict[str, Any] = {}

        for step_name in target_steps:
            try:
                if step_name == self.STEP_CLONE:
                    ok = self.setup()  # setup 包含前3步
                elif step_name == self.STEP_SEARCH:
                    path = self.search()
                    results["video_jsonl"] = str(path)
                elif step_name == self.STEP_COMMENTS:
                    path = self.fetch_comments()
                    results["comments_jsonl"] = str(path)
                elif step_name == self.STEP_EXTRACT:
                    path = self.extract_scripts()
                    results["scripts_jsonl"] = str(path)
                elif step_name == self.STEP_MERGE:
                    path = self.merge()
                    results["csv_path"] = str(path)
                elif step_name == self.STEP_FFMPEG:
                    setup_ffmpeg()
                elif step_name == self.STEP_WHISPER:
                    self._do_install_whisper()
                elif step_name == self.STEP_CONFIG:
                    pass  # 已在 setup 中处理
                elif step_name == self.STEP_SETUP_ENV:
                    pass  # 已在 setup 中处理
            except ScraperError as e:
                results["error"] = str(e)
                results["error_step"] = step_name
                results["exit_code"] = e.exit_code
                break
            except Exception as e:
                results["error"] = str(e)
                results["error_step"] = step_name
                results["exit_code"] = classify_error(e)
                break

        results["status"] = self._state.get_all_status()
        return results

    def get_status(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        return self._state.get_all_status()

    def reset_step(self, step: str, clear_dedupe: bool = False) -> None:
        """重置某步骤状态"""
        self._state.reset_step(step, clear_dedupe=clear_dedupe)

    # ═══════════════════════════════════════════════════════════════
    # 内部实现
    # ═══════════════════════════════════════════════════════════════

    def get_paths(self) -> Dict[str, Any]:
        """Return output paths grouped by release feature."""
        result: Dict[str, Any] = {}
        result.update(self._search_output_paths())
        result.update(self._comments_output_paths())
        result.update(self._title_output_paths())
        result.update(self._script_output_paths())
        return result


    def _select_output_values(
        self,
        path_keys: Sequence[str] = (),
        stats_keys: Sequence[str] = (),
    ) -> Dict[str, Any]:
        selected: Dict[str, Any] = {}
        for key in path_keys:
            value = self._paths.get(key)
            if value is not None:
                selected[key] = str(value)
        for key in stats_keys:
            if key in self._paths:
                selected[key] = self._paths[key]
        return selected


    def _search_output_paths(self) -> Dict[str, Any]:
        return self._select_output_values(
            path_keys=("video_jsonl", "video_csv"),
            stats_keys=("csv_stats",),
        )


    def _comments_output_paths(self) -> Dict[str, Any]:
        return self._select_output_values(
            path_keys=(
                "comments_jsonl",
                "comments_raw_jsonl",
                "comments_raw_csv",
                "comments_clean_jsonl",
                "comments_clean_csv",
            ),
            stats_keys=("comments_stats", "clean_stats"),
        )


    def _title_output_paths(self) -> Dict[str, Any]:
        return self._select_output_values(
            path_keys=("title_clean_jsonl", "title_clean_csv"),
            stats_keys=("title_clean_stats",),
        )


    def _script_output_paths(self) -> Dict[str, Any]:
        return self._select_output_values(
            path_keys=(
                "script_sources_jsonl",
                "script_sources_csv",
                "script_raw_jsonl",
                "script_raw_csv",
                "script_clean_jsonl",
                "script_clean_csv",
                "scripts_jsonl",
            ),
            stats_keys=(
                "script_sources_stats",
                "script_raw_stats",
                "script_clean_stats",
            ),
        )


    def _require_step_ready(self, step: str) -> None:
        """检查步骤是否可执行，否则抛异常"""
        if not self._state.check_step_ready(step):
            status = self._state.get_step_status(step)
            if status == "completed":
                raise NonRetryableError(
                    f"步骤 {step} 已完成，跳过（使用 reset_step 重跑）",
                    step=step,
                )
            if status == "failed":
                info = self._state.get_step_info(step)
                logger.warning(
                    "[%s] 上次失败 (%s)，自动重置后重试",
                    step, info.get("error_summary", "未知"),
                )
                self._state.reset_step(step, clear_dedupe=False)

    def _do_clone(self) -> None:
        """克隆 MediaCrawler 仓库"""
        project_dir = self._config.project_dir
        if (project_dir / ".git").exists():
            logger.info("仓库已存在: %s", project_dir)
            return
        # 如果目录存在但没有 .git，备份
        if project_dir.exists() and not (project_dir / ".git").exists():
            backup = project_dir.parent / f"MediaCrawler_backup_{int(time.time())}"
            logger.warning("发现残留目录，备份到: %s", backup)
            shutil.move(str(project_dir), str(backup))

        subprocess.run(
            ["git", "clone", "https://github.com/NanmiCoder/MediaCrawler.git",
             str(project_dir)],
            check=True, timeout=300,
        )

    def _do_setup_env(self) -> None:
        """安装依赖"""
        project_dir = self._config.project_dir
        venv_python = self._get_venv_python()

        if venv_python.exists():
            result = subprocess.run(
                [str(venv_python), "-c", "import httpx; print('OK')"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                logger.info("依赖已安装")
                return

        # 尝试 uv sync
        try:
            subprocess.run(
                ["uv", "sync"], cwd=str(project_dir),
                check=True, timeout=300,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("uv sync 失败，尝试 pip fallback")
            if not venv_python.exists():
                subprocess.run(
                    [sys.executable, "-m", "venv", str(project_dir / ".venv")],
                    check=True,
                )
            subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r",
                 str(project_dir / "requirements.txt")],
                check=False,
            )

        setup_env_vars()

    def _do_config(self) -> None:
        """配置抖音搜索参数"""
        config_path = self._config.project_dir / "config" / "base_config.py"
        if not config_path.exists():
            raise NonRetryableError(
                f"配置文件不存在: {config_path}",
                step=self.STEP_CONFIG,
            )
        logger.info("配置文件: %s (请手动确认)", config_path)

    def _do_search(self) -> Path:
        """执行搜索采集"""
        venv_python = self._get_venv_python()
        project_dir = self._config.project_dir

        # ★ Fix 3: 计算 task output_dir — 在 state_dir 的父目录下创建 outputs/ ★
        state_parent = self._config.project_dir / Path(self._config.state_dir_name).parent
        output_dir = state_parent / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        jsonl_dir = project_dir / "data" / "douyin" / "jsonl"

        # ★ 子进程同一天写入同一个文件（search_contents_YYYY-MM-DD.jsonl 追加模式）。
        # 为防止新旧任务数据混在一起，先记下当前文件行数，跑完只取增量。
        global_output = None
        existing_count = 0
        for f in jsonl_dir.glob("search_contents_*.jsonl"):
            if "_with_scripts" in f.name or "_comments" in f.name:
                continue
            global_output = f
            with open(f, "r", encoding="utf-8") as fh:
                existing_count = sum(1 for _ in fh)
            break  # 只处理最新文件
        if existing_count:
            logger.info("搜索前全局文件已有 %d 条数据（将被过滤，只取本次增量）", existing_count)

        # 检查 CDP 端口 — Docker 中可能没有预先启动的 Chrome
        cdp_ready = check_port_in_use(self._config.chrome_debugging_port)
        if not cdp_ready:
            if self._config.enable_cdp_mode:
                raise RetryableError(
                    f"Chrome CDP 端口 {self._config.chrome_debugging_port} 未就绪，"
                    "请先启动 Chrome: chrome.exe --remote-debugging-port=9222",
                    step=self.STEP_SEARCH,
                )
            else:
                logger.info("CDP 模式已禁用，使用 headless 浏览器")

        # 构建命令行参数
        keywords_str = ",".join(self._config.keywords)
        # Cookie 优先级：1) 持久化文件 2) 环境变量 3) qrcode（Docker 中会失败）
        cookie_file = Path("/app/data/douyin_cookie.txt")
        douyin_cookie = ""
        if cookie_file.exists():
            try:
                _file_cookie = cookie_file.read_text(encoding="utf-8").strip()
                if _file_cookie:
                    douyin_cookie = _file_cookie
                    logger.info("使用持久化 Cookie 文件登录，Cookie 长度: %d", len(douyin_cookie))
            except OSError as _e:
                logger.warning("读取 Cookie 文件失败: %s", _e)
        if not douyin_cookie and os.environ.get("DOUYIN_COOKIE"):
            douyin_cookie = os.environ.get("DOUYIN_COOKIE", "")
            logger.info("使用环境变量 DOUYIN_COOKIE 登录，Cookie 长度: %d", len(douyin_cookie))

        if douyin_cookie:
            login_type = "cookie"
            logger.info("Cookie 登录模式，Cookie 长度: %d", len(douyin_cookie))
        else:
            login_type = "qrcode"
            logger.warning(
                "未找到 Cookie，将使用 qrcode 登录"
                "（Docker headless 模式中可能失败，请先通过 POST /login/qrcode/start 扫码登录）"
            )
        cmd = [
            str(venv_python), str(project_dir / "main.py"),
            "--platform", "dy",
            "--lt", login_type,
            "--type", "search",
            "--keywords", keywords_str,
            "--crawler_max_notes_count", str(self._config.max_videos_per_keyword),
            "--save_data_option", "jsonl",
            "--headless", "true",
            "--get_comment", "false",
            "--output_dir", str(output_dir),
        ]
        if douyin_cookie:
            cmd.extend(["--cookies", douyin_cookie])
        logger.info("运行搜索子进程: %s (cwd=%s)", " ".join(cmd), project_dir)

        # ★ Fix 7: 构建子进程环境变量，禁用登录状态持久化以避免任务间互相干扰 ★
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"
        env["MEDIACRAWLER_SAVE_LOGIN_STATE"] = "false"

        logger.info("subprocess cmd keywords=%r", keywords_str)

        # 运行 MediaCrawler
        subprocess.run(
            cmd,
            cwd=str(project_dir), check=True, timeout=1800,
            env=env,
        )

        # ★ Fix 4: 优先直接使用 output_dir 下的稳定文件名 ★
        target = output_dir / "search_result.jsonl"
        if target.exists() and target.stat().st_size > 0:
            logger.info("搜索子进程完成，输出: %s (size=%d)", target, target.stat().st_size)
            return target

        # 兼容：搜索 output_dir 下任意 jsonl
        output_jsonls = list(output_dir.rglob("*.jsonl"))
        if output_jsonls:
            latest = sorted(output_jsonls, key=lambda p: p.stat().st_mtime)[-1]
            if latest != target:
                shutil.copy2(str(latest), str(target))
            logger.info("搜索子进程完成，输出: %s (来自 %s)", target, latest)
            return target

        # Fallback：全局目录（极不安全，仅当 output_dir 完全未生效时）
        logger.warning("WARNING: fallback to global data/douyin/jsonl latest file, this is unsafe for concurrent tasks")
        if jsonl_dir.exists():
            files = [
                f for f in jsonl_dir.glob("search_contents_*.jsonl")
                if "_with_scripts" not in f.name and "_comments" not in f.name
            ]
            if files:
                latest = sorted(files)[-1]
                # 从全局文件中提取增量数据，写入任务专属 workspace
                new_lines = self._extract_new_lines(latest, existing_count)
                state_parent.mkdir(parents=True, exist_ok=True)
                task_output = state_parent / "search_result.jsonl"
                with open(task_output, "w", encoding="utf-8") as outf:
                    for line in new_lines:
                        outf.write(line)
                logger.info("搜索子进程完成（fallback），本次采集 %d 条，输出: %s", len(new_lines), task_output)
                return task_output

        raise NonRetryableError("搜索采集未产出结果文件", step=self.STEP_SEARCH)

    def _extract_new_lines(self, file_path: Path, skip_count: int) -> List[str]:
        """读取文件，跳过前 skip_count 行，返回剩余行"""
        lines: List[str] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < skip_count:
                    continue
                if line.strip():
                    lines.append(line)
        return lines

    def _do_fetch_comments(
        self,
        input_path: Optional[Path],
        video_ids: Optional[List[str]] = None,
        source_task_id: Optional[str] = None,
        max_comments_per_video: int = 200,
    ) -> Path:
        """Collect comments and write standard comments_raw outputs."""
        workspace_dir = self._current_task_workspace_dir()
        output_dir = workspace_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "comments_raw.jsonl"
        csv_path = output_dir / "comments_raw.csv"
        output_path.touch(exist_ok=True)

        videos_in = len(self._load_comment_video_records(input_path, video_ids))
        if videos_in <= 0:
            raise NonRetryableError("评论采集输入中没有可用视频 ID", step=self.STEP_COMMENTS)

        venv_python = self._get_venv_python()
        comments_script = self._config.project_dir / "crawl_comments_v2.py"
        if not comments_script.exists():
            raise NonRetryableError(
                f"评论采集脚本不存在: {comments_script}",
                step=self.STEP_COMMENTS,
            )

        cmd = [
            str(venv_python),
            str(comments_script),
            "--output",
            str(output_path),
            "--max-comments",
            str(max_comments_per_video),
            "--skip-existing",
        ]
        if input_path:
            cmd.extend(["--input", str(input_path)])
        if video_ids:
            cmd.extend(["--video-ids", ",".join(str(v) for v in video_ids)])
        if source_task_id:
            cmd.extend(["--source-task-id", source_task_id])

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"

        logger.info("调用评论采集子进程: %s", " ".join(cmd))
        subprocess_error: Optional[str] = None
        try:
            subprocess.run(
                cmd,
                cwd=str(self._config.project_dir),
                check=True,
                timeout=3600,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            logger.error("评论采集子进程失败 (exit %d): %s", exc.returncode, exc)
            subprocess_error = f"评论采集子进程失败 (exit {exc.returncode}): {exc}"
        except subprocess.TimeoutExpired as exc:
            logger.error("评论采集子进程超时: %s", exc)
            subprocess_error = f"评论采集子进程超时: {exc}"

        comments_stats = self._convert_comments_jsonl_to_csv(
            jsonl_path=output_path,
            csv_path=csv_path,
            videos_in=videos_in,
        )
        if subprocess_error:
            comments_stats["errors"].append(subprocess_error)
        self._paths["comments_raw_csv"] = csv_path
        self._paths["comments_stats"] = comments_stats
        return output_path

    def _do_extract_scripts(self, input_path: Path, model: str) -> Path:
        """
        提取文案：下载视频 → ASR 转写 → 写入 JSONL。
        v5: 内置提取逻辑，不再依赖 extract_scripts_v2.py。
        """
        # 准备目录
        video_dir = ensure_dir_writable(
            self._config.video_dir, self._config.fallback_dir
        )
        output_dir = ensure_dir_writable(
            input_path.parent, self._config.fallback_dir
        )
        output_path = output_dir / f"{input_path.stem}_with_scripts.jsonl"

        # 磁盘空间预检
        check_disk_space_enforced(video_dir, min_gb=2.0)

        # 读取输入
        records = self._load_jsonl(input_path)
        valid = [r for r in records if r.get("video_download_url")]
        logger.info("有视频链接的: %d 条", len(valid))

        # 断点续传
        done_ids = self._state.load_completed_ids_from_jsonl(output_path, "aweme_id")

        # 加载 Whisper 模型
        try:
            from faster_whisper import WhisperModel
            whisper_model = WhisperModel(model, device="cpu", compute_type="int8")
        except ImportError:
            raise NonRetryableError(
                "faster-whisper 未安装", step=self.STEP_EXTRACT
            )
        except MemoryError:
            raise FatalError("内存不足，无法加载 Whisper 模型", step=self.STEP_EXTRACT)

        success_count = 0
        fail_count = 0

        max_workers = getattr(self._config, "max_workers", 1)
        # 确保 max_workers 合法
        if not isinstance(max_workers, int) or max_workers < 1:
            max_workers = 1

        if max_workers <= 1:
            # 串行模式（保持原有行为）
            for i, rec in enumerate(valid, 1):
                if self._cancel_event.is_set():
                    logger.warning("文案提取被取消")
                    break

                aweme_id = str(rec.get("aweme_id", ""))
                if not aweme_id or aweme_id == "None":
                    aweme_id = self._state.generate_pseudo_id(i, rec, prefix="video")
                    rec["aweme_id"] = aweme_id

                if aweme_id in done_ids or self._state.is_duplicate("script_extract", aweme_id):
                    continue

                logger.info("[%d/%d] %s", i, len(valid), aweme_id)

                # 每 10 条检查磁盘
                if i % 10 == 0:
                    try:
                        check_disk_space_enforced(video_dir, min_gb=0.5)
                    except FatalError as e:
                        self._state.mark_step_failed(
                            self.STEP_EXTRACT, str(e), EXIT_FATAL
                        )
                        raise

                # 下载
                video_file = video_dir / f"{aweme_id}.mp4"
                try:
                    video_size = video_file.stat().st_size
                except FileNotFoundError:
                    video_size = 0
                if not (video_file.exists() and video_size > 10000):
                    try:
                        ok = self._download_video(
                            rec.get("video_download_url", ""), str(video_file)
                        )
                    except Exception as e:
                        logger.error("下载重试耗尽: %s: %s", aweme_id, e)
                        ok = False

                    if not ok:
                        rec["script_text"] = ""
                        rec["script_status"] = "download_failed"
                        append_record(output_path, rec, self._config.fallback_dir)
                        self._state.mark_written("script_extract", aweme_id)
                        fail_count += 1
                        continue

                # 转写
                script_text = self._transcribe_video(str(video_file), whisper_model)
                if script_text:
                    rec["script_text"] = script_text
                    rec["script_status"] = "success"
                    success_count += 1
                else:
                    rec["script_text"] = ""
                    rec["script_status"] = "asr_failed"
                    fail_count += 1

                # ★ 立即写入 ★
                append_record(output_path, rec, self._config.fallback_dir)
                self._state.mark_written("script_extract", aweme_id)

                # 删除视频节省磁盘
                if not self._config.keep_videos and video_file.exists():
                    video_file.unlink()
        else:
            # 并发模式
            def _process_one(idx: int, rec: dict) -> Dict[str, Any]:
                """处理单条视频，返回结果字典"""
                aweme_id = str(rec.get("aweme_id", ""))
                if not aweme_id or aweme_id == "None":
                    aweme_id = self._state.generate_pseudo_id(idx, rec, prefix="video")
                    rec["aweme_id"] = aweme_id

                if aweme_id in done_ids or self._state.is_duplicate("script_extract", aweme_id):
                    return {"action": "skip"}

                logger.info("[%d/%d] %s", idx, len(valid), aweme_id)

                # 下载
                video_file = video_dir / f"{aweme_id}.mp4"
                try:
                    video_size = video_file.stat().st_size
                except FileNotFoundError:
                    video_size = 0
                if not (video_file.exists() and video_size > 10000):
                    try:
                        ok = self._download_video(
                            rec.get("video_download_url", ""), str(video_file)
                        )
                    except Exception as e:
                        logger.error("下载重试耗尽: %s: %s", aweme_id, e)
                        ok = False

                    if not ok:
                        return {"action": "fail", "aweme_id": aweme_id, "status": "download_failed"}

                # 转写
                script_text = self._transcribe_video(str(video_file), whisper_model)
                if script_text:
                    rec["script_text"] = script_text
                    rec["script_status"] = "success"
                else:
                    rec["script_text"] = ""
                    rec["script_status"] = "asr_failed"

                # 立即写入（线程安全：append_record 内部有原子写入）
                append_record(output_path, rec, self._config.fallback_dir)
                self._state.mark_written("script_extract", aweme_id)

                # 删除视频节省磁盘
                if not self._config.keep_videos and video_file.exists():
                    try:
                        video_file.unlink()
                    except OSError:
                        pass

                if rec["script_status"] == "success":
                    return {"action": "success", "aweme_id": aweme_id}
                else:
                    return {"action": "fail", "aweme_id": aweme_id, "status": "asr_failed"}

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i, rec in enumerate(valid, 1):
                    if self._cancel_event.is_set():
                        logger.warning("文案提取被取消，不再提交新任务")
                        break
                    # 磁盘检查（仅主线程）
                    if i % 10 == 0:
                        try:
                            check_disk_space_enforced(video_dir, min_gb=0.5)
                        except FatalError as e:
                            self._state.mark_step_failed(
                                self.STEP_EXTRACT, str(e), EXIT_FATAL
                            )
                            raise
                    future = executor.submit(_process_one, i, rec)
                    futures[future] = i

                for future in as_completed(futures):
                    if self._cancel_event.is_set():
                        break
                    try:
                        result = future.result()
                        if result["action"] == "success":
                            success_count += 1
                        elif result["action"] == "fail":
                            fail_count += 1
                            if result.get("status") == "download_failed":
                                # 写入下载失败记录
                                for rec in valid:
                                    if str(rec.get("aweme_id", "")) == result["aweme_id"]:
                                        rec["script_text"] = ""
                                        rec["script_status"] = "download_failed"
                                        append_record(output_path, rec, self._config.fallback_dir)
                                        self._state.mark_written("script_extract", result["aweme_id"])
                                        break
                    except Exception as e:
                        logger.error("并发处理异常: %s", e)
                        fail_count += 1

        logger.info(
            "文案提取完成: 成功 %d, 失败 %d, 输出 %s",
            success_count, fail_count, output_path,
        )
        # 刷新去重索引到磁盘
        self._state.flush_dedupe()
        return output_path

    def _do_merge(
        self,
        video_path: Optional[Path],
        comments_path: Optional[Path],
        scripts_path: Optional[Path],
        output_csv: Optional[Path],
    ) -> Path:
        """合并三份数据生成标准 CSV"""
        if not video_path or not video_path.exists():
            raise NonRetryableError(
                f"视频数据不存在: {video_path}", step=self.STEP_MERGE
            )

        # 加载数据
        videos = self._load_jsonl(video_path)
        comments = self._load_jsonl(comments_path) if comments_path and comments_path.exists() else []
        scripts = self._load_jsonl(scripts_path) if scripts_path and scripts_path.exists() else []

        logger.info(
            "数据源: 视频 %d | 评论 %d | 文案 %d",
            len(videos), len(comments), len(scripts),
        )

        # 去重
        videos = self._deduplicate(videos, "aweme_id")
        scripts = self._deduplicate(scripts, "aweme_id")

        # 构建索引
        scripts_map: Dict[str, dict] = {
            str(r.get("aweme_id", "")): r
            for r in scripts if r.get("aweme_id")
        }
        comments_map: Dict[str, List[str]] = defaultdict(list)
        for c in comments:
            aid = str(c.get("aweme_id", ""))
            text = c.get("content") or c.get("text") or ""
            if text:
                comments_map[aid].append(text)

        # 合并
        rows = []
        for video in videos:
            aid = str(video.get("aweme_id", ""))
            if not aid or aid == "None":
                continue

            script_rec = scripts_map.get(aid, {})
            script_text = ""
            if script_rec.get("script_status") == "success":
                script_text = script_rec.get("script_text", "")

            video_comments = comments_map.get(aid, [])
            comments_str = "|".join(c.replace("|", "/") for c in video_comments)

            likes = parse_count(video.get("liked_count", 0))
            favorites = parse_count(video.get("collected_count", 0))
            shares = parse_count(video.get("share_count", 0))

            rows.append({
                "video_id": aid,
                "platform": "douyin",
                "script_text": script_text,
                "likes": likes,
                "favorites": favorites,
                "shares": shares,
                "comments": comments_str,
            })

        # 校验：超限抛异常而非静默截断
        MAX_CSV_ROWS = 200
        if len(rows) > MAX_CSV_ROWS:
            raise NonRetryableError(
                f"合并数据行数 {len(rows)} 超过上限 {MAX_CSV_ROWS}，"
                f"请缩小采集范围或联系管理员调整上限",
                step=self.STEP_MERGE,
                details={"row_count": len(rows), "max_rows": MAX_CSV_ROWS},
            )

        # 输出
        if not output_csv:
            output_csv = self._config.data_dir / "douyin_koubo_data.csv"

        actual_dir = ensure_dir_writable(
            output_csv.parent, self._config.fallback_dir
        )
        if actual_dir != output_csv.parent:
            output_csv = actual_dir / "douyin_koubo_data.csv"

        check_disk_space_enforced(actual_dir, min_gb=0.1)

        fieldnames = [
            "video_id", "platform", "script_text",
            "likes", "favorites", "shares", "comments",
        ]
        # 原子写入：先写临时文件，再 os.replace 替换
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(output_csv.parent),
            prefix=output_csv.stem + ".tmp",
            suffix=".csv",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(tmp_path, str(output_csv))
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        file_size = output_csv.stat().st_size
        logger.info(
            "CSV: %s (%.1fKB, %d 行)",
            output_csv, file_size / 1024, len(rows),
        )
        return output_csv

    # ═══════════════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════════════

    def _current_task_workspace_dir(self) -> Path:
        """Return the current API task workspace from project_dir/state_dir_name."""
        state_parent = Path(self._config.state_dir_name).parent
        if str(state_parent) in ("", "."):
            return self._config.project_dir
        if self._config.project_dir.name == state_parent.name:
            return self._config.project_dir
        return self._config.project_dir / state_parent


    @staticmethod
    def _comment_video_id(record: Dict[str, Any]) -> str:
        for key in ("aweme_id", "video_id", "note_id", "item_id"):
            value = record.get(key)
            if value is not None and str(value).strip() and str(value).strip() != "None":
                return str(value).strip()
        return ""


    def _load_comment_video_records(
        self,
        input_path: Optional[Path],
        video_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        if input_path:
            if input_path.suffix.lower() == ".csv":
                with open(str(input_path), "r", encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    records.extend(dict(row) for row in reader)
            else:
                records.extend(self._load_jsonl(input_path))

        for video_id in video_ids or []:
            value = str(video_id).strip()
            if value:
                records.append({"aweme_id": value, "video_id": value})

        seen: Set[str] = set()
        unique_records: List[Dict[str, Any]] = []
        for record in records:
            aweme_id = self._comment_video_id(record)
            if not aweme_id or aweme_id in seen:
                continue
            seen.add(aweme_id)
            unique_records.append(record)
        return unique_records


    def _get_venv_python(self) -> Path:
        """获取 venv 中的 Python 路径，不存在时回退到当前 Python"""
        project_dir = self._config.project_dir
        if sys.platform == "win32":
            venv_python = project_dir / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = project_dir / ".venv" / "bin" / "python"

        if venv_python.exists():
            return venv_python

        logger.info("venv 不存在 (%s)，使用当前 Python: %s", venv_python, sys.executable)
        return Path(sys.executable)

    @staticmethod
    def _load_jsonl(filepath: Path) -> list:
        """加载 JSONL 文件"""
        if not filepath.exists():
            return []
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(
                        "JSONL 损坏行已跳过: %s 第 %d 行: %s",
                        filepath, line_num, str(e)[:100],
                    )
        return records

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


    def _convert_comments_jsonl_to_csv(
        self,
        jsonl_path: Path,
        csv_path: Path,
        videos_in: int,
    ) -> Dict[str, Any]:
        fieldnames = [
            "source_keyword",
            "platform",
            "source_task_id",
            "video_id",
            "aweme_id",
            "aweme_url",
            "comment_id",
            "parent_comment_id",
            "user_id",
            "nickname",
            "content",
            "liked_count",
            "reply_count",
            "create_time",
            "ip_location",
            "crawl_time",
        ]
        stats: Dict[str, Any] = {
            "videos_in": videos_in,
            "videos_success": 0,
            "comments_out": 0,
            "comments_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []
        success_video_ids: Set[str] = set()

        if jsonl_path.exists():
            with open(str(jsonl_path), "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        stats["errors"].append(f"line {line_num}: {str(exc)[:120]}")
                        continue

                    liked_count = self._safe_int(rec.get("liked_count", 0))
                    reply_count = self._safe_int(rec.get("reply_count", 0))
                    aweme_id = str(rec.get("aweme_id") or rec.get("video_id") or "").strip()
                    video_id = str(rec.get("video_id") or aweme_id).strip()
                    if aweme_id or video_id:
                        success_video_ids.add(aweme_id or video_id)

                    rows.append({
                        "source_keyword": str(rec.get("source_keyword", "")),
                        "platform": str(rec.get("platform") or "douyin"),
                        "source_task_id": str(rec.get("source_task_id", "")),
                        "video_id": video_id,
                        "aweme_id": aweme_id,
                        "aweme_url": str(rec.get("aweme_url", "")),
                        "comment_id": str(rec.get("comment_id", "")),
                        "parent_comment_id": str(rec.get("parent_comment_id", "")),
                        "user_id": str(rec.get("user_id", "")),
                        "nickname": str(rec.get("nickname", "")),
                        "content": str(rec.get("content", "")),
                        "liked_count": liked_count,
                        "reply_count": reply_count,
                        "create_time": str(rec.get("create_time", "")),
                        "ip_location": str(rec.get("ip_location", "")),
                        "crawl_time": str(rec.get("crawl_time", "")),
                    })

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(csv_path), "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        stats["videos_success"] = len(success_video_ids)
        stats["comments_out"] = len(rows)
        stats["comments_csv_generated"] = True
        return stats


    @staticmethod
    def _normalize_comment_text(value: Any) -> str:
        text = "" if value is None else str(value)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"([!?！？。,.，、~～])\1{2,}", r"\1\1", text)
        return text


    @staticmethod
    def _comment_compact_key(text: str) -> str:
        return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


    @staticmethod
    def _is_emoji_only(text: str) -> bool:
        compact = text.strip()
        if not compact:
            return False
        meaningful = re.search(r"[\u4e00-\u9fffA-Za-z0-9]", compact)
        if meaningful:
            return False
        return any(unicodedata.category(ch).startswith("S") for ch in compact)


    @staticmethod
    def _extract_pain_tags(text: str) -> List[str]:
        rules = [
            ("压线", r"压线|压到线|轧线|踩线"),
            ("30公分", r"30\s*公分|三十\s*公分|30\s*厘米|三十\s*厘米"),
            ("看点不准", r"看不准|看点|点位|点不准|找不准"),
            ("后视镜", r"后视镜|镜子|倒车镜"),
            ("方向盘", r"方向盘|打方向|回方向"),
            ("靠边太宽", r"太宽|靠边.*宽|离边.*远|距离.*宽"),
            ("挂科", r"挂科|挂了|挂的|没过|不过|不合格"),
            ("紧张", r"紧张|一紧张|慌|心态|害怕|怕"),
            ("考试忘步骤", r"忘步骤|忘了|忘记|想不起来|流程|顺序"),
            ("教练讲不清", r"教练.*没讲|教练.*讲不清|没讲清|讲不清|不清楚"),
            ("想要方法", r"方法|技巧|教程|怎么练|求教|教一下|有没有.*办法"),
        ]
        tags: List[str] = []
        for tag, pattern in rules:
            if re.search(pattern, text, flags=re.IGNORECASE):
                tags.append(tag)
        return tags


    @staticmethod
    def _infer_comment_intent(text: str, pain_tags: List[str], invalid_reason: str) -> str:
        if invalid_reason:
            if invalid_reason in {"ad_spam", "contact_spam"}:
                return "spam"
            if invalid_reason == "irrelevant":
                return "irrelevant"
            return "meaningless"
        if re.search(r"怎么|咋|如何|怎么看|怎么.*看|吗|么|哪里|到底|[?？]", text):
            return "question"
        if re.search(r"求|想要|有没有.*方法|教一下|详细|展开", text):
            return "request_more_detail"
        if re.search(r"不对|不是|没用|不同意|反而|但是", text):
            return "objection"
        if pain_tags:
            return "pain"
        if re.search(r"我也|同感|确实|对对|一样|赞同", text):
            return "agreement"
        if re.search(r"我|自己|考试|练车|教练|科目|挂|总是|老是", text):
            return "experience"
        return "experience"


    def _classify_clean_comment(
        self,
        rec: Dict[str, Any],
        seen_content: Set[str],
    ) -> Dict[str, Any]:
        raw_content = str(rec.get("content", ""))
        clean_content = self._normalize_comment_text(raw_content)
        compact = self._comment_compact_key(clean_content)
        pain_tags = self._extract_pain_tags(clean_content)
        invalid_reason = ""

        if not clean_content:
            invalid_reason = "empty_comment"
        elif self._is_emoji_only(clean_content):
            invalid_reason = "emoji_only"
        elif compact in seen_content:
            invalid_reason = "duplicate"
        elif re.search(r"(微信|加v|加V|加微|v信|vx|VX|qq|QQ|电话|手机号|联系我)", clean_content):
            invalid_reason = "contact_spam"
        elif re.search(r"(包过|代考|办证|引流|优惠|推广|广告|招生|私教|直播间)", clean_content):
            invalid_reason = "ad_spam"
        elif re.search(r"(傻逼|sb|SB|滚|去死|脑残)", clean_content):
            invalid_reason = "attack_or_abuse"
        elif not pain_tags and re.fullmatch(r"(6+|哈+|哈哈+|笑死+|路过|打卡|赞+|牛+|666+)", compact):
            invalid_reason = "meaningless"
        elif not pain_tags and len(compact) <= 2:
            invalid_reason = "too_short"
        elif not pain_tags and re.search(r"(音乐|衣服|美女|帅哥|主播|bgm|BGM|哪里买)", clean_content):
            invalid_reason = "irrelevant"

        if compact and invalid_reason != "duplicate":
            seen_content.add(compact)

        is_valid = not invalid_reason
        intent_type = self._infer_comment_intent(clean_content, pain_tags, invalid_reason)
        confidence = 0.9 if is_valid and pain_tags else 0.8 if is_valid else 0.75

        return {
            "source_keyword": str(rec.get("source_keyword", "")),
            "platform": str(rec.get("platform") or "douyin"),
            "source_task_id": str(rec.get("source_task_id", "")),
            "video_id": str(rec.get("video_id") or rec.get("aweme_id") or ""),
            "aweme_id": str(rec.get("aweme_id") or rec.get("video_id") or ""),
            "aweme_url": str(rec.get("aweme_url", "")),
            "comment_id": str(rec.get("comment_id", "")),
            "raw_content": raw_content,
            "clean_content": clean_content,
            "is_valid": is_valid,
            "invalid_reason": invalid_reason,
            "pain_tags": pain_tags,
            "intent_type": intent_type,
            "confidence": confidence,
            "liked_count": self._safe_int(rec.get("liked_count", 0)),
            "reply_count": self._safe_int(rec.get("reply_count", 0)),
            "create_time": str(rec.get("create_time", "")),
            "crawl_time": str(rec.get("crawl_time", "")),
        }


    def _do_clean_comments(self, raw_jsonl_path: Path) -> tuple[Path, Path, Dict[str, Any]]:
        clean_jsonl_path = raw_jsonl_path.with_name("comments_clean.jsonl")
        clean_csv_path = raw_jsonl_path.with_name("comments_clean.csv")
        fieldnames = [
            "source_keyword",
            "platform",
            "source_task_id",
            "video_id",
            "aweme_id",
            "aweme_url",
            "comment_id",
            "raw_content",
            "clean_content",
            "is_valid",
            "invalid_reason",
            "pain_tags",
            "intent_type",
            "confidence",
            "liked_count",
            "reply_count",
            "create_time",
            "crawl_time",
        ]
        stats: Dict[str, Any] = {
            "comments_in": 0,
            "comments_valid": 0,
            "comments_invalid": 0,
            "duplicates_removed": 0,
            "clean_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []
        seen_content: Set[str] = set()

        if raw_jsonl_path.exists():
            with open(str(raw_jsonl_path), "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        stats["errors"].append(f"line {line_num}: {str(exc)[:120]}")
                        continue
                    stats["comments_in"] += 1
                    row = self._classify_clean_comment(rec, seen_content)
                    if row["is_valid"]:
                        stats["comments_valid"] += 1
                    else:
                        stats["comments_invalid"] += 1
                        if row["invalid_reason"] == "duplicate":
                            stats["duplicates_removed"] += 1
                    rows.append(row)

        clean_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(clean_jsonl_path), "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        with open(str(clean_csv_path), "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                csv_row = dict(row)
                csv_row["pain_tags"] = "|".join(row["pain_tags"])
                writer.writerow(csv_row)

        stats["clean_csv_generated"] = True
        return clean_jsonl_path, clean_csv_path, stats


    @staticmethod
    def _dedupe_text_list(items: Sequence[str]) -> List[str]:
        result: List[str] = []
        seen: Set[str] = set()
        for item in items:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result


    @staticmethod
    def _is_noise_title_hashtag(tag: str) -> bool:
        text = str(tag or "").strip().lower()
        if not text:
            return True
        noise_exact = {
            "学车",
            "驾考",
            "驾校",
            "热门",
            "上热门",
            "抖音热门",
            "dou小助手",
            "dou+",
            "热点",
            "挑战",
            "日常",
            "同城",
            "流量",
            "汽车",
            "干货分享",
            "知识分享",
        }
        if text in noise_exact:
            return True
        return any(token in text for token in ("上热门", "抖音热门", "dou", "热点挑战"))


    def _extract_title_hashtags(self, *texts: str) -> tuple[List[str], List[str]]:
        hashtags: List[str] = []
        noise_removed: List[str] = []
        seen: Set[str] = set()
        pattern = re.compile(r"#([^#\s，,。；;！!？?\r\n]+)")
        for text in texts:
            for match in pattern.findall(str(text or "")):
                tag = match.strip(" #\t\r\n,，.。!！?？;；:：、")
                if not tag:
                    continue
                label = f"#{tag}"
                if tag in seen:
                    noise_removed.append(label)
                    continue
                seen.add(tag)
                if self._is_noise_title_hashtag(tag):
                    noise_removed.append(label)
                    continue
                hashtags.append(tag)
        return hashtags, self._dedupe_text_list(noise_removed)


    def _normalize_title_text(self, value: str, noise_removed: List[str]) -> str:
        text = str(value or "")
        text = re.sub(r"#[^#\s，,。；;！!？?\r\n]+", " ", text)
        noise_terms = [
            "点击头像",
            "主页还有",
            "主页看合集",
            "关注我",
            "记得关注",
            "点赞关注",
            "点赞",
            "收藏起来",
            "建议收藏",
            "收藏转发",
            "转发收藏",
            "评论区",
            "蹲后续",
            "看完再走",
            "快来看看",
            "上热门",
            "热门推荐",
            "DOU小助手",
            "抖音热点",
            "抖音热门",
        ]
        for term in noise_terms:
            if term in text:
                noise_removed.append(term)
                text = text.replace(term, " ")

        core_terms = [
            "科目三",
            "科三",
            "靠边停车",
            "直线行驶",
            "30公分",
            "压线",
            "挂科",
            "找点",
            "看点",
            "后视镜",
            "方向盘",
            "一把过",
            "考试紧张",
        ]
        for term in core_terms:
            separated = re.compile(
                rf"({re.escape(term)})(?:[\s,，、/|]+{re.escape(term)})+"
            )
            compact = re.compile(rf"({re.escape(term)})(?:{re.escape(term)})+")
            if separated.search(text) or compact.search(text):
                noise_removed.append(term)
            text = separated.sub(term, text)
            text = compact.sub(term, text)

        text = re.sub(r"[ \t\r\n　]+", " ", text)
        text = re.sub(r"[，,。；;！!？?、|]{2,}", "，", text)
        return text.strip(" \t\r\n　,，。；;！!？?、|")


    @staticmethod
    def _infer_title_topic(haystack: str) -> str:
        text = str(haystack or "")
        if "靠边停车" in text or ("靠边" in text and "停车" in text):
            return "靠边停车"
        if "直线行驶" in text or "直线跑偏" in text:
            return "直线行驶"
        if "科目三" in text or "科三" in text:
            if any(token in text for token in ("流程", "全流程", "步骤")):
                return "科目三全流程"
            return "科目三"
        return ""


    @staticmethod
    def _infer_title_pain_point(haystack: str) -> str:
        text = str(haystack or "")
        has_30cm = bool(re.search(r"(30\s*公分|三十公分|30cm|30厘米)", text, re.I))
        if has_30cm and any(token in text for token in ("看不准", "找不准", "不准", "不会看", "看不清", "怎么看")):
            return "30公分看不准"
        if "压线" in text:
            return "压线"
        if "跑偏" in text:
            return "直线跑偏"
        if "紧张" in text:
            return "考试紧张"
        if "挂科" in text or "挂的" in text:
            return "挂科"
        if has_30cm:
            return "30公分"
        return ""


    @staticmethod
    def _infer_title_teaching_angle(haystack: str, pain_point: str) -> str:
        text = str(haystack or "")
        if any(token in text for token in ("找点", "点位", "看点")) or pain_point == "30公分看不准":
            return "找点方法"
        if "压线" in text or pain_point == "压线":
            return "防压线技巧"
        if any(token in text for token in ("流程", "步骤")):
            return "考试流程讲解"
        if "后视镜" in text:
            return "后视镜观察方法"
        if "方向盘" in text:
            return "方向盘控制"
        if any(token in text for token in ("保姆级", "教学", "技巧", "一把过")):
            return "技巧讲解"
        return ""


    def _clean_search_title_record(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        raw_title = str(rec.get("title", rec.get("raw_title", "")) or "")
        raw_desc = str(rec.get("desc", rec.get("raw_desc", "")) or "")
        hashtags, hashtag_noise = self._extract_title_hashtags(raw_title, raw_desc)
        noise_removed = list(hashtag_noise)
        clean_title = self._normalize_title_text(raw_title, noise_removed)
        clean_desc = self._normalize_title_text(raw_desc, noise_removed)
        if not clean_title:
            clean_title = clean_desc or " ".join(hashtags[:2]) or str(rec.get("source_keyword", "")).strip()

        haystack = " ".join([raw_title, raw_desc, clean_title, clean_desc, " ".join(hashtags)])
        topic = self._infer_title_topic(haystack)
        pain_point = self._infer_title_pain_point(haystack)
        teaching_angle = self._infer_title_teaching_angle(haystack, pain_point)

        def _safe_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        liked_count = _safe_int(rec.get("liked_count", 0))
        collected_count = _safe_int(rec.get("collected_count", 0))
        comment_count = _safe_int(rec.get("comment_count", 0))
        share_count = _safe_int(rec.get("share_count", 0))
        total_engagement = _safe_int(
            rec.get("total_engagement", liked_count + collected_count + comment_count + share_count)
        )

        return {
            "source_keyword": str(rec.get("source_keyword", "")),
            "platform": str(rec.get("platform", "douyin") or "douyin"),
            "video_id": str(rec.get("video_id", "")),
            "aweme_id": str(rec.get("aweme_id", "")),
            "raw_title": raw_title,
            "clean_title": clean_title,
            "raw_desc": raw_desc,
            "clean_desc": clean_desc,
            "hashtags": hashtags,
            "topic": topic,
            "pain_point": pain_point,
            "teaching_angle": teaching_angle,
            "title_noise_removed": self._dedupe_text_list(noise_removed),
            "aweme_url": str(rec.get("aweme_url", "")),
            "liked_count": liked_count,
            "collected_count": collected_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "total_engagement": total_engagement,
        }


    def _load_search_rows_for_title_clean(
        self, search_csv_path: Path, search_jsonl_path: Optional[Path]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        errors: List[str] = []
        if search_csv_path.exists():
            try:
                with open(str(search_csv_path), "r", encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f)), errors
            except Exception as e:
                errors.append(f"read_csv_failed: {str(e)[:200]}")

        if search_jsonl_path and search_jsonl_path.exists():
            try:
                return self._load_jsonl(search_jsonl_path), errors
            except Exception as e:
                errors.append(f"read_jsonl_failed: {str(e)[:200]}")

        if not search_csv_path.exists():
            errors.append(f"search_csv_missing: {search_csv_path}")
        if search_jsonl_path and not search_jsonl_path.exists():
            errors.append(f"search_jsonl_missing: {search_jsonl_path}")
        return [], errors


    def _do_clean_search_titles(
        self, search_csv_path: Path, search_jsonl_path: Optional[Path] = None
    ) -> tuple[Path, Path, Dict[str, Any]]:
        clean_jsonl_path = search_csv_path.with_name("search_title_clean.jsonl")
        clean_csv_path = search_csv_path.with_name("search_title_clean.csv")
        fieldnames = [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "raw_title",
            "clean_title",
            "raw_desc",
            "clean_desc",
            "hashtags",
            "topic",
            "pain_point",
            "teaching_angle",
            "title_noise_removed",
            "aweme_url",
            "liked_count",
            "collected_count",
            "comment_count",
            "share_count",
            "total_engagement",
        ]
        stats: Dict[str, Any] = {
            "rows_in": 0,
            "rows_out": 0,
            "clean_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []
        try:
            records, load_errors = self._load_search_rows_for_title_clean(search_csv_path, search_jsonl_path)
            stats["errors"].extend(load_errors)
            stats["rows_in"] = len(records)
            for idx, rec in enumerate(records, start=1):
                try:
                    rows.append(self._clean_search_title_record(rec))
                except Exception as e:
                    stats["errors"].append(f"row_{idx}_failed: {str(e)[:200]}")

            stats["rows_out"] = len(rows)
            clean_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(clean_jsonl_path), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            with open(str(clean_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    csv_row = dict(row)
                    csv_row["hashtags"] = "|".join(row["hashtags"])
                    csv_row["title_noise_removed"] = "|".join(row["title_noise_removed"])
                    writer.writerow(csv_row)
            stats["clean_csv_generated"] = True
        except Exception as e:
            stats["errors"].append(f"title_clean_failed: {str(e)[:500]}")
            try:
                clean_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
                clean_jsonl_path.write_text("", encoding="utf-8")
                with open(str(clean_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writeheader()
                stats["clean_csv_generated"] = True
            except Exception as write_error:
                stats["errors"].append(f"title_clean_write_failed: {str(write_error)[:500]}")

        return clean_jsonl_path, clean_csv_path, stats


    @staticmethod
    def _join_source_text(*parts: Any) -> str:
        texts: List[str] = []
        seen: Set[str] = set()
        for part in parts:
            text = re.sub(r"\s+", " ", str(part or "")).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            texts.append(text)
        return " ".join(texts)


    @staticmethod
    def _script_source_key(rec: Dict[str, Any]) -> str:
        for key in ("aweme_id", "video_id", "aweme_url"):
            value = str(rec.get(key, "") or "").strip()
            if value and value != "None":
                return value
        return ""


    def _load_title_clean_map(self, title_clean_csv_path: Optional[Path]) -> tuple[Dict[str, Dict[str, Any]], List[str]]:
        errors: List[str] = []
        clean_map: Dict[str, Dict[str, Any]] = {}
        if not title_clean_csv_path or not title_clean_csv_path.exists():
            return clean_map, errors
        try:
            with open(str(title_clean_csv_path), "r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    keys = self._dedupe_text_list([
                        str(row.get("aweme_id", "") or "").strip(),
                        str(row.get("video_id", "") or "").strip(),
                        str(row.get("aweme_url", "") or "").strip(),
                    ])
                    for key in keys:
                        if key and key != "None":
                            clean_map[key] = row
        except Exception as e:
            errors.append(f"read_title_clean_failed: {str(e)[:200]}")
        return clean_map, errors


    def _build_script_source_record(
        self,
        rec: Dict[str, Any],
        clean_rec: Optional[Dict[str, Any]],
        created_at: str,
    ) -> Dict[str, Any]:
        raw_title = str(rec.get("title", rec.get("raw_title", "")) or "")
        raw_desc = str(rec.get("desc", rec.get("raw_desc", "")) or "")
        clean_title = str((clean_rec or {}).get("clean_title", rec.get("clean_title", "")) or "")
        clean_desc = str((clean_rec or {}).get("clean_desc", rec.get("clean_desc", "")) or "")
        video_download_url = str(rec.get("video_download_url", "") or "").strip()

        title_desc_text = self._join_source_text(raw_title, raw_desc)
        clean_title_text = self._join_source_text(clean_title, clean_desc)
        title_desc_available = bool(title_desc_text)
        clean_title_available = bool(clean_title_text)
        video_download_available = bool(video_download_url)
        asr_planned = video_download_available

        notes: List[str] = []
        if clean_title_available:
            quality = "medium"
            status = "available"
            notes.append("clean_title_desc_available")
        elif title_desc_available:
            quality = "weak"
            status = "available"
            notes.append("raw_title_desc_available")
        elif video_download_available:
            quality = "low"
            status = "planned"
            notes.append("video_download_available_asr_planned")
        else:
            quality = "missing"
            status = "missing"
            notes.append("no_text_or_video_source")

        if video_download_available and quality != "low":
            notes.append("video_download_available")
        if not video_download_available:
            notes.append("video_download_missing")

        return {
            "source_keyword": str(rec.get("source_keyword", "")),
            "platform": str(rec.get("platform", "douyin") or "douyin"),
            "video_id": str(rec.get("video_id", "")),
            "aweme_id": str(rec.get("aweme_id", "")),
            "aweme_url": str(rec.get("aweme_url", "")),
            "raw_title": raw_title,
            "clean_title": clean_title,
            "raw_desc": raw_desc,
            "clean_desc": clean_desc,
            "video_download_url": video_download_url,
            "source_title_desc_available": title_desc_available,
            "source_title_desc_text": title_desc_text,
            "source_clean_title_available": clean_title_available,
            "source_clean_title_text": clean_title_text,
            "source_video_download_available": video_download_available,
            "source_video_download_url": video_download_url,
            "source_asr_planned": asr_planned,
            "source_ocr_planned": False,
            "source_subtitle_planned": False,
            "script_source_status": status,
            "script_source_quality": quality,
            "script_source_notes": "|".join(self._dedupe_text_list(notes)),
            "created_at": created_at,
        }


    def _do_build_script_sources(
        self,
        search_csv_path: Path,
        search_jsonl_path: Optional[Path] = None,
        title_clean_csv_path: Optional[Path] = None,
    ) -> tuple[Path, Path, Dict[str, Any]]:
        sources_jsonl_path = search_csv_path.with_name("script_sources.jsonl")
        sources_csv_path = search_csv_path.with_name("script_sources.csv")
        fieldnames = [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "aweme_url",
            "raw_title",
            "clean_title",
            "raw_desc",
            "clean_desc",
            "video_download_url",
            "source_title_desc_available",
            "source_title_desc_text",
            "source_clean_title_available",
            "source_clean_title_text",
            "source_video_download_available",
            "source_video_download_url",
            "source_asr_planned",
            "source_ocr_planned",
            "source_subtitle_planned",
            "script_source_status",
            "script_source_quality",
            "script_source_notes",
            "created_at",
        ]
        stats: Dict[str, Any] = {
            "rows_in": 0,
            "rows_out": 0,
            "title_desc_available": 0,
            "clean_title_available": 0,
            "video_download_available": 0,
            "asr_planned": 0,
            "script_sources_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []
        try:
            records, load_errors = self._load_search_rows_for_title_clean(search_csv_path, search_jsonl_path)
            stats["errors"].extend(load_errors)
            clean_map, clean_errors = self._load_title_clean_map(title_clean_csv_path)
            stats["errors"].extend(clean_errors)
            stats["rows_in"] = len(records)
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            for idx, rec in enumerate(records, start=1):
                try:
                    clean_rec = clean_map.get(self._script_source_key(rec))
                    row = self._build_script_source_record(rec, clean_rec, created_at)
                    if row["source_title_desc_available"]:
                        stats["title_desc_available"] += 1
                    if row["source_clean_title_available"]:
                        stats["clean_title_available"] += 1
                    if row["source_video_download_available"]:
                        stats["video_download_available"] += 1
                    if row["source_asr_planned"]:
                        stats["asr_planned"] += 1
                    rows.append(row)
                except Exception as e:
                    stats["errors"].append(f"row_{idx}_failed: {str(e)[:200]}")

            stats["rows_out"] = len(rows)
            sources_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(sources_jsonl_path), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            with open(str(sources_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            stats["script_sources_csv_generated"] = True
        except Exception as e:
            stats["errors"].append(f"script_sources_failed: {str(e)[:500]}")
            try:
                sources_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
                sources_jsonl_path.write_text("", encoding="utf-8")
                with open(str(sources_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writeheader()
                stats["script_sources_csv_generated"] = True
            except Exception as write_error:
                stats["errors"].append(f"script_sources_write_failed: {str(write_error)[:500]}")

        return sources_jsonl_path, sources_csv_path, stats


    @staticmethod
    def _script_raw_fieldnames() -> List[str]:
        return [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "aweme_url",
            "video_download_url",
            "local_video_path",
            "download_status",
            "download_error",
            "asr_status",
            "asr_raw_text",
            "asr_error",
            "script_raw_quality",
            "created_at",
        ]


    @staticmethod
    def _truthy_source_flag(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        return text in ("1", "true", "yes", "y", "on")


    @staticmethod
    def _script_raw_video_name(rec: Dict[str, Any], idx: int) -> str:
        raw = str(rec.get("aweme_id") or rec.get("video_id") or f"row_{idx}")
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._")
        return (safe[:80] or f"row_{idx}") + ".mp4"


    def _load_script_source_rows(
        self,
        script_sources_jsonl: Optional[Path],
        script_sources_csv: Optional[Path],
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        errors: List[str] = []
        if script_sources_jsonl and script_sources_jsonl.exists():
            try:
                return self._load_jsonl(script_sources_jsonl), errors
            except Exception as e:
                errors.append(f"read_script_sources_jsonl_failed: {str(e)[:200]}")

        if script_sources_csv and script_sources_csv.exists():
            try:
                with open(str(script_sources_csv), "r", encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f)), errors
            except Exception as e:
                errors.append(f"read_script_sources_csv_failed: {str(e)[:200]}")

        errors.append("script_sources_missing")
        return [], errors


    @staticmethod
    def _load_script_raw_whisper_model(model_name: str) -> tuple[Optional[Any], str, str]:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None, "dependency_missing", "faster-whisper 未安装"

        try:
            return WhisperModel(model_name, device="cpu", compute_type="int8"), "", ""
        except MemoryError:
            return None, "failed", "内存不足，无法加载 Whisper 模型"
        except Exception as e:
            return None, "failed", f"Whisper 模型加载失败: {str(e)[:300]}"


    def _do_build_script_raw(
        self,
        script_sources_jsonl: Optional[Path] = None,
        script_sources_csv: Optional[Path] = None,
        model_name: str = "small",
        max_items: Optional[int] = None,
    ) -> tuple[Path, Path, Dict[str, Any]]:
        workspace_dir = self._current_task_workspace_dir()
        output_dir = workspace_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_jsonl_path = output_dir / "script_raw.jsonl"
        raw_csv_path = output_dir / "script_raw.csv"
        tmp_video_dir = workspace_dir / "tmp" / "videos"
        fieldnames = self._script_raw_fieldnames()
        stats: Dict[str, Any] = {
            "rows_in": 0,
            "rows_targeted": 0,
            "download_success": 0,
            "download_failed": 0,
            "asr_success": 0,
            "asr_failed": 0,
            "asr_dependency_missing": 0,
            "asr_empty_text": 0,
            "rows_out": 0,
            "script_raw_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []

        try:
            records, load_errors = self._load_script_source_rows(script_sources_jsonl, script_sources_csv)
            stats["errors"].extend(load_errors)
            stats["rows_in"] = len(records)
            limit = max_items
            if limit is None:
                try:
                    limit = int(getattr(self._config, "max_script_raw_items", 5) or 5)
                except (TypeError, ValueError):
                    limit = 5
            limit = max(0, limit)

            eligible_indexes: List[int] = []
            for idx, rec in enumerate(records, start=1):
                planned = self._truthy_source_flag(rec.get("source_asr_planned"))
                video_available = self._truthy_source_flag(rec.get("source_video_download_available"))
                video_url = str(
                    rec.get("video_download_url")
                    or rec.get("source_video_download_url")
                    or ""
                ).strip()
                if planned and video_available and video_url:
                    eligible_indexes.append(idx)

            selected_indexes = set(eligible_indexes[:limit])
            stats["rows_targeted"] = len(selected_indexes)
            if len(eligible_indexes) > limit:
                stats["errors"].append(
                    f"max_script_raw_items_limit: eligible={len(eligible_indexes)} processed={limit}"
                )

            disk_error = ""
            if selected_indexes:
                try:
                    tmp_video_dir.mkdir(parents=True, exist_ok=True)
                    check_disk_space_enforced(tmp_video_dir, min_gb=0.5)
                except Exception as e:
                    disk_error = str(e)[:300]
                    stats["errors"].append(f"script_raw_disk_check_failed: {disk_error}")

            whisper_model: Optional[Any] = None
            model_error_status = ""
            model_error = ""
            if selected_indexes and not disk_error:
                whisper_model, model_error_status, model_error = self._load_script_raw_whisper_model(model_name)

            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for idx, rec in enumerate(records, start=1):
                video_url = str(
                    rec.get("video_download_url")
                    or rec.get("source_video_download_url")
                    or ""
                ).strip()
                row: Dict[str, Any] = {
                    "source_keyword": str(rec.get("source_keyword", "")),
                    "platform": str(rec.get("platform", "douyin") or "douyin"),
                    "video_id": str(rec.get("video_id", "")),
                    "aweme_id": str(rec.get("aweme_id", "")),
                    "aweme_url": str(rec.get("aweme_url", "")),
                    "video_download_url": video_url,
                    "local_video_path": "",
                    "download_status": "skipped",
                    "download_error": "",
                    "asr_status": "skipped",
                    "asr_raw_text": "",
                    "asr_error": "",
                    "script_raw_quality": "missing",
                    "created_at": created_at,
                }

                if idx not in selected_indexes:
                    if idx in eligible_indexes:
                        row["download_error"] = "max_script_raw_items_limit"
                    rows.append(row)
                    continue

                video_file = tmp_video_dir / self._script_raw_video_name(rec, idx)
                row["local_video_path"] = str(video_file)

                if disk_error:
                    row["download_status"] = "failed"
                    row["download_error"] = disk_error
                    stats["download_failed"] += 1
                    rows.append(row)
                    continue

                if model_error_status:
                    row["asr_status"] = model_error_status
                    row["asr_error"] = model_error
                    if model_error_status == "dependency_missing":
                        stats["asr_dependency_missing"] += 1
                    else:
                        stats["asr_failed"] += 1
                    rows.append(row)
                    continue

                try:
                    ok = self._download_video(video_url, str(video_file))
                except Exception as e:
                    ok = False
                    row["download_error"] = str(e)[:500]

                if not ok:
                    row["download_status"] = "failed"
                    if not row["download_error"]:
                        row["download_error"] = "download_failed"
                    stats["download_failed"] += 1
                    rows.append(row)
                    continue

                row["download_status"] = "success"
                stats["download_success"] += 1

                try:
                    script_text = self._transcribe_video(str(video_file), whisper_model)
                    if script_text:
                        row["asr_status"] = "success"
                        row["asr_raw_text"] = script_text
                        row["script_raw_quality"] = "high"
                        stats["asr_success"] += 1
                    else:
                        row["asr_status"] = "empty_text"
                        row["script_raw_quality"] = "low"
                        stats["asr_empty_text"] += 1
                except Exception as e:
                    row["asr_status"] = "failed"
                    row["asr_error"] = str(e)[:500]
                    row["script_raw_quality"] = "low"
                    stats["asr_failed"] += 1
                finally:
                    if not self._config.keep_videos and video_file.exists():
                        try:
                            video_file.unlink()
                        except OSError as e:
                            stats["errors"].append(f"cleanup_failed: {video_file}: {str(e)[:120]}")

                rows.append(row)

            stats["rows_out"] = len(rows)
            with open(str(raw_jsonl_path), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            with open(str(raw_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            stats["script_raw_csv_generated"] = True
        except Exception as e:
            stats["errors"].append(f"script_raw_failed: {str(e)[:500]}")
            try:
                raw_jsonl_path.write_text("", encoding="utf-8")
                with open(str(raw_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writeheader()
                stats["script_raw_csv_generated"] = True
            except Exception as write_error:
                stats["errors"].append(f"script_raw_write_failed: {str(write_error)[:500]}")

        return raw_jsonl_path, raw_csv_path, stats


    @staticmethod
    def _script_clean_fieldnames() -> List[str]:
        return [
            "source_keyword",
            "platform",
            "video_id",
            "aweme_id",
            "aweme_url",
            "script_clean_text",
            "script_clean_source",
            "script_clean_status",
            "script_clean_quality",
            "script_clean_notes",
            "asr_status",
            "asr_raw_text",
            "script_raw_quality",
            "source_clean_title_available",
            "source_clean_title_text",
            "source_title_desc_available",
            "source_title_desc_text",
            "created_at",
        ]


    def _load_script_raw_rows(
        self,
        script_raw_jsonl: Optional[Path],
        script_raw_csv: Optional[Path],
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        errors: List[str] = []
        if script_raw_jsonl and script_raw_jsonl.exists():
            try:
                return self._load_jsonl(script_raw_jsonl), errors
            except Exception as e:
                errors.append(f"read_script_raw_jsonl_failed: {str(e)[:200]}")

        if script_raw_csv and script_raw_csv.exists():
            try:
                with open(str(script_raw_csv), "r", encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f)), errors
            except Exception as e:
                errors.append(f"read_script_raw_csv_failed: {str(e)[:200]}")

        errors.append("script_raw_missing")
        return [], errors


    def _build_script_clean_record(
        self,
        source_rec: Dict[str, Any],
        raw_rec: Optional[Dict[str, Any]],
        title_clean_rec: Optional[Dict[str, Any]],
        created_at: str,
    ) -> Dict[str, Any]:
        raw_rec = raw_rec or {}
        title_clean_rec = title_clean_rec or {}

        asr_text = str(raw_rec.get("asr_raw_text", "") or "").strip()
        source_clean_text = str(source_rec.get("source_clean_title_text", "") or "").strip()
        if not source_clean_text:
            source_clean_text = self._join_source_text(
                title_clean_rec.get("clean_title", ""),
                title_clean_rec.get("clean_desc", ""),
            )
        if not source_clean_text:
            source_clean_text = self._join_source_text(
                source_rec.get("clean_title", ""),
                source_rec.get("clean_desc", ""),
            )

        source_title_desc_text = str(source_rec.get("source_title_desc_text", "") or "").strip()
        if not source_title_desc_text:
            source_title_desc_text = self._join_source_text(
                source_rec.get("raw_title", source_rec.get("title", "")),
                source_rec.get("raw_desc", source_rec.get("desc", "")),
            )

        notes: List[str] = []
        if asr_text:
            clean_text = asr_text
            clean_source = "asr_raw"
            clean_status = "available"
            clean_quality = "high"
            notes.append("asr_raw_text_available")
        elif source_clean_text:
            clean_text = source_clean_text
            clean_source = "source_clean_title"
            clean_status = "available"
            clean_quality = "medium"
            notes.append("fallback_source_clean_title")
        elif source_title_desc_text:
            clean_text = source_title_desc_text
            clean_source = "source_title_desc"
            clean_status = "available"
            clean_quality = "weak"
            notes.append("fallback_source_title_desc")
        else:
            clean_text = ""
            clean_source = "missing"
            clean_status = "missing"
            clean_quality = "missing"
            notes.append("script_text_missing")

        asr_status = str(raw_rec.get("asr_status", "") or "").strip()
        if asr_status and asr_status != "success":
            notes.append(f"asr_status_{asr_status}")

        source_clean_available = bool(source_clean_text)
        source_title_desc_available = bool(source_title_desc_text)
        return {
            "source_keyword": str(source_rec.get("source_keyword", raw_rec.get("source_keyword", "")) or ""),
            "platform": str(source_rec.get("platform", raw_rec.get("platform", "douyin")) or "douyin"),
            "video_id": str(source_rec.get("video_id", raw_rec.get("video_id", "")) or ""),
            "aweme_id": str(source_rec.get("aweme_id", raw_rec.get("aweme_id", "")) or ""),
            "aweme_url": str(source_rec.get("aweme_url", raw_rec.get("aweme_url", "")) or ""),
            "script_clean_text": clean_text,
            "script_clean_source": clean_source,
            "script_clean_status": clean_status,
            "script_clean_quality": clean_quality,
            "script_clean_notes": "|".join(self._dedupe_text_list(notes)),
            "asr_status": asr_status,
            "asr_raw_text": asr_text,
            "script_raw_quality": str(raw_rec.get("script_raw_quality", "") or ""),
            "source_clean_title_available": source_clean_available,
            "source_clean_title_text": source_clean_text,
            "source_title_desc_available": source_title_desc_available,
            "source_title_desc_text": source_title_desc_text,
            "created_at": created_at,
        }


    def _do_build_script_clean(
        self,
        script_sources_jsonl: Optional[Path] = None,
        script_sources_csv: Optional[Path] = None,
        script_raw_jsonl: Optional[Path] = None,
        script_raw_csv: Optional[Path] = None,
        title_clean_csv: Optional[Path] = None,
    ) -> tuple[Path, Path, Dict[str, Any]]:
        output_dir = self._current_task_workspace_dir() / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        clean_jsonl_path = output_dir / "script_clean.jsonl"
        clean_csv_path = output_dir / "script_clean.csv"
        fieldnames = self._script_clean_fieldnames()
        stats: Dict[str, Any] = {
            "rows_in": 0,
            "script_raw_rows": 0,
            "rows_out": 0,
            "asr_text_used": 0,
            "clean_title_used": 0,
            "title_desc_used": 0,
            "missing": 0,
            "script_clean_csv_generated": False,
            "errors": [],
        }
        rows: List[Dict[str, Any]] = []

        try:
            source_records, source_errors = self._load_script_source_rows(
                script_sources_jsonl,
                script_sources_csv,
            )
            raw_records, raw_errors = self._load_script_raw_rows(
                script_raw_jsonl,
                script_raw_csv,
            )
            title_clean_map, title_clean_errors = self._load_title_clean_map(title_clean_csv)
            stats["errors"].extend(source_errors)
            stats["errors"].extend(raw_errors)
            stats["errors"].extend(title_clean_errors)
            stats["script_raw_rows"] = len(raw_records)

            records = source_records or raw_records
            stats["rows_in"] = len(records)
            raw_map = {
                self._script_source_key(rec): rec
                for rec in raw_records
                if self._script_source_key(rec)
            }
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            for idx, rec in enumerate(records, start=1):
                try:
                    key = self._script_source_key(rec)
                    raw_rec = raw_map.get(key, rec if not source_records else {})
                    title_clean_rec = title_clean_map.get(key)
                    row = self._build_script_clean_record(
                        rec,
                        raw_rec,
                        title_clean_rec,
                        created_at,
                    )
                    if row["script_clean_source"] == "asr_raw":
                        stats["asr_text_used"] += 1
                    elif row["script_clean_source"] == "source_clean_title":
                        stats["clean_title_used"] += 1
                    elif row["script_clean_source"] == "source_title_desc":
                        stats["title_desc_used"] += 1
                    else:
                        stats["missing"] += 1
                    rows.append(row)
                except Exception as e:
                    stats["errors"].append(f"row_{idx}_failed: {str(e)[:200]}")

            stats["rows_out"] = len(rows)
            with open(str(clean_jsonl_path), "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

            with open(str(clean_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            stats["script_clean_csv_generated"] = True
        except Exception as e:
            stats["errors"].append(f"script_clean_failed: {str(e)[:500]}")
            try:
                clean_jsonl_path.write_text("", encoding="utf-8")
                with open(str(clean_csv_path), "w", encoding="utf-8-sig", newline="") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writeheader()
                stats["script_clean_csv_generated"] = True
            except Exception as write_error:
                stats["errors"].append(f"script_clean_write_failed: {str(write_error)[:500]}")

        return clean_jsonl_path, clean_csv_path, stats


    def _convert_jsonl_to_standard_csv(
        self,
        jsonl_path: str,
        csv_path: str,
        source_keyword: str,
    ) -> dict:
        """
        将 search_result.jsonl 转换为标准 CSV（T016）。

        返回: {
            "rows_in": int,
            "rows_out": int,
            "duplicates_removed": int,
            "csv_generated": bool,
            "csv_error": str or None
        }
        """
        import csv as csv_module

        jsonl_f = Path(jsonl_path)
        csv_f = Path(csv_path)
        stats = {
            "rows_in": 0,
            "rows_out": 0,
            "duplicates_removed": 0,
            "csv_generated": False,
            "csv_error": None,
        }

        try:
            # 读取 JSONL
            records = self._load_jsonl(jsonl_f)
            stats["rows_in"] = len(records)
            if not records:
                stats["csv_error"] = "JSONL 文件为空"
                return stats

            # 去重（按 aweme_id 或 aweme_url，保留第一条）
            seen_ids: set = set()
            seen_urls: set = set()
            deduped = []
            for rec in records:
                aid = str(rec.get("aweme_id", "")).strip()
                aurl = str(rec.get("aweme_url", "")).strip()
                if aid and aid != "None":
                    if aid in seen_ids:
                        continue
                    seen_ids.add(aid)
                elif aurl:
                    if aurl in seen_urls:
                        continue
                    seen_urls.add(aurl)
                # 如果既没有 aid 也没有 url，保留（无法去重）
                deduped.append(rec)

            stats["duplicates_removed"] = stats["rows_in"] - len(deduped)

            # 转换为标准行
            rows = []
            for rec in deduped:
                aid = str(rec.get("aweme_id", "")).strip()
                aurl = str(rec.get("aweme_url", "")).strip()
                video_id = aid if aid and aid != "None" else ""

                # 整数转换（失败则 0）
                def _safe_int(val):
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return 0

                likes = _safe_int(rec.get("liked_count", 0))
                collected = _safe_int(rec.get("collected_count", 0))
                comments = _safe_int(rec.get("comment_count", 0))
                shares = _safe_int(rec.get("share_count", 0))
                total_engagement = likes + collected + comments + shares

                rows.append({
                    "source_keyword": source_keyword,
                    "platform": "douyin",
                    "video_id": video_id,
                    "aweme_id": aid if aid and aid != "None" else "",
                    "title": str(rec.get("title", "")),
                    "desc": str(rec.get("desc", "")),
                    "nickname": str(rec.get("nickname", "")),
                    "liked_count": likes,
                    "collected_count": collected,
                    "comment_count": comments,
                    "share_count": shares,
                    "total_engagement": total_engagement,
                    "aweme_url": aurl,
                    "cover_url": str(rec.get("cover_url", "")),
                    "video_download_url": str(rec.get("video_download_url", "")),
                    "music_download_url": str(rec.get("music_download_url", "")),
                    "create_time": str(rec.get("create_time", "")),
                    "last_modify_ts": str(rec.get("last_modify_ts", "")),
                })

            stats["rows_out"] = len(rows)

            # 写入 CSV（UTF-8-SIG 编码，Excel 兼容）
            csv_f.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = [
                "source_keyword",
                "platform",
                "video_id",
                "aweme_id",
                "title",
                "desc",
                "nickname",
                "liked_count",
                "collected_count",
                "comment_count",
                "share_count",
                "total_engagement",
                "aweme_url",
                "cover_url",
                "video_download_url",
                "music_download_url",
                "create_time",
                "last_modify_ts",
            ]
            with open(str(csv_f), "w", encoding="utf-8-sig", newline="") as f:
                writer = csv_module.DictWriter(f, fieldnames=fieldnames, quoting=csv_module.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(rows)

            stats["csv_generated"] = True
            logger.info(
                "CSV 转换完成: %s (%d 行, 去重 %d)", csv_f, len(rows), stats["duplicates_removed"]
            )
        except Exception as e:
            stats["csv_error"] = str(e)[:500]
            logger.error("CSV 转换失败: %s", e)

        return stats


    def _deduplicate(self, records: list, key: str = "aweme_id") -> list:
        """
        按 key 去重，优先保留 script_status=success。
        ★ 幂等键缺失时生成确定性伪 ID ★
        """
        seen: Dict[str, dict] = {}
        for i, rec in enumerate(records):
            aid = str(rec.get(key, ""))
            if not aid or aid == "None":
                aid = self._state.generate_pseudo_id(i + 1, rec, prefix="video")
                rec[key] = aid

            if aid not in seen:
                seen[aid] = rec
            else:
                if (rec.get("script_status") == "success" and
                        seen[aid].get("script_status") != "success"):
                    seen[aid] = rec
        return list(seen.values())

    @retry(max_retries=3, base_delay=5, backoff_factor=3,
           retryable_exceptions=(OSError, ConnectionError, TimeoutError))
    def _download_video(self, url: str, save_path: str, timeout: int = 120) -> bool:
        """下载视频到本地"""
        import httpx

        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.douyin.com/",
            })

            if resp.status_code == 429:
                wait_time = 60 + random.uniform(0, 30)
                logger.warning("HTTP 429 风控，等待 %.1fs（可被 cancel 中断）", wait_time)
                interrupted = self._cancel_event.wait(timeout=wait_time)
                if interrupted:
                    raise NonRetryableError(
                        "操作已被取消", step=self.STEP_EXTRACT
                    )
                raise ConnectionError("HTTP 429 rate limited")

            if resp.status_code >= 500:
                raise ConnectionError(f"HTTP {resp.status_code}")

            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return True

            # 小文件可能是防爬页面或空响应，重试
            if resp.status_code == 200 and len(resp.content) <= 10000:
                logger.warning(
                    "下载返回小文件 (%d bytes)，可能是防爬页面，重试: %s",
                    len(resp.content), url[:80],
                )
                raise ConnectionError(
                    f"下载文件过小: {len(resp.content)} bytes (可能防爬)"
                )

            logger.warning(
                "下载失败: status=%d size=%d", resp.status_code, len(resp.content)
            )
            return False

    @staticmethod
    def _transcribe_video(video_path: str, model: Any, max_retries: int = 2) -> str:
        """用 faster-whisper 转写视频中的语音"""
        for attempt in range(1, max_retries + 1):
            try:
                segments, info = model.transcribe(
                    video_path,
                    language="zh",
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                texts = [seg.text.strip() for seg in segments]
                result = "".join(texts)
                if result:
                    return result
                logger.warning("转写结果为空 (attempt %d)", attempt)
            except Exception as e:
                logger.error("转写失败 (attempt %d): %s", attempt, e)
            if attempt < max_retries:
                delay = 5 * attempt + random.uniform(0, 1)
                time.sleep(delay)
        return ""

    def _do_install_whisper(self) -> None:
        """安装 faster-whisper"""
        venv_python = self._get_venv_python()
        result = subprocess.run(
            [str(venv_python), "-c", "import faster_whisper; print('OK')"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            logger.info("faster-whisper 已安装")
            return

        subprocess.run(
            [str(venv_python), "-m", "pip", "install",
             "faster-whisper", "imageio-ffmpeg", "httpx"],
            check=True, timeout=300,
        )
