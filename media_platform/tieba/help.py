# -*- coding: utf-8 -*-

from typing import List, Dict

from parsel import Selector


class TieBaExtractor:
    def __init__(self):
        pass

    @staticmethod
    def extract_search_note_list(page_content: str) -> List[Dict]:
        """
        提取贴吧帖子列表
        Args:
            page_content: 页面内容的HTML字符串

        Returns:
            包含帖子信息的字典列表
        """
        xpath_selector = "//div[@class='s_post']"
        post_list = Selector(text=page_content).xpath(xpath_selector)
        result = []
        for post in post_list:
            post_id = post.xpath(".//span[@class='p_title']/a/@data-tid").get(default='').strip()
            title = post.xpath(".//span[@class='p_title']/a/text()").get(default='').strip()
            link = post.xpath(".//span[@class='p_title']/a/@href").get(default='')
            description = post.xpath(".//div[@class='p_content']/text()").get(default='').strip()
            forum = post.xpath(".//a[@class='p_forum']/font/text()").get(default='').strip()
            forum_link = post.xpath(".//a[@class='p_forum']/@href").get(default='')
            author = post.xpath(".//a[starts-with(@href, '/home/main')]/font/text()").get(default='').strip()
            author_link = post.xpath(".//a[starts-with(@href, '/home/main')]/@href").get(default='')
            date = post.xpath(".//font[@class='p_green p_date']/text()").get(default='').strip()

            result.append({
                "note_id": post_id,
                "title": title,
                "desc": description,
                "note_url": link,
                "time": date,
                "tieba_name": forum,
                "tieba_link": forum_link,
                "nickname": author,
                "nickname_link": author_link,
            })

        return result

    @staticmethod
    def extract_tieba_note_comments(page_content: str) -> List[Dict]:
        """
        提取贴吧帖子评论
        Args:
            page_content:

        Returns:

        """
        pass


if __name__ == '__main__':
    with open("test_data/search_keyword_notes.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        _result = extractor.extract_search_note_list(content)
        print(_result)
        print(f"Total: {len(_result)}")
