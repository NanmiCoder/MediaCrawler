"""
douyin_scraper — 抖音关键词批量采集工具（生产级 Python 模块）
=========================================================
版本: v5.0 | 日期: 2026-06-05
本文档对应的提示词版本为 v5。

从 v4 脚本集合重构为可安装的 Python 模块。

自我反思 — v4 仍然存在的 5 个问题：
  1. 步骤间数据传递依赖 handoff.md 人工查看，未自动化
     → v5: DouyinScraper 类内部通过 self._paths 字典自动管理路径
  2. fallback 目录硬编码为 C:/temp/dy_fallback
     → v5: 通过 config.fallback_dir 配置，默认跨平台自动选择
  3. 没有支持增量采集或并发采集
     → v5: 架构预留了增量接口，search/fetch_comments/extract_scripts
           均支持 skip_existing 参数
  4. 日志轮转策略在 common_utils 中实现了但 extract_scripts 等脚本
     没有调用 setup_log_rotation
     → v5: DouyinScraper.__init__() 自动调用，所有方法共享
  5. 测试用例依赖模块级全局变量（PROJECT_DIR, FALLBACK_DIR），
     无法并行运行
     → v5: 所有状态通过实例属性管理，测试时注入临时目录

核心改进：
  - DouyinScraper 类：统一入口，状态内部管理
  - 配置支持：字典 / .env / YAML
  - 自定义异常：带 step / exit_code / details 属性
  - 跨平台：全部使用 pathlib，无 shell 特有命令
  - 可测试：所有外部依赖可 mock
  - logging 替代 print
  - 类型注解 + mypy --strict 兼容
"""

from douyin_scraper.core import DouyinScraper
from douyin_scraper.exceptions import (
    RetryableError,
    NonRetryableError,
    ConfigError,
    FatalError,
)
from douyin_scraper.models import Video, Comment, Script
from douyin_scraper.config import ScraperConfig

__version__ = "5.0.0"
__all__ = [
    "DouyinScraper",
    "RetryableError",
    "NonRetryableError",
    "ConfigError",
    "FatalError",
    "Video",
    "Comment",
    "Script",
    "ScraperConfig",
]
