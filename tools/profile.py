# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Optional

import config


def get_browser_profile_dir(platform: Optional[str] = None, *, cdp: bool = False) -> str:
    """Return browser profile directory for the current crawler run."""
    if config.BROWSER_PROFILE_DIR:
        path = Path(config.BROWSER_PROFILE_DIR)
        return str(path if path.is_absolute() else Path(os.getcwd()) / path)

    platform_name = platform or config.PLATFORM
    dirname = config.USER_DATA_DIR % platform_name
    if cdp:
        dirname = f"cdp_{dirname}"
    return str(Path(os.getcwd()) / "browser_data" / dirname)
