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
    def extract_note_detail(page_content: str) -> Dict:
        """
        提取贴吧帖子详情
        Args:
            page_content:

        Returns:

        """
        content_selector = Selector(text=page_content)
        # 查看楼主的链接： only_view_author_link: / p / 9117905169?see_lz = 1
        only_view_author_link = content_selector.xpath("//*[@id='lzonly_cntn']/@href").get(default='').strip() #
        note_id = only_view_author_link.split("?")[0].split("/")[-1]
        title = content_selector.xpath("//*[@id='j_core_title_wrap']/h3").get(default='').strip()
        desc = content_selector.xpath("//meta[@name='description']").get(default='').strip()
        note_url = f"/p/{note_id}"
        pass

    @staticmethod
    def extract_tieba_note_comments(page_content: str) -> List[Dict]:
        """
        提取贴吧帖子评论
        Args:
            page_content:

        Returns:

        """
        xpath_selector = "//div[@id='j_p_postlist']/div[@class='l_post l_post_bright j_l_post clearfix']"
        comment_list = Selector(text=page_content).xpath(xpath_selector)
        result = []
        for comment in comment_list:
            comment_id = comment.xpath(".//@data-pid").get(default='').strip()
            author = comment.xpath(".//a[@data-field]/text()").get(default='').strip()
            author_link = comment.xpath(".//a[@data-field]/@href").get(default='')
            content = comment.xpath(".//div[@class='d_post_content j_d_post_content ']/text()").get(default='').strip()
            date = comment.xpath(".//span[@class='tail-info']/text()").get(default='').strip()

            result.append({
                "comment_id": comment_id,
                "author": author,
                "author_link": author_link,
                "content": content,
                "time": date,
            })



if __name__ == '__main__':
    with open("test_data/search_keyword_notes.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        _result = extractor.extract_search_note_list(content)
        print(_result)
        print(f"Total: {len(_result)}")
