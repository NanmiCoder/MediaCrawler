import argparse
import logging
import config
from logging.handlers import RotatingFileHandler
from .crawler_util import *
from .slider_util import *
from .time_util import *

LOG_FILENAME = get_current_date() + ".log"
# 单个日志文件大小20M 
LOG_FILE_SIZE = 1024 * 1024 * 20

FORMAT_PATTERN = "%(asctime)s [%(threadName)s] %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s"

def init_loging_config():
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)

    # 是否输出日志到文件
    if (config.ENABLE_LOG_TO_FILE):
        handler = RotatingFileHandler(
            LOG_FILENAME, maxBytes=LOG_FILE_SIZE, backupCount=50, encoding="utf-8")
        formatter = logging.Formatter(FORMAT_PATTERN)
        handler.setFormatter(formatter)
        _logger.handlers.clear()
        _logger.addHandler(handler)
    # 是否开启控制台日志输出
    _logger.propagate = config.ENABLE_CONSOLE_LOG
    return _logger


logger = init_loging_config()

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
