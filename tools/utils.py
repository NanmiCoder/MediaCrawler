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
import re

from .crawler_util import *
from .slider_util import *
from .time_util import *


def init_loging_config():
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    _logger = logging.getLogger("MediaCrawler")
    _logger.setLevel(level)
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


def replaceT(text: str) -> str:
    """Make text safe for use as a Windows folder/file name.

    - Strips leading/trailing whitespace
    - Replaces illegal characters <>:"/\|?* and control chars with underscore
    - Collapses consecutive underscores
    - Avoids reserved device names (CON, PRN, AUX, NUL, COM1..COM9, LPT1..LPT9)
    - Returns 'default' if result becomes empty
    """
    if text is None:
        return "default"
    s = str(text).strip()
    # Replace illegal characters
    s = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', s)
    # Collapse multiple underscores
    s = re.sub(r'_+', '_', s)
    # Remove trailing dots or spaces (invalid for Windows file/folder names)
    s = s.rstrip(' .')
    # Reserved device names
    reserved = {
        'CON', 'PRN', 'AUX', 'NUL',
        *(f'COM{i}' for i in range(1, 10)),
        *(f'LPT{i}' for i in range(1, 10)),
    }
    if s.upper() in reserved or s == '':
        return "default"
    return s
