import re
from typing import List

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

import config
from tools import utils

app = FastAPI()

redis_client = redis.Redis(host=config.REDIS_DB_HOST, password=config.REDIS_DB_PWD)


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
        redis_client.set(key, sms_code, ex=60 * 3)

    return {"status": "ok"}


@app.get("/", status_code=status.HTTP_404_NOT_FOUND)
async def not_found():
    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == '__main__':
    uvicorn.run(app, port=8000, host='0.0.0.0')