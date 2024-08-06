# -*- coding: utf-8 -*-
import re
import json
import html
from typing import List, Dict, Tuple

from parsel import Selector

from model.m_baidu_tieba import TiebaNote, TiebaComment
from constant import baidu_tieba as const
from tools import utils


class TieBaExtractor:
    def __init__(self):
        pass

    @staticmethod
    def extract_search_note_list(page_content: str) -> List[TiebaNote]:
        """
        提取贴吧帖子列表，这里提取的关键词搜索结果页的数据，还缺少帖子的回复数和回复页等数据
        Args:
            page_content: 页面内容的HTML字符串

        Returns:
            包含帖子信息的字典列表
        """
        xpath_selector = "//div[@class='s_post']"
        post_list = Selector(text=page_content).xpath(xpath_selector)
        result: List[TiebaNote] = []
        for post in post_list:
            tieba_note = TiebaNote(
                note_id=post.xpath(".//span[@class='p_title']/a/@data-tid").get(default='').strip(),
                title=post.xpath(".//span[@class='p_title']/a/text()").get(default='').strip(),
                desc=post.xpath(".//div[@class='p_content']/text()").get(default='').strip(),
                note_url=const.TIEBA_URL + post.xpath(".//span[@class='p_title']/a/@href").get(default=''),
                user_nickname=post.xpath(".//a[starts-with(@href, '/home/main')]/font/text()").get(default='').strip(),
                user_link=const.TIEBA_URL + post.xpath(".//a[starts-with(@href, '/home/main')]/@href").get(default=''),
                tieba_name=post.xpath(".//a[@class='p_forum']/font/text()").get(default='').strip(),
                tieba_link=const.TIEBA_URL + post.xpath(".//a[@class='p_forum']/@href").get(default=''),
                publish_time=post.xpath(".//font[@class='p_green p_date']/text()").get(default='').strip(),
            )
            result.append(tieba_note)
        return result

    def extract_note_detail(self, page_content: str) -> TiebaNote:
        """
        提取贴吧帖子详情
        Args:
            page_content:

        Returns:

        """
        content_selector = Selector(text=page_content)
        first_floor_selector = content_selector.xpath("//div[@class='p_postlist'][1]")
        only_view_author_link = content_selector.xpath("//*[@id='lzonly_cntn']/@href").get(default='').strip()
        note_id = only_view_author_link.split("?")[0].split("/")[-1]
        # 帖子回复数、回复页数
        thread_num_infos = content_selector.xpath(
            "//div[@id='thread_theme_5']//li[@class='l_reply_num']//span[@class='red']"
        )
        # IP地理位置、发表时间
        other_info_content = content_selector.xpath(".//div[@class='post-tail-wrap']").get(default="").strip()
        ip_location, publish_time = self.extract_ip_and_pub_time(other_info_content)
        note = TiebaNote(
            note_id=note_id,
            title=content_selector.xpath("//title/text()").get(default='').strip(),
            desc=content_selector.xpath("//meta[@name='description']/@content").get(default='').strip(),
            note_url=const.TIEBA_URL + f"/p/{note_id}",
            user_link=const.TIEBA_URL + first_floor_selector.xpath(".//a[@class='p_author_face ']/@href").get(
                default='').strip(),
            user_nickname=first_floor_selector.xpath(".//a[@class='p_author_name j_user_card']/text()").get(
                default='').strip(),
            user_avatar=first_floor_selector.xpath(".//a[@class='p_author_face ']/img/@src").get(default='').strip(),
            tieba_name=content_selector.xpath("//a[@class='card_title_fname']/text()").get(default='').strip(),
            tieba_link=const.TIEBA_URL + content_selector.xpath("//a[@class='card_title_fname']/@href").get(default=''),
            ip_location=ip_location,
            publish_time=publish_time,
            total_replay_num=thread_num_infos[0].xpath("./text()").get(default='').strip(),
            total_replay_page=thread_num_infos[1].xpath("./text()").get(default='').strip(),
        )
        note.title = note.title.replace(f"【{note.tieba_name}】_百度贴吧", "")
        return note

    def extract_tieba_note_parment_comments(self, page_content: str, note_id: str) -> List[TiebaComment]:
        """
        提取贴吧帖子一级评论
        Args:
            page_content:
            note_id:

        Returns:

        """
        xpath_selector = "//div[@class='l_post l_post_bright j_l_post clearfix  ']"
        comment_list = Selector(text=page_content).xpath(xpath_selector)
        result: List[TiebaComment] = []
        for comment_selector in comment_list:
            comment_field_value: Dict = self.extract_data_field_value(comment_selector)
            if not comment_field_value:
                continue

            other_info_content = comment_selector.xpath(".//div[@class='post-tail-wrap']").get(default="").strip()
            ip_location, publish_time = self.extract_ip_and_pub_time(other_info_content)
            tieba_comment = TiebaComment(
                comment_id=str(comment_field_value.get("content").get("post_id")),
                sub_comment_count=comment_field_value.get("content").get("comment_num"),
                content=utils.extract_text_from_html(comment_field_value.get("content").get("content")),
                note_url=const.TIEBA_URL + f"/p/{note_id}",
                user_link=const.TIEBA_URL + comment_selector.xpath(".//a[@class='p_author_face ']/@href").get(default='').strip(),
                user_nickname=comment_selector.xpath(".//a[@class='p_author_name j_user_card']/text()").get(
                    default='').strip(),
                user_avatar=comment_selector.xpath(".//a[@class='p_author_face ']/img/@src").get(
                    default='').strip(),
                tieba_name=comment_selector.xpath("//a[@class='card_title_fname']/text()").get(default='').strip(),
                ip_location=ip_location,
                publish_time=publish_time,
                note_id=note_id,
            )
            result.append(tieba_comment)
        return result

    @staticmethod
    def extract_ip_and_pub_time(html_content: str) -> Tuple[str, str]:
        """
        提取IP位置和发布时间
        Args:
            html_content:

        Returns:

        """
        pattern_ip = re.compile(r'IP属地:(\S+)</span>')
        pattern_pub_time = re.compile(r'<span class="tail-info">(\d{4}-\d{2}-\d{2} \d{2}:\d{2})</span>')
        ip_match = pattern_ip.search(html_content)
        time_match = pattern_pub_time.search(html_content)
        ip = ip_match.group(1) if ip_match else ""
        pub_time = time_match.group(1) if time_match else ""
        return ip, pub_time

    @staticmethod
    def extract_data_field_value(selector: Selector) -> Dict:
        """
        提取data-field的值
        Args:
            selector:

        Returns:

        """
        data_field_value = selector.xpath("./@data-field").get(default='').strip()
        if not data_field_value or data_field_value == "{}":
            return {}
        try:
            # 先使用 html.unescape 处理转义字符 再json.loads 将 JSON 字符串转换为 Python 字典
            unescaped_json_str = html.unescape(data_field_value)
            data_field_dict_value = json.loads(unescaped_json_str)
        except Exception as ex:
            print(f"extract_data_field_value，错误信息：{ex}, 尝试使用其他方式解析")
            data_field_dict_value = {}
        return data_field_dict_value




def test_extract_search_note_list():
    with open("test_data/search_keyword_notes.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        result = extractor.extract_search_note_list(content)
        print(result)


def test_extract_note_detail():
    with open("test_data/note_detail.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        result = extractor.extract_note_detail(content)
        print(result.model_dump())

def test_extract_tieba_note_parment_comments():
    with open("test_data/note_comments.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        result = extractor.extract_tieba_note_parment_comments(content, "123456")
        print(result)

if __name__ == '__main__':
    # test_extract_search_note_list()
    # test_extract_note_detail()
    test_extract_tieba_note_parment_comments()
