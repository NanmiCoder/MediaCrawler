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
import shutil
import subprocess
import sys
import tempfile
import threading
import time
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


    def fetch_comments(
        self,
        video_jsonl: Optional[Path] = None,
    ) -> Path:
        """
        对已有视频采集评论，返回评论 JSONL 路径。
        """
        step = self.STEP_COMMENTS
        self._require_step_ready(step)

        input_path = video_jsonl or self._paths.get("video_jsonl")
        if not input_path or not input_path.exists():
            raise NonRetryableError(
                f"视频 JSONL 不存在: {input_path}",
                step=step,
            )

        self._state.mark_step_started(step)
        try:
            output_path = self._do_fetch_comments(input_path)
            self._state.mark_step_completed(
                step, detail=f"output={output_path}"
            )
            self._paths["comments_jsonl"] = output_path
            return output_path
        except Exception as e:
            exit_code = classify_error(e)
            self._state.mark_step_failed(step, str(e)[:200], exit_code)
            raise

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

    def _do_fetch_comments(self, input_path: Path) -> Path:
        """
        对已有视频采集评论。
        v5: 内置评论采集逻辑，不再依赖外部脚本。
        """
        output_dir = self._config.jsonl_dir
        actual_dir = ensure_dir_writable(output_dir, self._config.fallback_dir)
        output_path = actual_dir / "search_comments.jsonl"

        # 读取视频列表
        videos = self._load_jsonl(input_path)
        video_ids = [str(v.get("aweme_id", "")) for v in videos if v.get("aweme_id")]

        # 断点续传
        done_ids = self._state.load_completed_ids_from_jsonl(output_path, "aweme_id")

        logger.info("视频 %d 个, 已完成评论 %d 个", len(video_ids), len(done_ids))

        # 这里只是占位：实际评论采集需要 Chrome CDP 交互
        # MediaCrawler 的 crawl_comments_v2.py 负责实际采集
        # v5 通过子进程调用
        venv_python = self._get_venv_python()
        comments_script = self._config.project_dir / "crawl_comments_v2.py"

        if comments_script.exists():
            logger.info("调用评论采集子进程: %s", comments_script)
            try:
                subprocess.run(
                    [str(venv_python), str(comments_script)],
                    cwd=str(self._config.project_dir),
                    check=True, timeout=3600,
                )
            except subprocess.CalledProcessError as exc:
                logger.error(
                    "评论采集子进程失败 (exit %d): %s",
                    exc.returncode, exc,
                )
                raise NonRetryableError(
                    f"评论采集子进程失败 (exit {exc.returncode}): {exc}",
                    step="fetch_comments",
                ) from exc

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
