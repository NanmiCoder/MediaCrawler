# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/utils.py
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


import argparse
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from .crawler_util import *
from .slider_util import *
from .time_util import *


def init_loging_config():
    # 导入配置
    try:
        from config.base_config import LOG_SAVE_ENABLE, LOG_SAVE_PATH, LOG_SAVE_LEVEL
    except ImportError:
        LOG_SAVE_ENABLE = False
        LOG_SAVE_PATH = "./logs"
        LOG_SAVE_LEVEL = "INFO"
    
    level = logging.INFO
    log_format = "%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s"
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置基础日志
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format
    )
    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)

    # 如果启用日志保存，添加文件处理器
    if LOG_SAVE_ENABLE and LOG_SAVE_PATH:
        try:
            # 确保日志目录存在
            log_dir = os.path.abspath(LOG_SAVE_PATH)
            os.makedirs(log_dir, exist_ok=True)
            
            # 日志文件名：按日期命名
            log_filename = os.path.join(log_dir, f"mediacrawler-{datetime.now().strftime('%Y-%m-%d')}.log")
            
            # 转换日志级别字符串为logging级别
            file_level = getattr(logging, LOG_SAVE_LEVEL.upper(), logging.INFO)
            
            # 创建文件处理器
            file_handler = RotatingFileHandler(
                log_filename,
                encoding='utf-8'
            )
            file_handler.setLevel(file_level)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            
            # 添加到logger
            _logger.addHandler(file_handler)
            
        except Exception as e:
            # 如果文件日志配置失败，不影响控制台日志
            _logger.warning(f"日志文件保存配置失败: {e}")

    # Disable httpx INFO level logs
    logging.getLogger("httpx").setLevel(logging.WARNING)

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
