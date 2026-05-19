# -*- coding: utf-8 -*-

from pathlib import Path

from media_platform.tieba.help import TieBaExtractor
from model.m_baidu_tieba import TiebaComment


FIXTURE_DIR = Path(__file__).parent.parent / "media_platform" / "tieba" / "test_data"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_extract_search_note_list_from_keyword_page():
    notes = TieBaExtractor.extract_search_note_list(read_fixture("search_keyword_notes.html"))

    assert len(notes) == 10
    assert notes[0].note_id == "9117888152"
    assert notes[0].title.startswith("武汉交互空间科技")
    assert notes[0].tieba_name == "武汉交互空间"
    assert notes[0].user_nickname == "VR虚拟达人"


def test_extract_search_note_list_from_current_pc_card_page():
    page_content = """
    <html>
      <body>
        <div class="threadcardclass thread-new3 index-feed-cards">
          <a class="action-link-bg" href="https://tieba.baidu.com/p/10559655942?fr=undefined"></a>
          <div class="thread-forum-name display-flex align-center">
            <span class="forum-name-text">诸城吧</span>
          </div>
          <div class="top-title">
            <span class="forum-attention user">754023117</span>
            <span>发布于 2026-3-15</span>
          </div>
          <div class="title-wrap"><span>数，英，编程老师</span></div>
          <div class="abstract-wrap">
            <span>培训班需求，数学，英语，编程老师，专职兼职都可</span>
          </div>
          <a class="comment-link-zone" href="https://tieba.baidu.com/p/10559655942?showComment=1">
            <span class="action-number">19</span>
          </a>
        </div>
      </body>
    </html>
    """

    notes = TieBaExtractor.extract_search_note_list(page_content)

    assert len(notes) == 1
    assert notes[0].note_id == "10559655942"
    assert notes[0].title == "数，英，编程老师"
    assert notes[0].desc == "培训班需求，数学，英语，编程老师，专职兼职都可"
    assert notes[0].tieba_name == "诸城吧"
    assert notes[0].tieba_link.endswith("kw=%E8%AF%B8%E5%9F%8E")
    assert notes[0].user_nickname == "754023117"
    assert notes[0].publish_time == "2026-3-15"
    assert notes[0].total_replay_num == 19


def test_extract_search_note_list_from_current_pc_api():
    api_data = {
        "no": 0,
        "error": "success",
        "data": {
            "card_list": [
                {"cardInfo": "related_user", "cardStyle": "related_user", "data": {}},
                {
                    "cardInfo": "thread",
                    "cardStyle": "thread",
                    "data": {
                        "tid": "10559655942",
                        "title": "数，英，编程老师",
                        "content": "培训班需求，数学，英语，编程老师，专职兼职都可",
                        "time": 1773552643,
                        "user": {
                            "show_nickname": "754023117",
                            "portrait": "https://example.com/avatar.jpg",
                        },
                        "post_num": 19,
                        "forum_name": "诸城",
                    },
                },
            ]
        },
    }

    notes = TieBaExtractor().extract_search_note_list_from_api(api_data)

    assert len(notes) == 1
    assert notes[0].note_id == "10559655942"
    assert notes[0].title == "数，英，编程老师"
    assert notes[0].tieba_name == "诸城吧"
    assert notes[0].total_replay_num == 19
    assert notes[0].publish_time


def test_extract_note_detail_and_comments_from_current_pc_api():
    api_data = {
        "error_code": 0,
        "thread": {
            "id": 10451142633,
            "title": "这X尔斯对比巴尔斯，我只能说ID正确，允许居功自傲",
            "reply_num": 15,
            "create_time": 1769951446,
        },
        "forum": {"id": 1627732, "name": "dota2"},
        "page": {"total_page": 1},
        "first_floor": {
            "id": 153154064746,
            "author_id": 4089186644,
            "time": 1769951446,
            "content": [{"type": 0, "text": "皮队败决处刑德国编程钢琴师兼职数学家"}],
        },
        "post_list": [
            {
                "id": 153154097267,
                "author_id": 6614897968,
                "time": 1769952062,
                "content": [{"type": 0, "text": "xg现在大树阵容另一个辅助不选控制"}],
                "sub_post_number": 4,
            }
        ],
        "user_list": [
            {
                "id": 4089186644,
                "name_show": "泰高祖蒙斯克",
                "portrait": "tb.1.f893a7af",
                "ip_address": "广东",
            },
            {
                "id": 6614897968,
                "name_show": "期胡希3",
                "portrait": "tb.1.4d0471d4",
                "ip_address": "河北",
            },
        ],
    }

    extractor = TieBaExtractor()
    note = extractor.extract_note_detail_from_api(api_data)
    comments = extractor.extract_tieba_note_parent_comments_from_api(api_data, note)

    assert note.note_id == "10451142633"
    assert note.title == "这X尔斯对比巴尔斯，我只能说ID正确，允许居功自傲"
    assert note.desc == "皮队败决处刑德国编程钢琴师兼职数学家"
    assert note.user_nickname == "泰高祖蒙斯克"
    assert note.tieba_name == "dota2吧"
    assert note.total_replay_num == 15
    assert note.total_replay_page == 1
    assert note.ip_location == "广东"
    assert len(comments) == 1
    assert comments[0].comment_id == "153154097267"
    assert comments[0].content == "xg现在大树阵容另一个辅助不选控制"
    assert comments[0].user_nickname == "期胡希3"
    assert comments[0].sub_comment_count == 4
    assert comments[0].ip_location == "河北"


def test_extract_creator_info_and_threads_from_current_pc_api():
    creator_api = {
        "error_code": 0,
        "data": {
            "user": {
                "id": 3546493137,
                "name": "拜月教Alice",
                "name_show": "米米世界大手子",
                "portrait": "tb.1.6ad0cd4a.7ZcjVYWa7UpHttCld2OppA?t=1777543466",
                "fans_num": 58,
                "concern_num": 1,
                "sex": 1,
                "tb_age": "7.8",
                "ip_address": "广东",
            }
        },
    }
    feed_api = {
        "error_code": 0,
        "data": {
            "list": [
                {"type": 1, "thread_info": {"id": 10208192951, "tid": 10208192951}},
                {"type": 1, "thread_info": {"id": 9835114923}},
            ]
        },
    }

    extractor = TieBaExtractor()
    creator = extractor.extract_creator_info_from_api(creator_api)
    thread_ids = extractor.extract_creator_thread_id_list_from_api(feed_api)

    assert creator.user_id == "3546493137"
    assert creator.user_name == "拜月教Alice"
    assert creator.nickname == "米米世界大手子"
    assert creator.fans == 58
    assert creator.follows == 1
    assert creator.ip_location == "广东"
    assert creator.registration_duration == "7.8"
    assert thread_ids == ["10208192951", "9835114923"]


def test_extract_tieba_note_list_from_current_frs_api():
    api_data = {
        "error_code": 0,
        "forum": {
            "id": 351091,
            "name": "加工中心",
            "tids": "10376710029,10636556989,",
        },
    }

    notes = TieBaExtractor().extract_tieba_note_list_from_frs_api(api_data)

    assert [note.note_id for note in notes] == ["10376710029", "10636556989"]
    assert notes[0].note_url == "https://tieba.baidu.com/p/10376710029"
    assert notes[0].tieba_name == "加工中心吧"
    assert notes[0].tieba_link.endswith("kw=%E5%8A%A0%E5%B7%A5%E4%B8%AD%E5%BF%83")


def test_extract_tieba_note_list_from_bigpipe_thread_page():
    notes = TieBaExtractor().extract_tieba_note_list(read_fixture("tieba_note_list.html"))

    assert len(notes) == 48
    assert notes[0].note_id == "9079949995"
    assert notes[0].title == "盗墓笔记全集+txt小说，已整理"
    assert notes[0].user_nickname == "公子伯仲"
    assert notes[0].tieba_name == "盗墓笔记吧"
    assert notes[0].tieba_link.endswith("kw=%E7%9B%97%E5%A2%93%E7%AC%94%E8%AE%B0&ie=utf-8")


def test_extract_note_detail_from_post_page():
    note = TieBaExtractor().extract_note_detail(read_fixture("note_detail.html"))

    assert note.note_id == "9117905169"
    assert note.title == "对于一个父亲来说，这个女儿14岁就死了"
    assert note.user_nickname == "章景轩"
    assert note.tieba_name == "以太比特吧"
    assert note.total_replay_num == 786
    assert note.total_replay_page == 13
    assert note.ip_location == "广东"


def test_extract_parent_comments_from_post_page():
    comments = TieBaExtractor().extract_tieba_note_parment_comments(
        read_fixture("note_comments.html"),
        "9119688421",
    )

    assert len(comments) == 30
    assert comments[0].comment_id == "150726491368"
    assert comments[0].content == "中国队第22金！无悬念！"
    assert comments[0].user_nickname == "heinzfrentzen"
    assert comments[0].tieba_name == "网球风云吧"
    assert comments[0].ip_location == "福建"


def test_extract_sub_comments_with_class_token_matching():
    parent = TiebaComment(
        comment_id="150726496253",
        content="parent",
        note_id="9119688421",
        note_url="https://tieba.baidu.com/p/9119688421",
        tieba_id="4513750",
        tieba_name="网球风云吧",
        tieba_link="https://tieba.baidu.com/f?kw=%E7%BD%91%E7%90%83%E9%A3%8E%E4%BA%91",
    )

    comments = TieBaExtractor().extract_tieba_note_sub_comments(
        read_fixture("note_sub_comments.html"),
        parent,
    )

    assert len(comments) >= 10
    assert comments[0].comment_id
    assert comments[0].parent_comment_id == parent.comment_id
    assert comments[0].user_link.startswith("https://tieba.baidu.com/home/main")
