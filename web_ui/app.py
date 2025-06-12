# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import config
import db
from main import CrawlerFactory

app = FastAPI()

templates = Jinja2Templates(directory="web_ui/templates")


def set_config(
    platform: str,
    login_type: str,
    crawler_type: str,
    keywords: str,
    start_page: int,
    cookies: str,
):
    config.PLATFORM = platform
    config.LOGIN_TYPE = login_type
    config.CRAWLER_TYPE = crawler_type
    config.KEYWORDS = keywords
    config.START_PAGE = start_page
    config.COOKIES = cookies


async def run_crawler():
    if config.SAVE_DATA_OPTION == "db":
        await db.init_db()
    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()
    if config.SAVE_DATA_OPTION == "db":
        await db.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/run", response_class=HTMLResponse)
async def run(
    request: Request,
    platform: str = Form(...),
    lt: str = Form(...),
    crawler_type: str = Form(...),
    keywords: str = Form(""),
    start: int = Form(1),
    cookies: str = Form(""),
):
    set_config(platform, lt, crawler_type, keywords, start, cookies)
    asyncio.create_task(run_crawler())
    message = "Crawler started"
    return templates.TemplateResponse("index.html", {"request": request, "message": message})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
