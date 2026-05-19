# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tieba/help.py
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


# -*- coding: utf-8 -*-
import html
import json
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, quote, unquote, urljoin

from parsel import Selector

from constant import baidu_tieba as const
from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from tools import utils

GENDER_MALE = "sex_male"
GENDER_FEMALE = "sex_female"


class TieBaExtractor:
    def __init__(self):
        pass

    @staticmethod
    def _class_contains(class_name: str) -> str:
        return f"contains(concat(' ', normalize-space(@class), ' '), ' {class_name} ')"

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @classmethod
    def _selector_text(cls, selector: Selector, xpath: str) -> str:
        node = selector.xpath(xpath)
        if not node:
            return ""
        return cls._normalize_text(node[0].xpath("string(.)").get(default=""))

    @staticmethod
    def _absolute_url(url: str) -> str:
        return urljoin(const.TIEBA_URL, (url or "").strip())

    @staticmethod
    def _extract_note_id_from_url(url: str) -> str:
        note_id_match = re.search(r"/p/(\d+)", url or "")
        return note_id_match.group(1) if note_id_match else ""

    @staticmethod
    def _text_to_int(text: str) -> int:
        match = re.search(r"\d+", text or "")
        return int(match.group(0)) if match else 0

    @staticmethod
    def _ensure_tieba_suffix(tieba_name: str) -> str:
        tieba_name = (tieba_name or "").strip()
        return tieba_name if not tieba_name or tieba_name.endswith("吧") else f"{tieba_name}吧"

    @classmethod
    def _tieba_link_from_name(cls, tieba_name: str) -> str:
        if not tieba_name:
            return const.TIEBA_URL
        return f"{const.TIEBA_URL}/f?kw={quote(tieba_name.removesuffix('吧'))}"

    @classmethod
    def _extract_api_content_text(cls, content: Any) -> str:
        if isinstance(content, str):
            return cls._normalize_text(content)
        if not isinstance(content, list):
            return ""
        text_list: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("c") or ""
            if text:
                text_list.append(str(text))
        return cls._normalize_text("".join(text_list))

    @staticmethod
    def _api_user_map(api_data: Dict) -> Dict[str, Dict]:
        return {str(user.get("id")): user for user in api_data.get("user_list", []) if user.get("id")}

    @staticmethod
    def _api_user_link(user: Dict) -> str:
        portrait = (user or {}).get("portrait", "")
        if not portrait:
            return ""
        return f"{const.TIEBA_URL}/home/main?id={quote(str(portrait))}"

    @staticmethod
    def _api_user_avatar(user: Dict) -> str:
        image_data = (
            (user or {})
            .get("user_show_info", {})
            .get("feed_head", {})
            .get("image_data", {})
        )
        return image_data.get("img_url") or (
            "https://gss0.bdstatic.com/6LZ1dD3d1sgCo2Kml5_Y_D3/sys/portrait/item/"
            f"{user.get('portrait', '')}"
            if user and user.get("portrait")
            else ""
        )

    def extract_search_note_list_from_api(self, api_data: Dict) -> List[TiebaNote]:
        """
        Extract Tieba post list from current PC search JSON API.
        """
        result: List[TiebaNote] = []
        cards = api_data.get("data", {}).get("card_list", [])
        for card in cards:
            if card.get("cardInfo") != "thread" and card.get("cardStyle") != "thread":
                continue
            item = card.get("data") or {}
            note_id = str(item.get("tid") or "")
            if not note_id:
                continue
            user = item.get("user") or {}
            tieba_name = self._ensure_tieba_suffix(item.get("forum_name") or "")
            tieba_note = TiebaNote(
                note_id=note_id,
                title=self._normalize_text(item.get("title") or ""),
                desc=self._normalize_text(item.get("content") or ""),
                note_url=f"{const.TIEBA_URL}/p/{note_id}",
                publish_time=utils.get_time_str_from_unix_time(
                    item.get("time") or item.get("create_time") or 0
                ),
                user_link="",
                user_nickname=user.get("show_nickname") or user.get("user_name") or "",
                user_avatar=user.get("portrait") or user.get("portraith") or "",
                tieba_name=tieba_name,
                tieba_link=self._tieba_link_from_name(tieba_name),
                total_replay_num=item.get("post_num") or 0,
            )
            result.append(tieba_note)
        return result

    def extract_note_detail_from_api(self, api_data: Dict) -> TiebaNote:
        """
        Extract Tieba post detail from current PC page_pc JSON API.
        """
        thread = api_data.get("thread") or {}
        first_floor = api_data.get("first_floor") or {}
        forum = api_data.get("forum") or api_data.get("display_forum") or {}
        page = api_data.get("page") or {}
        user_map = self._api_user_map(api_data)
        author = user_map.get(str(first_floor.get("author_id"))) or {}
        note_id = str(thread.get("id") or thread.get("tid") or first_floor.get("tid") or "")
        tieba_name = self._ensure_tieba_suffix(forum.get("name") or "")
        note = TiebaNote(
            note_id=note_id,
            title=self._clean_title(thread.get("title") or first_floor.get("title") or "", tieba_name),
            desc=self._extract_api_content_text(
                first_floor.get("content")
                or thread.get("origin_thread_info", {}).get("abstract")
                or thread.get("origin_thread_info", {}).get("content")
            ),
            note_url=f"{const.TIEBA_URL}/p/{note_id}",
            publish_time=utils.get_time_str_from_unix_time(
                first_floor.get("time") or thread.get("create_time") or 0
            ),
            user_link=self._api_user_link(author),
            user_nickname=author.get("name_show") or author.get("name") or "",
            user_avatar=self._api_user_avatar(author),
            tieba_name=tieba_name,
            tieba_link=self._tieba_link_from_name(tieba_name),
            total_replay_num=thread.get("reply_num") or 0,
            total_replay_page=page.get("total_page") or 0,
            ip_location=author.get("ip_address") or "",
        )
        return note

    def extract_tieba_note_parent_comments_from_api(
        self, api_data: Dict, note_detail: TiebaNote
    ) -> List[TiebaComment]:
        """
        Extract first-level comments from current PC page_pc JSON API.
        """
        forum = api_data.get("forum") or api_data.get("display_forum") or {}
        tieba_id = str(forum.get("id") or "")
        tieba_name = note_detail.tieba_name or self._ensure_tieba_suffix(forum.get("name") or "")
        tieba_link = note_detail.tieba_link or self._tieba_link_from_name(tieba_name)
        user_map = self._api_user_map(api_data)
        result: List[TiebaComment] = []
        for item in api_data.get("post_list", []):
            comment_id = str(item.get("id") or "")
            if not comment_id:
                continue
            user = user_map.get(str(item.get("author_id"))) or {}
            comment = TiebaComment(
                comment_id=comment_id,
                sub_comment_count=item.get("sub_post_number") or 0,
                content=self._extract_api_content_text(item.get("content")),
                note_url=note_detail.note_url,
                user_link=self._api_user_link(user),
                user_nickname=user.get("name_show") or user.get("name") or "",
                user_avatar=self._api_user_avatar(user),
                tieba_id=tieba_id,
                tieba_name=tieba_name,
                tieba_link=tieba_link,
                ip_location=user.get("ip_address") or "",
                publish_time=utils.get_time_str_from_unix_time(item.get("time") or 0),
                note_id=note_detail.note_id,
            )
            result.append(comment)
        return result

    def extract_creator_info_from_api(self, api_data: Dict) -> TiebaCreator:
        """
        Extract Tieba creator information from current PC creator JSON API.
        """
        user = api_data.get("data", {}).get("user", {})
        if not user:
            raise ValueError(f"Creator API response does not contain user info: {api_data}")
        gender_value = user.get("sex", user.get("gender", 0))
        gender = "Unknown"
        if gender_value == 1:
            gender = "Male"
        elif gender_value == 2:
            gender = "Female"

        return TiebaCreator(
            user_id=str(user.get("id", "")),
            user_name=str(user.get("name", "")),
            nickname=str(user.get("name_show") or user.get("name") or ""),
            avatar=self._api_user_avatar(user),
            gender=gender,
            ip_location=str(user.get("ip_address", "")),
            follows=int(user.get("concern_num") or 0),
            fans=int(user.get("fans_num") or 0),
            registration_duration=str(user.get("tb_age", "")),
        )

    @staticmethod
    def extract_creator_thread_id_list_from_api(api_data: Dict) -> List[str]:
        """
        Extract creator thread ids from current PC creator feed JSON API.
        """
        thread_ids: List[str] = []
        for item in api_data.get("data", {}).get("list", []):
            thread_info = item.get("thread_info") or {}
            thread_id = thread_info.get("tid") or thread_info.get("id")
            if thread_id:
                thread_ids.append(str(thread_id))
        return thread_ids

    def extract_tieba_note_list_from_frs_api(self, api_data: Dict) -> List[TiebaNote]:
        """
        Extract Tieba thread ids from current PC forum page JSON API.

        The by-forum command immediately fetches full details for every id, so
        this list intentionally carries only stable routing fields.
        """
        forum = api_data.get("forum", {})
        tieba_name = self._ensure_tieba_suffix(forum.get("name") or "")
        tieba_link = self._tieba_link_from_name(tieba_name)
        tids = [
            tid.strip()
            for tid in str(forum.get("tids") or "").split(",")
            if tid.strip()
        ]
        return [
            TiebaNote(
                note_id=tid,
                title="",
                desc="",
                note_url=f"{const.TIEBA_URL}/p/{tid}",
                tieba_name=tieba_name,
                tieba_link=tieba_link,
            )
            for tid in tids
        ]

    @staticmethod
    def _decode_js_string(value: str) -> str:
        if not value or value == "null":
            return ""
        try:
            decoded_value = json.loads(f'"{value}"')
            return decoded_value if isinstance(decoded_value, str) else str(decoded_value)
        except Exception:
            return value

    @classmethod
    def _extract_forum_info(cls, selector: Selector, page_content: str) -> Tuple[str, str]:
        forum_xpath = f"//a[{cls._class_contains('card_title_fname')}]"
        forum_link_selector = selector.xpath(forum_xpath)
        tieba_name = cls._selector_text(selector, forum_xpath)
        tieba_link = cls._absolute_url(forum_link_selector.xpath("./@href").get(default=""))

        if not tieba_name:
            patterns = [
                r"PageData\.forum\s*=\s*\{.*?['\"]name['\"]\s*:\s*\"([^\"\\\\]*(?:\\\\.[^\"\\\\]*)*)\"",
                r'"forum_name"\s*:\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"',
                r'"kw"\s*:\s*"([^"\\\\]*(?:\\\\.[^"\\\\]*)*)"',
            ]
            for pattern in patterns:
                match = re.search(pattern, page_content, re.S)
                if match:
                    tieba_name = cls._decode_js_string(match.group(1))
                    if tieba_name:
                        break

        if not tieba_name:
            title = selector.xpath("//title/text()").get(default="")
            match = re.search(r"(.+?)吧[-_]", title)
            if match:
                tieba_name = cls._normalize_text(match.group(1))

        if not tieba_link and tieba_name:
            tieba_link = f"{const.TIEBA_URL}/f?kw={quote(tieba_name.removesuffix('吧'))}"

        return tieba_name, tieba_link or const.TIEBA_URL

    @classmethod
    def _clean_title(cls, title: str, tieba_name: str = "") -> str:
        title = cls._normalize_text(title)
        title = re.sub(r"_(?:百度贴吧|Baidu Tieba)$", "", title).strip()
        for name in {tieba_name, tieba_name.removesuffix("吧")}:
            if name:
                title = title.replace(f"【{name}】", "").strip()
        return title

    @staticmethod
    def extract_search_note_list(page_content: str) -> List[TiebaNote]:
        """
        Extract Tieba post list from keyword search result pages, still missing reply count and reply page data
        Args:
            page_content: HTML string of page content

        Returns:
            List of Tieba post objects
        """
        extractor = TieBaExtractor()
        selector = Selector(text=page_content)
        post_list = selector.xpath(
            f"//div[{extractor._class_contains('s_post')}]"
        )
        result: List[TiebaNote] = []
        for post in post_list:
            title_link = post.xpath(".//*[contains(@class, 'p_title')]//a[1]")
            note_url = extractor._absolute_url(title_link.xpath("./@href").get(default=""))
            note_id = title_link.xpath("./@data-tid").get(default="").strip()
            if not note_id:
                note_id = extractor._extract_note_id_from_url(note_url)
            user_selector = post.xpath(".//a[contains(@href, '/home/main')][1]")
            forum_selector = post.xpath(f".//a[{extractor._class_contains('p_forum')}][1]")
            tieba_note = TiebaNote(
                note_id=note_id,
                title=extractor._selector_text(post, ".//*[contains(@class, 'p_title')]//a[1]"),
                desc=extractor._selector_text(
                    post, f".//div[{extractor._class_contains('p_content')}]"
                ),
                note_url=note_url,
                user_nickname=extractor._selector_text(
                    post, ".//a[contains(@href, '/home/main')][1]"
                ),
                user_link=extractor._absolute_url(user_selector.xpath("./@href").get(default="")),
                tieba_name=extractor._selector_text(
                    post, f".//a[{extractor._class_contains('p_forum')}][1]"
                ),
                tieba_link=extractor._absolute_url(forum_selector.xpath("./@href").get(default="")),
                publish_time=extractor._selector_text(
                    post, ".//*[contains(@class, 'p_date')][1]"
                ),
            )
            result.append(tieba_note)
        if result:
            return result

        # Tieba search changed to a PC feed/card layout in 2026. The old
        # s_post nodes disappeared, while each search result now lives in a
        # threadcardclass card with overlay links to /p/<thread_id>.
        post_list = selector.xpath(
            f"//*[contains(concat(' ', normalize-space(@class), ' '), ' threadcardclass ') "
            f"and .//a[contains(@href, '/p/')]]"
        )
        seen_note_ids = set()
        for post in post_list:
            title_link = post.xpath(
                f".//a[{extractor._class_contains('action-link-bg')} and contains(@href, '/p/')][1]"
                f"|.//a[contains(@href, '/p/')][1]"
            )
            note_url = extractor._absolute_url(title_link.xpath("./@href").get(default=""))
            note_id = extractor._extract_note_id_from_url(note_url)
            if not note_id or note_id in seen_note_ids:
                continue
            seen_note_ids.add(note_id)

            tieba_name = extractor._selector_text(
                post, f".//*[{extractor._class_contains('forum-name-text')}][1]"
            )
            tieba_link = ""
            forum_link = post.xpath(".//a[contains(@href, '/f?')][1]/@href").get(default="")
            if forum_link:
                tieba_link = extractor._absolute_url(forum_link)
            elif tieba_name:
                tieba_keyword = tieba_name.removesuffix("吧")
                tieba_link = f"{const.TIEBA_URL}/f?kw={quote(tieba_keyword)}"
            else:
                tieba_link = const.TIEBA_URL

            publish_time = ""
            top_title_text = extractor._selector_text(
                post, f".//*[{extractor._class_contains('top-title')}][1]"
            )
            publish_match = re.search(r"发布于\s*([^\s]+)", top_title_text)
            if publish_match:
                publish_time = publish_match.group(1)

            title = extractor._selector_text(
                post, f".//*[{extractor._class_contains('title-wrap')}][1]"
            )
            desc = extractor._selector_text(
                post, f".//*[{extractor._class_contains('abstract-wrap')}][1]"
            )
            if not title:
                title = extractor._normalize_text(desc[:80])

            user_nickname = extractor._selector_text(
                post, f".//*[{extractor._class_contains('forum-attention')}][1]"
            )
            if not user_nickname and publish_time:
                user_nickname = extractor._normalize_text(
                    top_title_text.split("发布于", 1)[0]
                )

            comment_text = extractor._selector_text(
                post, f".//a[{extractor._class_contains('comment-link-zone')}][1]"
            )
            tieba_note = TiebaNote(
                note_id=note_id,
                title=title,
                desc=desc,
                note_url=f"{const.TIEBA_URL}/p/{note_id}",
                user_nickname=user_nickname,
                user_link="",
                tieba_name=tieba_name,
                tieba_link=tieba_link,
                publish_time=publish_time,
                total_replay_num=extractor._text_to_int(comment_text),
            )
            result.append(tieba_note)
        return result

    def extract_tieba_note_list(self, page_content: str) -> List[TiebaNote]:
        """
        Extract Tieba post list from Tieba page
        Args:
            page_content: HTML string of page content

        Returns:
            List of Tieba post objects
        """
        page_content = page_content.replace('<!--', "")
        content_selector = Selector(text=page_content)
        xpath_selector = f"//ul[@id='thread_list']/li[{self._class_contains('j_thread_list')}]"
        post_list = content_selector.xpath(xpath_selector)
        tieba_name, tieba_link = self._extract_forum_info(content_selector, page_content)
        result: List[TiebaNote] = []
        for post_selector in post_list:
            post_field_value: Dict = self.extract_data_field_value(post_selector)
            if not post_field_value:
                continue
            note_id = str(post_field_value.get("id"))
            user_selector = post_selector.xpath(f".//a[{self._class_contains('frs-author-name')}][1]")
            title = self._selector_text(post_selector, f".//a[{self._class_contains('j_th_tit')}][1]")
            if not title:
                title = self._selector_text(post_selector, f".//*[{self._class_contains('threadlist_title')}]//a[1]")
            user_nickname = (
                post_field_value.get("author_nickname")
                or post_field_value.get("author_name")
                or self._selector_text(
                    post_selector, f".//a[{self._class_contains('frs-author-name')}][1]"
                )
            )
            tieba_note = TiebaNote(
                note_id=note_id,
                title=title,
                desc=self._selector_text(
                    post_selector, f".//div[{self._class_contains('threadlist_abs')}]"
                ),
                note_url=const.TIEBA_URL + f"/p/{note_id}",
                user_link=self._absolute_url(user_selector.xpath("./@href").get(default="")),
                user_nickname=user_nickname,
                tieba_name=tieba_name,
                tieba_link=tieba_link,
                total_replay_num=post_field_value.get("reply_num", 0),
            )
            result.append(tieba_note)
        return result

    def extract_note_detail(self, page_content: str) -> TiebaNote:
        """
        Extract Tieba post details from post detail page
        Args:
            page_content: HTML string of page content

        Returns:
            Tieba post detail object
        """
        content_selector = Selector(text=page_content)
        first_floor_selector = content_selector.xpath(
            f"//div[{self._class_contains('l_post')} and {self._class_contains('j_l_post')}][1]"
        )
        only_view_author_link = content_selector.xpath("//*[@id='lzonly_cntn']/@href").get(default='').strip()
        note_id = only_view_author_link.split("?")[0].split("/")[-1]
        if not note_id:
            note_id_match = re.search(r'"thread_id"\s*:\s*"?(\d+)"?', page_content)
            note_id = note_id_match.group(1) if note_id_match else ""
        # Post reply count and reply page count
        thread_num_infos = content_selector.xpath(
            f"//div[@id='thread_theme_5']//li[{self._class_contains('l_reply_num')}]"
            f"//span[{self._class_contains('red')}]"
        )
        # IP location and publish time
        other_info_content = first_floor_selector.xpath(
            f".//div[{self._class_contains('post-tail-wrap')}]"
        ).get(default="").strip()
        ip_location, publish_time = self.extract_ip_and_pub_time(other_info_content)
        tieba_name, tieba_link = self._extract_forum_info(content_selector, page_content)
        first_floor_value = self.extract_data_field_value(first_floor_selector)
        author_value = first_floor_value.get("author", {}) if first_floor_value else {}
        author_link = first_floor_selector.xpath(
            f".//a[{self._class_contains('p_author_face')} "
            f"or {self._class_contains('p_author_name')}]/@href"
        ).get(default="")
        note = TiebaNote(
            note_id=note_id,
            title=content_selector.xpath("//title/text()").get(default="").strip(),
            desc=content_selector.xpath("//meta[@name='description']/@content").get(default="").strip(),
            note_url=const.TIEBA_URL + f"/p/{note_id}",
            user_link=self._absolute_url(author_link),
            user_nickname=(
                self._selector_text(first_floor_selector, f".//a[{self._class_contains('p_author_name')}][1]")
                or author_value.get("user_nickname")
                or author_value.get("user_name", "")
            ),
            user_avatar=first_floor_selector.xpath(
                f".//a[{self._class_contains('p_author_face')}]//img/@src"
            ).get(default="").strip(),
            tieba_name=tieba_name,
            tieba_link=tieba_link,
            ip_location=ip_location,
            publish_time=publish_time,
            total_replay_num=(
                thread_num_infos[0].xpath("./text()").get(default="0").strip()
                if len(thread_num_infos) > 0 else 0
            ),
            total_replay_page=(
                thread_num_infos[1].xpath("./text()").get(default="0").strip()
                if len(thread_num_infos) > 1 else 0
            ),
        )
        note.title = self._clean_title(note.title, note.tieba_name)
        return note

    def extract_tieba_note_parment_comments(self, page_content: str, note_id: str) -> List[TiebaComment]:
        """
        Extract Tieba post first-level comments from comment page
        Args:
            page_content: HTML string of page content
            note_id: Post ID

        Returns:
            List of first-level comment objects
        """
        xpath_selector = f"//div[{self._class_contains('l_post')} and {self._class_contains('j_l_post')}]"
        comment_list = Selector(text=page_content).xpath(xpath_selector)
        content_selector = Selector(text=page_content)
        tieba_name, tieba_link = self._extract_forum_info(content_selector, page_content)
        result: List[TiebaComment] = []
        for comment_selector in comment_list:
            comment_field_value: Dict = self.extract_data_field_value(comment_selector)
            comment_content_value = comment_field_value.get("content", {}) if comment_field_value else {}
            if not comment_content_value:
                continue
            other_info_content = comment_selector.xpath(
                f".//div[{self._class_contains('post-tail-wrap')}]"
            ).get(default="").strip()
            ip_location, publish_time = self.extract_ip_and_pub_time(other_info_content)
            user_selector = comment_selector.xpath(f".//a[{self._class_contains('p_author_name')}][1]")
            user_avatar = comment_selector.xpath(
                f".//a[{self._class_contains('p_author_face')}]//img/@src"
            ).get(default="").strip()
            if not user_avatar and comment_field_value.get("author", {}).get("portrait"):
                portrait = comment_field_value["author"]["portrait"]
                user_avatar = (
                    "https://gss0.bdstatic.com/6LZ1dD3d1sgCo2Kml5_Y_D3/sys/portrait/item/"
                    f"{portrait}"
                )
            content_html = comment_content_value.get("content") or comment_selector.xpath(
                f".//div[{self._class_contains('d_post_content')}]"
            ).get(default="")
            user_nickname = (
                self._selector_text(comment_selector, f".//a[{self._class_contains('p_author_name')}][1]")
                or comment_field_value.get("author", {}).get("user_nickname")
                or comment_field_value.get("author", {}).get("user_name", "")
            )
            tieba_comment = TiebaComment(
                comment_id=str(
                    comment_content_value.get("post_id")
                    or comment_selector.xpath("./@data-pid").get(default="")
                ),
                sub_comment_count=comment_content_value.get("comment_num") or 0,
                content=utils.extract_text_from_html(content_html),
                note_url=const.TIEBA_URL + f"/p/{note_id}",
                user_link=self._absolute_url(user_selector.xpath("./@href").get(default="")),
                user_nickname=user_nickname,
                user_avatar=user_avatar,
                tieba_id=str(comment_content_value.get("forum_id", "")),
                tieba_name=tieba_name,
                tieba_link=tieba_link,
                ip_location=ip_location,
                publish_time=publish_time,
                note_id=note_id,
            )
            result.append(tieba_comment)
        return result

    def extract_tieba_note_sub_comments(self, page_content: str, parent_comment: TiebaComment) -> List[TiebaComment]:
        """
        Extract Tieba post second-level comments from sub-comment page
        Args:
            page_content: HTML string of page content
            parent_comment: Parent comment object

        Returns:
            List of second-level comment objects
        """
        selector = Selector(page_content)
        comments = []
        comment_ele_list = selector.xpath(
            f"//li[{self._class_contains('lzl_single_post')} and {self._class_contains('j_lzl_s_p')}]"
        )
        for comment_ele in comment_ele_list:
            comment_value = self.extract_data_field_value(comment_ele)
            if not comment_value:
                continue
            comment_user_a_selector = comment_ele.xpath(
                f"./a[{self._class_contains('j_user_card')} and {self._class_contains('lzl_p_p')}][1]"
            )
            content = utils.extract_text_from_html(
                comment_ele.xpath(f".//span[{self._class_contains('lzl_content_main')}]").get(default=""))
            comment = TiebaComment(
                comment_id=str(comment_value.get("spid")), content=content,
                user_link=self._absolute_url(comment_user_a_selector.xpath("./@href").get(default="")),
                user_nickname=str(comment_value.get("showname") or ""),
                user_avatar=comment_user_a_selector.xpath("./img/@src").get(default=""),
                publish_time=self._selector_text(comment_ele, f".//span[{self._class_contains('lzl_time')}]"),
                parent_comment_id=parent_comment.comment_id,
                note_id=parent_comment.note_id, note_url=parent_comment.note_url,
                tieba_id=parent_comment.tieba_id, tieba_name=parent_comment.tieba_name,
                tieba_link=parent_comment.tieba_link)
            comments.append(comment)

        return comments

    def extract_creator_info(self, html_content: str) -> TiebaCreator:
        """
        Extract Tieba creator information from creator homepage
        Args:
            html_content: HTML string of creator homepage

        Returns:
            Tieba creator object
        """
        selector = Selector(text=html_content)
        user_link_selector = selector.xpath("//p[@class='space']/a")
        user_link: str = user_link_selector.xpath("./@href").get(default='')
        user_link_params: Dict = parse_qs(unquote(user_link.split("?")[-1]))
        user_name = user_link_params.get("un")[0] if user_link_params.get("un") else ""
        user_id = user_link_params.get("id")[0] if user_link_params.get("id") else ""
        userinfo_userdata_selector = selector.xpath("//div[@class='userinfo_userdata']")
        follow_fans_selector = selector.xpath("//span[@class='concern_num']")
        follows, fans = 0, 0
        if len(follow_fans_selector) == 2:
            follows, fans = self.extract_follow_and_fans(follow_fans_selector)
        user_content = userinfo_userdata_selector.get(default='')
        return TiebaCreator(user_id=user_id, user_name=user_name,
                            nickname=selector.xpath(".//span[@class='userinfo_username ']/text()").get(
                                default='').strip(),
                            avatar=selector.xpath(".//div[@class='userinfo_left_head']//img/@src").get(
                                default='').strip(),
                            gender=self.extract_gender(user_content),
                            ip_location=self.extract_ip(user_content),
                            follows=follows,
                            fans=fans,
                            registration_duration=self.extract_registration_duration(user_content)
                            )

    @staticmethod
    def extract_tieba_thread_id_list_from_creator_page(
        html_content: str
    ) -> List[str]:
        """
        Extract post ID list from Tieba creator's homepage
        Args:
            html_content: HTML string of creator homepage

        Returns:
            List of post IDs
        """
        selector = Selector(text=html_content)
        thread_id_list = []
        xpath_selector = (
            "//ul[@class='new_list clearfix']//div[@class='thread_name']/a[1]/@href"
        )
        thread_url_list = selector.xpath(xpath_selector).getall()
        for thread_url in thread_url_list:
            thread_id = thread_url.split("?")[0].split("/")[-1]
            thread_id_list.append(thread_id)
        return thread_id_list

    def extract_ip_and_pub_time(self, html_content: str) -> Tuple[str, str]:
        """
        Extract IP location and publish time from HTML content
        Args:
            html_content: HTML string

        Returns:
            Tuple of (IP location, publish time)
        """
        pattern_pub_time = re.compile(r'<span class="tail-info">(\d{4}-\d{2}-\d{2} \d{2}:\d{2})</span>')
        time_match = pattern_pub_time.search(html_content)
        pub_time = time_match.group(1) if time_match else ""
        return self.extract_ip(html_content), pub_time

    @staticmethod
    def extract_ip(html_content: str) -> str:
        """
        Extract IP location from HTML content
        Args:
            html_content: HTML string

        Returns:
            IP location string
        """
        pattern_ip = re.compile(r'IP属地:(\S+)</span>')
        ip_match = pattern_ip.search(html_content)
        ip = ip_match.group(1) if ip_match else ""
        return ip

    @staticmethod
    def extract_gender(html_content: str) -> str:
        """
        Extract gender from HTML content
        Args:
            html_content: HTML string

        Returns:
            Gender string ('Male', 'Female', or 'Unknown')
        """
        if GENDER_MALE in html_content:
            return 'Male'
        elif GENDER_FEMALE in html_content:
            return 'Female'
        return 'Unknown'

    @staticmethod
    def extract_follow_and_fans(selectors: List[Selector]) -> Tuple[str, str]:
        """
        Extract follow count and fan count from selectors
        Args:
            selectors: List of selector objects

        Returns:
            Tuple of (follow count, fan count)
        """
        pattern = re.compile(r'<span class="concern_num">\(<a[^>]*>(\d+)</a>\)</span>')
        follow_match = pattern.findall(selectors[0].get())
        fans_match = pattern.findall(selectors[1].get())
        follows = follow_match[0] if follow_match else 0
        fans = fans_match[0] if fans_match else 0
        return follows, fans

    @staticmethod
    def extract_registration_duration(html_content: str) -> str:
        """
        Extract Tieba age from HTML content
        Example: "<span>吧龄:1.9年</span>"
        Returns: "1.9年"

        Args:
            html_content: HTML string

        Returns:
            Tieba age string
        """
        pattern = re.compile(r'<span>吧龄:(\S+)</span>')
        match = pattern.search(html_content)
        return match.group(1) if match else ""

    @staticmethod
    def extract_data_field_value(selector: Selector) -> Dict:
        """
        Extract data-field value from selector
        Args:
            selector: Selector object

        Returns:
            Dictionary containing data-field value
        """
        data_field_value = selector.xpath("./@data-field").get(default='').strip()
        if not data_field_value or data_field_value == "{}":
            return {}
        try:
            # First use html.unescape to handle escape characters, then json.loads to convert JSON string to Python dictionary
            unescaped_json_str = html.unescape(data_field_value)
            data_field_dict_value = json.loads(unescaped_json_str)
        except Exception as ex:
            print(f"extract_data_field_value, error: {ex}, trying alternative parsing method")
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


def test_extract_tieba_note_sub_comments():
    with open("test_data/note_sub_comments.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        fake_parment_comment = TiebaComment(comment_id="123456", content="content", user_link="user_link",
                                            user_nickname="user_nickname", user_avatar="user_avatar",
                                            publish_time="publish_time", parent_comment_id="parent_comment_id",
                                            note_id="note_id", note_url="note_url", tieba_id="tieba_id",
                                            tieba_name="tieba_name", )
        result = extractor.extract_tieba_note_sub_comments(content, fake_parment_comment)
        print(result)


def test_extract_tieba_note_list():
    with open("test_data/tieba_note_list.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        result = extractor.extract_tieba_note_list(content)
        print(result)
    pass


def test_extract_creator_info():
    with open("test_data/creator_info.html", "r", encoding="utf-8") as f:
        content = f.read()
        extractor = TieBaExtractor()
        result = extractor.extract_creator_info(content)
        print(result.model_dump_json())


if __name__ == '__main__':
    # test_extract_search_note_list()
    # test_extract_note_detail()
    # test_extract_tieba_note_parment_comments()
    # test_extract_tieba_note_list()
    test_extract_creator_info()
