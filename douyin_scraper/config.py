"""
douyin_scraper.config — 配置管理
=================================
v5 新增：统一配置管理，支持字典 / .env 文件 / YAML。
我实际执行时：配置散落在 base_config.py、命令行参数、环境变量中，
无法集中管理和验证。
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from douyin_scraper.exceptions import ConfigError

# 跨平台默认 fallback 目录
if sys.platform == "win32":
    _DEFAULT_FALLBACK = "C:/temp/dy_fallback"
else:
    _DEFAULT_FALLBACK = "/tmp/dy_fallback"


class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 5.0
    backoff_factor: float = 3.0

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)


class ScraperConfig:
    """
    采集工具配置。

    支持三种初始化方式：
    1. 字典：ScraperConfig({"project_dir": "/path", "keywords": ["xxx"]})
    2. .env 文件路径：ScraperConfig("/path/to/.env")
    3. 默认值：ScraperConfig()

    我实际执行时：配置散落在各处，新机器部署时容易遗漏。
    v5：集中管理 + 验证 + 默认值。
    """

    def __init__(self, config: Optional[Union[str, Path, dict]] = None) -> None:
        # 默认值
        self.project_dir: Path = Path.cwd() / "douyin_scraper_workspace"
        self.keywords: List[str] = []
        self.max_videos_per_keyword: int = 20
        self.enable_comments: bool = True
        self.enable_cdp_mode: bool = True
        self.chrome_debugging_port: int = 9222
        self.ffmpeg_backend: str = "imageio-ffmpeg"  # or "system"
        self.retry: RetryConfig = RetryConfig()
        self.log_level: str = "INFO"
        self.fallback_dir: Path = Path(_DEFAULT_FALLBACK)
        self.state_dir_name: str = "state"
        self.whisper_model: str = "small"
        self.keep_videos: bool = False
        self.max_workers: int = 1

        # 加载配置
        if config is not None:
            self._load(config)

        # 环境变量覆盖（DOUYIN_SCRAPER_ 前缀）
        self._load_env_vars()

    def _load(self, config: Union[str, Path, dict]) -> None:
        """加载配置源"""
        if isinstance(config, dict):
            self._apply_dict(config)
        elif isinstance(config, (str, Path)):
            path = Path(config)
            if not path.exists():
                raise ConfigError(
                    f"配置文件不存在: {path}",
                    step="config",
                    details={"path": str(path)},
                )
            if path.suffix == ".env":
                self._load_dotenv(path)
            elif path.suffix in (".yaml", ".yml"):
                self._load_yaml(path)
            else:
                raise ConfigError(
                    f"不支持的配置文件格式: {path.suffix}",
                    step="config",
                    details={"path": str(path)},
                )

    def _apply_dict(self, data: dict) -> None:
        """应用字典配置"""
        if "project_dir" in data:
            self.project_dir = Path(data["project_dir"])
        if "keywords" in data:
            self.keywords = list(data["keywords"])
        if "max_videos_per_keyword" in data:
            try:
                self.max_videos_per_keyword = int(data["max_videos_per_keyword"])
            except (ValueError, TypeError) as e:
                raise ConfigError(
                    f"max_videos_per_keyword 必须是整数: {data.get('max_videos_per_keyword')}",
                    step="config",
                ) from e
        if "enable_comments" in data:
            self.enable_comments = bool(data["enable_comments"])
        if "enable_cdp_mode" in data:
            self.enable_cdp_mode = bool(data["enable_cdp_mode"])
        if "chrome_debugging_port" in data:
            try:
                self.chrome_debugging_port = int(data["chrome_debugging_port"])
            except (ValueError, TypeError) as e:
                raise ConfigError(
                    f"chrome_debugging_port 必须是整数: {data.get('chrome_debugging_port')}",
                    step="config",
                ) from e
        if "ffmpeg_backend" in data:
            self.ffmpeg_backend = str(data["ffmpeg_backend"])
        if "log_level" in data:
            self.log_level = str(data["log_level"])
        if "fallback_dir" in data:
            self.fallback_dir = Path(data["fallback_dir"])
        if "whisper_model" in data:
            self.whisper_model = str(data["whisper_model"])
        if "keep_videos" in data:
            self.keep_videos = bool(data["keep_videos"])
        if "max_workers" in data:
            try:
                self.max_workers = int(data["max_workers"])
            except (ValueError, TypeError) as e:
                raise ConfigError(
                    f"max_workers 必须是整数: {data.get('max_workers')}",
                    step="config",
                ) from e
        if "state_dir_name" in data:
            self.state_dir_name = str(data["state_dir_name"])
        if "retry" in data:
            self.retry = RetryConfig(**data["retry"])

    def _load_dotenv(self, path: Path) -> None:
        """
        加载 .env 文件。
        格式：KEY=VALUE，支持 DOUYIN_SCRAPER_ 前缀。
        """
        data: Dict[str, Any] = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                data[key] = value
        self._apply_dict(data)

    def _load_yaml(self, path: Path) -> None:
        """加载 YAML 配置文件（需要 PyYAML）"""
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            raise ConfigError(
                "PyYAML 未安装，请执行: pip install pyyaml",
                step="config",
            )
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._apply_dict(data)

    def _load_env_vars(self) -> None:
        """从环境变量加载配置（DOUYIN_SCRAPER_ 前缀）"""
        prefix = "DOUYIN_SCRAPER_"
        mapping: Dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                clean_key = key[len(prefix):].lower()
                mapping[clean_key] = value

        if mapping:
            self._apply_dict(mapping)

    @property
    def state_dir(self) -> Path:
        return self.project_dir / self.state_dir_name

    @property
    def data_dir(self) -> Path:
        return self.project_dir / "data" / "douyin"

    @property
    def jsonl_dir(self) -> Path:
        return self.data_dir / "jsonl"

    @property
    def video_dir(self) -> Path:
        return self.data_dir / "downloaded_videos"

    def validate(self) -> None:
        """
        验证配置完整性。
        我实际执行时：配置错误到运行时才发现（如没有关键词就执行搜索）。
        """
        errors: List[str] = []
        if self.project_dir is None or not str(self.project_dir).strip():
            errors.append("project_dir 未设置")
        if self.ffmpeg_backend not in ("imageio-ffmpeg", "system"):
            errors.append(f"不支持的 ffmpeg_backend: {self.ffmpeg_backend}")
        if self.chrome_debugging_port < 1 or self.chrome_debugging_port > 65535:
            errors.append(f"无效端口: {self.chrome_debugging_port}")
        if self.retry.max_attempts < 1:
            errors.append("retry.max_attempts 必须 >= 1")
        if self.max_videos_per_keyword < 1:
            errors.append(f"max_videos_per_keyword 必须 >= 1, 当前: {self.max_videos_per_keyword}")
        if not isinstance(self.keywords, list):
            errors.append(f"keywords 必须是列表, 当前类型: {type(self.keywords).__name__}")
        elif self.keywords:
            empty_keywords = [k for k in self.keywords if not k.strip()]
            if empty_keywords:
                errors.append(f"keywords 包含 {len(empty_keywords)} 个空字符串")
        if self.whisper_model not in ("tiny", "base", "small", "medium", "large"):
            errors.append(f"不支持的 whisper_model: {self.whisper_model}")
        if errors:
            raise ConfigError(
                "配置验证失败: " + "; ".join(errors),
                step="config",
                details={"errors": errors},
            )
