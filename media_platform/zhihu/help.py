# -*- coding: utf-8 -*-
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

import execjs

from constant import zhihu as zhihu_constant
from model.m_zhihu import ZhihuComment, ZhihuContent, ZhihuCreator
from tools.crawler_util import extract_text_from_html

ZHIHU_SGIN_JS = None


def sign(url: str, cookies: str) -> Dict:
    """
    zhihu sign algorithm
    Args:
        url: request url with query string
        cookies: request cookies with d_c0 key

    Returns:

    """
    global ZHIHU_SGIN_JS
    if not ZHIHU_SGIN_JS:
        with open("libs/zhihu.js", "r") as f:
            ZHIHU_SGIN_JS = execjs.compile(f.read())

    return ZHIHU_SGIN_JS.call("get_sign", url, cookies)


class ZhiHuJsonExtractor:
    def __init__(self):
        pass

    def extract_contents(self, json_data: Dict) -> List[ZhihuContent]:
        """
        extract zhihu contents
        Args:
            json_data: zhihu json data

        Returns:

        """
        if not json_data:
            return []

        result: List[ZhihuContent] = []
        search_result: List[Dict] = json_data.get("data", [])
        search_result = [s_item for s_item in search_result if s_item.get("type") in ['search_result', 'zvideo']]
        for sr_item in search_result:
            sr_object: Dict = sr_item.get("object", {})
            if sr_object.get("type") == zhihu_constant.ANSWER_NAME:
                result.append(self._extract_answer_content(sr_object))
            elif sr_object.get("type") == zhihu_constant.ARTICLE_NAME:
                result.append(self._extract_article_content(sr_object))
            elif sr_object.get("type") == zhihu_constant.VIDEO_NAME:
                result.append(self._extract_zvideo_content(sr_object))
            else:
                continue

        return result

    def _extract_answer_content(self, answer: Dict) -> ZhihuContent:
        """
        extract zhihu answer content
        Args:
            answer: zhihu answer

        Returns:
        """
        res = ZhihuContent()
        res.content_id = answer.get("id")
        res.content_type = answer.get("type")
        res.content_text = extract_text_from_html(answer.get("content"))
        res.question_id = answer.get("question").get("id")
        res.content_url = f"{zhihu_constant.ZHIHU_URL}/question/{res.question_id}/answer/{res.content_id}"
        res.title = extract_text_from_html(answer.get("title"))
        res.desc = extract_text_from_html(answer.get("description"))
        res.created_time = answer.get("created_time")
        res.updated_time = answer.get("updated_time")
        res.voteup_count = answer.get("voteup_count")
        res.comment_count = answer.get("comment_count")

        # extract author info
        author_info = self._extract_author(answer.get("author"))
        res.user_id = author_info.user_id
        res.user_link = author_info.user_link
        res.user_nickname = author_info.user_nickname
        res.user_avatar = author_info.user_avatar
        return res

    def _extract_article_content(self, article: Dict) -> ZhihuContent:
        """
        extract zhihu article content
        Args:
            article: zhihu article

        Returns:

        """
        res = ZhihuContent()
        res.content_id = article.get("id")
        res.content_type = article.get("type")
        res.content_text = extract_text_from_html(article.get("content"))
        res.content_url = f"{zhihu_constant.ZHIHU_URL}/p/{res.content_id}"
        res.title = extract_text_from_html(article.get("title"))
        res.desc = extract_text_from_html(article.get("excerpt"))
        res.created_time = article.get("created_time")
        res.updated_time = article.get("updated_time")
        res.voteup_count = article.get("voteup_count")
        res.comment_count = article.get("comment_count")

        # extract author info
        author_info = self._extract_author(article.get("author"))
        res.user_id = author_info.user_id
        res.user_link = author_info.user_link
        res.user_nickname = author_info.user_nickname
        res.user_avatar = author_info.user_avatar
        return res

    def _extract_zvideo_content(self, zvideo: Dict) -> ZhihuContent:
        """
        extract zhihu zvideo content
        Args:
            zvideo:

        Returns:

        """
        res = ZhihuContent()
        res.content_id = zvideo.get("zvideo_id")
        res.content_type = zvideo.get("type")
        res.content_url = zvideo.get("video_url")
        res.title = extract_text_from_html(zvideo.get("title"))
        res.desc = extract_text_from_html(zvideo.get("description"))
        res.created_time = zvideo.get("created_at")
        res.voteup_count = zvideo.get("voteup_count")
        res.comment_count = zvideo.get("comment_count")

        # extract author info
        author_info = self._extract_author(zvideo.get("author"))
        res.user_id = author_info.user_id
        res.user_link = author_info.user_link
        res.user_nickname = author_info.user_nickname
        res.user_avatar = author_info.user_avatar
        return res

    @staticmethod
    def _extract_author(author: Dict) -> ZhihuCreator:
        """
        extract zhihu author
        Args:
            author:

        Returns:

        """
        res = ZhihuCreator()
        if not author:
            return res
        if not author.get("id"):
            author = author.get("member")
        res.user_id = author.get("id")
        res.user_link = f"{zhihu_constant.ZHIHU_URL}/people/{author.get('url_token')}"
        res.user_nickname = author.get("name")
        res.user_avatar = author.get("avatar_url")
        return res

    def extract_comments(self, page_content: ZhihuContent, comments: List[Dict]) -> List[ZhihuComment]:
        """
        extract zhihu comments
        Args:
            page_content: zhihu content object
            comments: zhihu comments

        Returns:

        """
        if not comments:
            return []
        res: List[ZhihuComment] = []
        for comment in comments:
            if comment.get("type") != "comment":
                continue
            res.append(self._extract_comment(page_content, comment))
        return res

    def _extract_comment(self, page_content: ZhihuContent, comment: Dict) -> ZhihuComment:
        """
        extract zhihu comment
        Args:
            page_content: comment with content object
            comment: zhihu comment

        Returns:

        """
        res = ZhihuComment()
        res.comment_id = str(comment.get("id", ""))
        res.parent_comment_id = comment.get("reply_comment_id")
        res.content = extract_text_from_html(comment.get("content"))
        res.publish_time = comment.get("created_time")
        res.ip_location = self._extract_comment_ip_location(comment.get("comment_tag", []))
        res.sub_comment_count = comment.get("child_comment_count")
        res.like_count = comment.get("like_count") if comment.get("like_count") else 0
        res.dislike_count = comment.get("dislike_count") if comment.get("dislike_count") else 0
        res.content_id = page_content.content_id
        res.content_type = page_content.content_type

        # extract author info
        author_info = self._extract_author(comment.get("author"))
        res.user_id = author_info.user_id
        res.user_link = author_info.user_link
        res.user_nickname = author_info.user_nickname
        res.user_avatar = author_info.user_avatar
        return res

    @staticmethod
    def _extract_comment_ip_location(comment_tags: List[Dict]) -> str:
        """
        extract comment ip location
        Args:
            comment_tags:

        Returns:

        """
        if not comment_tags:
            return ""

        for ct in comment_tags:
            if ct.get("type") == "ip_info":
                return ct.get("text")

        return ""

    @staticmethod
    def extract_offset(paging_info: Dict) -> str:
        """
        extract offset
        Args:
            paging_info:

        Returns:

        """
        # https://www.zhihu.com/api/v4/comment_v5/zvideos/1424368906836807681/root_comment?limit=10&offset=456770961_10125996085_0&order_by=score
        next_url = paging_info.get("next")
        if not next_url:
            return ""

        parsed_url = urlparse(next_url)
        query_params = parse_qs(parsed_url.query)
        offset = query_params.get('offset', [""])[0]
        return offset
