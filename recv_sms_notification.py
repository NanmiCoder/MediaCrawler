# Start an HTTP server to receive SMS forwarding notifications and store them in Redis.
import asyncio
import json
import re
from typing import List

import redis
import tornado.web

import config


def extract_verification_code(message) -> str:
    """
    Extract verification code of 6 digits from the SMS.
    """
    pattern = re.compile(r'\b[0-9]{6}\b')
    codes: List[str] = pattern.findall(message)
    return codes[0] if codes and len(codes) > 0 else ""


class RecvSmsNotificationHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_status(404)
        self.write("404")

    async def post(self):
        # GitHub address for the SMS forwarding function：https://github.com/pppscn/SmsForwarder
        # Document address:：https://gitee.com/pp/SmsForwarder/wikis/pages?sort_id=6040999&doc_id=1821427
        # Forwarding channel definition：
        # {
        #     "platform": "xhs",
        #     "current_number": "138xxxxxxxx",
        #     "from_number": "[from]",
        #     "sms_content": "[org_content]",
        #     "timestamp": "[timestamp]"
        # }

        # SMS message body：
        # {
        #    'platform': 'xhs', # or dy
        #    'current_number': '138xxxxxxxx',
        #    'from_number': '1069421xxx134',
        #    'sms_content': '【小红书】您的验证码是: 171959， 3分钟内有效。请勿向他人泄漏。如非本人操作，可忽略本消息。',
        #    'timestamp': '1686720601614'
        # }
        request_body = self.request.body.decode("utf-8")
        req_body_dict = json.loads(request_body)
        print("recv sms notification and body content: ", req_body_dict)
        redis_obj = redis.Redis(host=config.REDIS_DB_HOST, password=config.REDIS_DB_PWD)
        sms_content = req_body_dict.get("sms_content")
        sms_code = extract_verification_code(sms_content)
        if sms_code:
            # Save the verification code in Redis and set the expiration time to 3 minutes.
            # Use Redis string data structure, in the following format:
            # xhs_138xxxxxxxx -> 171959
            key = f"{req_body_dict.get('platform')}_{req_body_dict.get('current_number')}"
            redis_obj.set(name=key, value=sms_code, ex=60 * 3)
        self.set_status(200)
        self.write("ok")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r'/', RecvSmsNotificationHandler)]
        settings = dict(
            gzip=True,
            autoescape=None,
            autoreload=True
        )
        super(Application, self).__init__(handlers, **settings)


async def main():
    app = Application()
    app.listen(port=9435)
    print("Recv sms notification app running ...")
    shutdown_event = tornado.locks.Event()
    await shutdown_event.wait()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
