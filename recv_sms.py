# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/recv_sms.py
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


import re
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

import config
from cache.abs_cache import AbstractCache
from cache.cache_factory import CacheFactory
from tools import utils

app = FastAPI()

cache_client : AbstractCache = CacheFactory.create_cache(cache_type=config.CACHE_TYPE_MEMORY)


class SmsNotification(BaseModel):
    platform: str
    current_number: str
    from_number: str
    sms_content: str
    timestamp: str


def extract_verification_code(message: str) -> str:
    """
    Extract verification code of 6 digits from the SMS.
    """
    pattern = re.compile(r'\b[0-9]{6}\b')
    codes: List[str] = pattern.findall(message)
    return codes[0] if codes else ""


@app.post("/")
def receive_sms_notification(sms: SmsNotification):
    """
    Receive SMS notification and send it to Redis.
    Args:
        sms:
            {
                "platform": "xhs",
                "from_number": "1069421xxx134",
                "sms_content": "【小红书】您的验证码是: 171959， 3分钟内有效。请勿向他人泄漏。如非本人操作，可忽略本消息。",
                "timestamp": "1686720601614",
                "current_number": "13152442222"
            }

    Returns:

    """
    utils.logger.info(f"Received SMS notification: {sms.platform}, {sms.current_number}")
    sms_code = extract_verification_code(sms.sms_content)
    if sms_code:
        # Save the verification code in Redis and set the expiration time to 3 minutes.
        key = f"{sms.platform}_{sms.current_number}"
        cache_client.set(key, sms_code, expire_time=60 * 3)

    return {"status": "ok"}


@app.get("/", status_code=status.HTTP_404_NOT_FOUND)
async def not_found():
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == '__main__':
    uvicorn.run(app, port=8000, host='0.0.0.0')
