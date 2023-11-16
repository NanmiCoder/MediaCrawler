import argparse
import asyncio
import sys

import config
import db
from base import proxy_account_pool
from media_platform.douyin import DouYinCrawler
from media_platform.xhs import XiaoHongShuCrawler
from fastapi import FastAPI, HTTPException, Request
import asyncio

app = FastAPI()


class CrawlerFactory:
    @staticmethod
    def create_crawler(platform: str):
        if platform == "xhs":
            return XiaoHongShuCrawler()
        elif platform == "dy":
            return DouYinCrawler()
        else:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy ...")


async def main():
    # define command line params ...
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs|dy)', choices=["xhs", "dy"],
                        default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)

    # init account pool
    account_pool = proxy_account_pool.create_account_pool()

    # init db
    if config.IS_SAVED_DATABASED:
        await db.init_db()

    args = parser.parse_args()
    crawler = CrawlerFactory.create_crawler(platform=args.platform)
    crawler.init_config(
        platform=args.platform,
        login_type=args.lt,
        account_pool=account_pool
    )
    await crawler.start()

# 修改 main 函数以接受参数


async def _main(platform: str, login_type: str):
    account_pool = proxy_account_pool.create_account_pool()

    if config.IS_SAVED_DATABASED:
        await db.init_db()

    crawler = CrawlerFactory.create_crawler(platform=platform)
    crawler.init_config(
        platform=platform,
        login_type=login_type,
        account_pool=account_pool
    )
    await crawler.start()


# 定义 API 路由
@app.post("/api/v1/search")
async def search(request: Request):
    body = await request.json()
    _ = body.get("user_id")
    _ = body.get("key_word")
    _ = body.get("desc")

    # 调用 main 函数
    platform = "xhs"  # 或从请求中获取
    login_type = "qrcode"  # 或从请求中获取
    await _main(platform, login_type)

    return {"message": "Crawler started"}

# 运行服务器
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# if __name__ == '__main__':
#     try:
#         # asyncio.run(main())
#         asyncio.get_event_loop().run_until_complete(main())
#     except KeyboardInterrupt:
#         sys.exit()

# TODO:
# 1. 先把main函数服务化，用api调用main
# 2. 实现传参，并且存下search的参数
# 3. 实现搜索结果回调
# 4. 实现qrcode发送手机(wx，邮件，telegram等)
