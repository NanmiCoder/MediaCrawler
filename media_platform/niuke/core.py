import re
import json
import httpx
import time
import requests
import json
import time
import re
from bs4 import BeautifulSoup 

import config
from base.base_crawler import AbstractCrawler
from tools import utils

categories = [
    '腾讯',
    '后台',
]

header = {
    "User-Agent": utils.get_user_agent(),
    "Content-Type": "application/json"
}

# 指定要过滤的词
skip_words = ['求捞', '泡池子', '池子了', '池子中', 'offer对比', '给个建议', '开奖群', '没消息', '有消息', '拉垮', '求一个', '求助', '池子的',
              '决赛圈', 'offer比较', '求捞', '补录面经', '捞捞', '收了我吧', 'offer选择', '有offer了', '想问一下', 'kpi吗', 'kpi面吗', 'kpi面吧']


class NiukeCrawler(AbstractCrawler):
    """Simple crawler for Niuke discussions"""

    def __init__(self) -> None:
        pass

    async def start(self):
        await self.search()

    async def search(self):
        items = []
        for keyword in config.KEYWORDS.split(","):
            for page in range(2, 4):
                data = {
                    "type": "all",
                    "query": keyword,
                    "page": page,
                    "tag": [],
                    "order": "create"
                }
                url = "https://gw-c.nowcoder.com/api/sparta/pc/search"
                utils.logger.info(f"[NiukeCrawler.search] url: {url} data: {data}")
                async with httpx.AsyncClient(headers=header) as client:
                    resp = await client.post(url, data=json.dumps(data))
                assert resp.status_code == 200

                data = json.loads(resp.text)
                items.extend(get_newcoder_page(data, skip_words, '2024'))

        utils.logger.info(f"[NiukeCrawler.search] items: {json.dumps(items, ensure_ascii=False)}")
        return items

    async def launch_browser(self, *args, **kwargs):
        raise NotImplementedError

def get_newcoder_content_page(discuss_id: int, header: dict) -> str:
    """
    根据帖子 ID 抓取 NowCoder 讨论区的**完整正文**。

    参数
    ----
    discuss_id : 帖子在网址中的数字 ID
    header     : 复用列表页的 UA 头，避免 403

    返回
    ----
    去掉标签后的纯文本正文；抓取失败则返回空字符串
    """
    url = f'https://www.nowcoder.com/discuss/{discuss_id}'
    try:
        resp = requests.get(url, headers=header, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 经验帖正文所在 div；若 NowCoder 后续改版，请相应调整选择器
        div = soup.select_one('div.nc-slate-editor-content')
        result = div.get_text('\n', strip=True) if div else ''
        return result
    except Exception as e:
        print(f'[warn] fetch detail failed ({discuss_id}):', e)
        return ''

def get_newcoder_page(data, skip_words, start_date):
    assert data['success'] == True
    pattern = re.compile("|".join(skip_words))
    res = []
    for x in data['data']['records']:
        x = x['data']
        if 'userBrief' not in x:
            continue 
        dic = {"user": x['userBrief']['nickname']}

        x = x['contentData'] if 'contentData' in x else x['momentData']
        dic['title'] = x['title']
        dic['content'] = x['content']
        dic['id'] = int(x['id'])
        if len(str(x['id'])) < 8:
            continue
        dic['url'] = 'https://www.nowcoder.com/discuss/' + str(x['id'])
        dic['categories'] = categories
        dic['is_analyzed'] = 0

        if len(skip_words) > 0 and pattern.search(x['title'] + x['content']) != None:  # 关键词正则过滤
            continue

        createdTime = x['createdAt'] if 'createdAt' in x else x['createTime']
        dic['createTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(createdTime // 1000))
        dic['editTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x['editTime'] // 1000))

        if dic['editTime'] < start_date:  # 根据时间过滤
            continue

        # 拉取完整正文；放在最后，避免给被过滤的帖子多做一次网络请求
        dic['detailed_content'] = get_newcoder_content_page(dic['id'], header=header)

        if dic['detailed_content'] == '': # 过滤掉没有完整正文的帖子
            continue

        res.append(dic)

    return res