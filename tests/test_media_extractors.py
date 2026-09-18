# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_media_extractors.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

"""各平台媒体地址提取器单测。

每个平台的 ``media.py`` 都是纯函数，这里用最小化的真实结构 fixture 直接断言
产出的 ``MediaItem`` 列表，不发起任何网络请求。
"""

from __future__ import annotations

import config
import pytest

from media_downloader import MediaType
from media_platform.bilibili import media as bili_media
from media_platform.douyin import media as douyin_media
from media_platform.kuaishou import media as kuaishou_media
from media_platform.weibo import media as weibo_media
from media_platform.xhs import media as xhs_media

# --------------------------------------------------------------------------- xhs fixture

# 旧结构：分档按编码命名（h264），consumer 带无水印源片 key。
# 保留这份 fixture 是为了确保兼容性不被改坏。
XHS_VIDEO_NOTE = {
    "note_id": "video-note-1",
    "type": "video",
    "image_list": [{"url_default": "https://sns-webpic.xhscdn.com/img-cover"}],
    "cover": {"url_default": "https://sns-webpic.xhscdn.com/top-cover"},
    "video": {
        "consumer": {"origin_video_key": "spec/abc/def"},
        "media": {"stream": {"h264": [{"master_url": "https://sns-video-hw.xhscdn.com/master"}]}},
        "cover": {"url_default": "https://sns-webpic.xhscdn.com/video-cover"},
    },
}

# 上游当前结构（2026-09 真实响应裁剪）：分档改按内部档位命名（EF4/EF5/EF6/EF7），
# 同一分档内含多个分辨率，consumer 里不再有 origin_video_key。
# 回归背景：写死 stream["h264"] 时这里的视频地址会被静默取空，只下到封面。
XHS_VIDEO_NOTE_NEW_SHAPE = {
    "note_id": "video-note-2",
    "type": "video",
    "image_list": [{"url_default": "https://sns-webpic.xhscdn.com/img-cover-2"}],
    "video": {
        "consumer": {"chapters": []},
        "media": {
            "stream": {
                "EF4": [
                    {
                        "master_url": "https://sns-video-v4.xhscdn.com/720p-ef4",
                        "backup_urls": ["https://sns-bak-v1.xhscdn.com/720p-ef4"],
                        "width": 1280,
                        "height": 720,
                        "avg_bitrate": 414724,
                    }
                ],
                "EF5": [
                    {
                        "master_url": "https://sns-video-v4.xhscdn.com/1080p-ef5",
                        "width": 1920,
                        "height": 1080,
                        "avg_bitrate": 635797,
                    },
                    {
                        "master_url": "https://sns-video-v4.xhscdn.com/4k-ef5",
                        "width": 3840,
                        "height": 2160,
                        "avg_bitrate": 1534891,
                    },
                ],
                "EF6": [],
                "EF7": [],
            }
        },
    },
}

XHS_IMAGE_NOTE = {
    "note_id": "image-note-1",
    "type": "normal",
    "image_list": [
        {"url_default": "https://sns-webpic.xhscdn.com/1"},
        {"url_default": "https://sns-webpic.xhscdn.com/2"},
        {"url_default": "https://sns-webpic.xhscdn.com/3"},
    ],
}


# --------------------------------------------------------------------------- xhs 用例


def test_xhs_video_note_yields_cover_and_video():
    items = xhs_media.build_media_items(XHS_VIDEO_NOTE)

    assert [item.stem for item in items] == ["cover", "video"]
    assert [item.media_type for item in items] == [MediaType.IMAGE, MediaType.VIDEO]

    cover, video = items
    assert cover.url == "https://sns-webpic.xhscdn.com/video-cover"
    assert video.content_id == "video-note-1"
    # 优先无水印源片，带水印的 master_url 作为备用
    assert video.url == "https://sns-video-bd.xhscdn.com/spec/abc/def"
    assert video.backup_urls == ("https://sns-video-hw.xhscdn.com/master",)


def test_xhs_video_note_falls_back_to_top_level_cover():
    note = {**XHS_VIDEO_NOTE, "video": {**XHS_VIDEO_NOTE["video"], "cover": {}}}
    note.pop("cover", None)
    note["cover"] = {"url_default": "https://sns-webpic.xhscdn.com/top-cover"}

    items = xhs_media.build_media_items(note)

    assert items[0].url == "https://sns-webpic.xhscdn.com/top-cover"


def test_xhs_video_note_falls_back_to_first_image_when_no_cover():
    note = {
        **XHS_VIDEO_NOTE,
        "video": {**XHS_VIDEO_NOTE["video"], "cover": {}},
        "cover": {},
    }

    items = xhs_media.build_media_items(note)

    assert items[0].stem == "cover"
    assert items[0].url == "https://sns-webpic.xhscdn.com/img-cover"


def test_xhs_video_note_without_any_cover_still_yields_video():
    note = {
        **XHS_VIDEO_NOTE,
        "video": {**XHS_VIDEO_NOTE["video"], "cover": {}},
        "cover": {},
        "image_list": [],
    }

    items = xhs_media.build_media_items(note)

    assert [item.stem for item in items] == ["video"]


def test_xhs_video_note_without_origin_key_uses_master_url():
    note = {
        **XHS_VIDEO_NOTE,
        "video": {"media": {"stream": {"h264": [{"master_url": "https://sns-video-hw.xhscdn.com/master"}]}}},
    }

    items = xhs_media.build_media_items(note)

    video = next(item for item in items if item.media_type == MediaType.VIDEO)
    assert video.url == "https://sns-video-hw.xhscdn.com/master"
    assert video.backup_urls == ()


def test_xhs_video_note_new_stream_buckets():
    """上游把分档名从 h264 换成 EF4/EF5/... 之后仍要能取到地址（本次回归核心）"""
    urls = xhs_media.extract_video_urls(XHS_VIDEO_NOTE_NEW_SHAPE)

    # 分辨率高的排前面作主地址，其余按清晰度降序作为备用
    assert urls == [
        "https://sns-video-v4.xhscdn.com/4k-ef5",
        "https://sns-video-v4.xhscdn.com/1080p-ef5",
        "https://sns-video-v4.xhscdn.com/720p-ef4",
    ]


def test_xhs_video_note_new_shape_builds_video_item():
    """新结构下必须产出 video 任务，而不是只剩封面"""
    items = xhs_media.build_media_items(XHS_VIDEO_NOTE_NEW_SHAPE)

    assert [item.stem for item in items] == ["cover", "video"]
    video = items[1]
    assert video.media_type == MediaType.VIDEO
    assert video.url == "https://sns-video-v4.xhscdn.com/4k-ef5"
    assert video.backup_urls == (
        "https://sns-video-v4.xhscdn.com/1080p-ef5",
        "https://sns-video-v4.xhscdn.com/720p-ef4",
    )


def test_xhs_video_note_missing_dimensions_keeps_all_urls():
    """缺 height/avg_bitrate 时不能抛异常，也不能丢地址"""
    note = {
        "type": "video",
        "video": {
            "media": {"stream": {"EF5": [{"master_url": "https://a"}, {"master_url": "https://b"}]}}
        },
    }

    assert sorted(xhs_media.extract_video_urls(note)) == ["https://a", "https://b"]


def test_xhs_international_does_not_build_xhscdn_url(monkeypatch):
    monkeypatch.setattr(config, "XHS_INTERNATIONAL", True)

    items = xhs_media.build_media_items(XHS_VIDEO_NOTE)

    video = next(item for item in items if item.media_type == MediaType.VIDEO)
    assert video.url == "https://sns-video-hw.xhscdn.com/master"
    assert "sns-video-bd" not in video.url


def test_xhs_image_note_yields_numbered_images_without_duplicate_cover():
    items = xhs_media.build_media_items(XHS_IMAGE_NOTE)

    assert [item.stem for item in items] == ["001", "002", "003"]
    assert [item.url for item in items] == [
        "https://sns-webpic.xhscdn.com/1",
        "https://sns-webpic.xhscdn.com/2",
        "https://sns-webpic.xhscdn.com/3",
    ]
    assert all(item.media_type is MediaType.IMAGE for item in items)
    assert not any(item.stem == "cover" for item in items)


def test_xhs_image_note_skips_entries_without_url():
    note = {
        "note_id": "n1",
        "type": "normal",
        "image_list": [{"url_default": ""}, {"url": "https://cdn/x"}, {"no_url": True}],
    }

    items = xhs_media.build_media_items(note)

    assert [item.url for item in items] == ["https://cdn/x"]


def test_xhs_missing_note_id_returns_empty():
    assert xhs_media.build_media_items({"type": "video"}) == []


@pytest.mark.parametrize("payload", [None, "not-a-dict", [], 123])
def test_xhs_non_dict_input_is_ignored(payload):
    assert xhs_media.build_media_items(payload) == []


# --------------------------------------------------------------------------- douyin fixture

DY_VIDEO_ITEM = {
    "aweme_id": "7300000000000000001",
    "desc": "video",
    "video": {
        "play_addr_h264": {"url_list": ["https://cdn-a/h264", "https://cdn-b/h264"]},
        "play_addr": {"url_list": ["https://cdn-a/play"]},
        "raw_cover": {"url_list": ["https://cdn-a/cover", "https://cdn-b/cover"]},
    },
}

DY_IMAGE_ITEM = {
    "aweme_id": "7300000000000000002",
    "desc": "images",
    "images": [
        {"url_list": ["https://cdn-a/img1-small", "https://cdn-b/img1"]},
        {"url_list": ["https://cdn-a/img2-small", "https://cdn-b/img2"]},
    ],
    "video": {"raw_cover": {"url_list": ["https://cdn/cover"]}},
}


# --------------------------------------------------------------------------- douyin 用例


def test_douyin_video_item_yields_cover_and_video():
    items = douyin_media.build_media_items(DY_VIDEO_ITEM)

    assert [item.stem for item in items] == ["cover", "video"]
    cover, video = items
    assert cover.url == "https://cdn-b/cover"
    # url_list 最后一个通常无水印，其余作为备用
    assert video.url == "https://cdn-b/h264"
    assert video.backup_urls == ("https://cdn-a/h264",)
    assert video.media_type is MediaType.VIDEO


def test_douyin_video_falls_back_to_lower_quality_addr():
    item = {
        "aweme_id": "1",
        "video": {"play_addr_256": {"url_list": ["https://cdn/only", "https://cdn/best"]}},
    }

    items = douyin_media.build_media_items(item)

    video = next(entry for entry in items if entry.media_type is MediaType.VIDEO)
    assert video.url == "https://cdn/best"
    assert video.backup_urls == ("https://cdn/only",)


def test_douyin_video_falls_back_to_bit_rate_list():
    item = {
        "aweme_id": "1",
        "video": {
            "bit_rate": [
                {"bit_rate": 100, "play_addr": {"url_list": ["https://cdn/low"]}},
                {"bit_rate": 900, "play_addr": {"url_list": ["https://cdn/high"]}},
            ]
        },
    }

    items = douyin_media.build_media_items(item)

    video = next(entry for entry in items if entry.media_type is MediaType.VIDEO)
    assert video.url == "https://cdn/high"


def test_douyin_image_item_yields_numbered_images_without_cover():
    items = douyin_media.build_media_items(DY_IMAGE_ITEM)

    assert [item.stem for item in items] == ["001", "002"]
    assert [item.url for item in items] == ["https://cdn-b/img1", "https://cdn-b/img2"]
    assert not any(item.stem == "cover" for item in items)


def test_douyin_empty_video_yields_nothing():
    assert douyin_media.build_media_items({"aweme_id": "1", "video": {}}) == []


def test_douyin_cover_key_priority_is_locked():
    """封面字段有明确优先级，不能只钉住第一个键"""
    detail = {
        "aweme_id": "1",
        "video": {
            "raw_cover": {"url_list": ["https://cdn/raw"]},
            "origin_cover": {"url_list": ["https://cdn/origin"]},
            "cover": {"url_list": ["https://cdn/cover"]},
            "dynamic_cover": {"url_list": ["https://cdn/dynamic"]},
        },
    }

    assert douyin_media.extract_cover_url(detail) == "https://cdn/raw"
    del detail["video"]["raw_cover"]
    assert douyin_media.extract_cover_url(detail) == "https://cdn/origin"
    del detail["video"]["origin_cover"]
    assert douyin_media.extract_cover_url(detail) == "https://cdn/cover"
    del detail["video"]["cover"]
    assert douyin_media.extract_cover_url(detail) == "https://cdn/dynamic"


def test_douyin_video_addr_key_priority_is_locked():
    """h264 > 256 > play_addr 的降级顺序必须被钉住"""
    detail = {
        "aweme_id": "1",
        "video": {
            "play_addr_h264": {"url_list": ["https://cdn/h264"]},
            "play_addr_256": {"url_list": ["https://cdn/256"]},
            "play_addr": {"url_list": ["https://cdn/plain"]},
        },
    }

    assert douyin_media.extract_video_urls(detail) == ["https://cdn/h264"]
    del detail["video"]["play_addr_h264"]
    assert douyin_media.extract_video_urls(detail) == ["https://cdn/256"]
    del detail["video"]["play_addr_256"]
    assert douyin_media.extract_video_urls(detail) == ["https://cdn/plain"]


def test_bilibili_falls_back_to_lowest_quality_keeping_codec_priority(monkeypatch):
    """所有档位都超过用户设置时取最低清晰度，但编码优先级仍要生效（AVC 优先）"""
    monkeypatch.setattr(config, "BILI_QN", 16)
    play_info = {
        "dash": {
            "video": [
                {"id": 32, "codecid": 12, "bandwidth": 300000, "base_url": "https://upos/hevc.m4s"},
                {"id": 32, "codecid": 7, "bandwidth": 200000, "base_url": "https://upos/avc.m4s"},
                {"id": 80, "codecid": 7, "bandwidth": 900000, "base_url": "https://upos/80.m4s"},
            ]
        }
    }

    assert bili_media.pick_video_stream(play_info)["base_url"] == "https://upos/avc.m4s"


def test_bilibili_tolerates_string_typed_ids():
    """接口偶发把 id/bandwidth 返回成字符串，不能因此整条媒体被跳过"""
    play_info = {
        "dash": {
            "video": [
                {"id": "80", "codecid": "12", "bandwidth": "900000", "base_url": "https://upos/hevc.m4s"},
                {"id": "80", "codecid": "7", "bandwidth": "800000", "base_url": "https://upos/avc.m4s"},
            ],
            "audio": [{"id": "30280", "bandwidth": "192000", "base_url": "https://upos/a.m4s"}],
        }
    }

    item = bili_media.build_dash_item(play_info, "BV1")

    assert item is not None
    assert item.url == "https://upos/avc.m4s"


def test_bilibili_durl_stem_differs_from_dash_stem():
    """直链降级产物必须与 DASH 产物区分，否则低清文件会永久阻塞高清路径"""
    dash_item = bili_media.build_dash_item(BILI_DASH_PLAY_INFO, "BV1")
    durl_item = bili_media.build_durl_item(BILI_DURL_PLAY_INFO, "BV1")

    assert dash_item.stem == "video"
    assert durl_item.stem == "video-durl"


# --------------------------------------------------------------------------- kuaishou fixture

KS_VIDEO_ITEM = {
    "photo": {
        "id": "3xabcdefg",
        "caption": "hello",
        "photoH265Url": "https://ks/h265.mp4",
        "photoUrl": "https://ks/h264.mp4",
        "coverUrl": "https://ks/cover.jpg",
    },
    "author": {"id": "u1"},
}


# --------------------------------------------------------------------------- kuaishou 用例


def test_kuaishou_video_item_yields_cover_and_video():
    items = kuaishou_media.build_media_items(KS_VIDEO_ITEM)

    assert [item.stem for item in items] == ["cover", "video"]
    cover, video = items
    assert cover.url == "https://ks/cover.jpg"
    assert video.url == "https://ks/h265.mp4"
    assert video.backup_urls == ("https://ks/h264.mp4",)
    assert video.content_id == "3xabcdefg"


def test_kuaishou_falls_back_to_video_resource_representations():
    item = {
        "photo": {
            "id": "1",
            "videoResource": {
                "h264": {
                    "adaptationSet": [
                        {"representation": [{"url": "https://ks/rep.mp4"}]}
                    ]
                }
            },
        }
    }

    items = kuaishou_media.build_media_items(item)

    video = next(entry for entry in items if entry.media_type is MediaType.VIDEO)
    assert video.url == "https://ks/rep.mp4"


def test_kuaishou_cover_falls_back_to_cover_urls_list():
    item = {"photo": {"id": "1", "coverUrls": [{"url": "https://ks/c1.jpg"}], "photoUrl": "https://ks/v.mp4"}}

    items = kuaishou_media.build_media_items(item)

    cover = next(entry for entry in items if entry.stem == "cover")
    assert cover.url == "https://ks/c1.jpg"


def test_kuaishou_missing_photo_id_yields_nothing():
    assert kuaishou_media.build_media_items({"photo": {"photoUrl": "https://ks/v.mp4"}}) == []


# --------------------------------------------------------------------------- weibo fixture

WB_IMAGE_MBLOG = {
    "id": "5000000000000000",
    "pics": [
        {"url": "https://wx1.sinaimg.cn/orj360/abc.jpg", "pid": "abc"},
        "https://wx2.sinaimg.cn/thumbnail/def.jpg",
    ],
}

WB_VIDEO_MBLOG = {
    "id": "5000000000000001",
    "page_info": {
        "type": "video",
        "page_pic": {"url": "https://wx1.sinaimg.cn/orj360/cover.jpg"},
        "media_info": {
            "mp4_hd_mp4": "https://f.video.weibocdn.com/hd.mp4",
            "mp4_ld_mp4": "https://f.video.weibocdn.com/ld.mp4",
        },
    },
}


# --------------------------------------------------------------------------- weibo 用例


def test_weibo_image_url_is_rewritten_to_large_via_agent_host():
    assert (
        weibo_media.rewrite_image_url("https://wx1.sinaimg.cn/orj360/abc.jpg")
        == "https://i1.wp.com/wx1.sinaimg.cn/large/abc.jpg"
    )


def test_weibo_image_url_rewrite_ignores_query_string():
    assert (
        weibo_media.rewrite_image_url("https://wx1.sinaimg.cn/orj360/abc.jpg?v=1")
        == "https://i1.wp.com/wx1.sinaimg.cn/large/abc.jpg"
    )


def test_weibo_image_note_yields_numbered_images():
    items = weibo_media.build_media_items(WB_IMAGE_MBLOG)

    assert [item.stem for item in items] == ["001", "002"]
    assert [item.url for item in items] == [
        "https://i1.wp.com/wx1.sinaimg.cn/large/abc.jpg",
        "https://i1.wp.com/wx2.sinaimg.cn/large/def.jpg",
    ]


def test_weibo_video_note_yields_cover_and_video():
    items = weibo_media.build_media_items(WB_VIDEO_MBLOG)

    assert [item.stem for item in items] == ["cover", "video"]
    cover, video = items
    assert cover.url == "https://wx1.sinaimg.cn/orj360/cover.jpg"
    assert video.url == "https://f.video.weibocdn.com/hd.mp4"
    assert video.backup_urls == ("https://f.video.weibocdn.com/ld.mp4",)


def test_weibo_plain_note_yields_nothing():
    assert weibo_media.build_media_items({"id": "1", "text": "just text"}) == []


def test_weibo_retweet_uses_original_media():
    """转发微博的媒体在 retweeted_status 里，顶层没有；不处理会一条都下不到"""
    retweet = {
        "id": "6000000000000000",
        "text": "转发内容",
        "retweeted_status": {
            "id": "5000000000000009",
            "pics": [{"url": "https://wx1.sinaimg.cn/orj360/original.jpg"}],
        },
    }

    items = weibo_media.build_media_items(retweet)

    assert [item.stem for item in items] == ["001"]
    assert items[0].url == "https://i1.wp.com/wx1.sinaimg.cn/large/original.jpg"
    assert items[0].content_id == "6000000000000000", "目录应按转发帖自身 id 组织"


def test_weibo_retweet_with_video():
    retweet = {
        "id": "6000000000000001",
        "retweeted_status": {
            "page_info": {
                "type": "video",
                "page_pic": {"url": "https://wx1.sinaimg.cn/orj360/cover.jpg"},
                "media_info": {"mp4_hd_mp4": "https://f.video.weibocdn.com/hd.mp4"},
            }
        },
    }

    items = weibo_media.build_media_items(retweet)

    assert [item.stem for item in items] == ["cover", "video"]
    assert items[1].url == "https://f.video.weibocdn.com/hd.mp4"


def test_weibo_own_media_wins_over_retweeted_status():
    """自己带媒体时不应去看被转发的内容"""
    mblog = {
        "id": "6000000000000002",
        "pics": [{"url": "https://wx1.sinaimg.cn/orj360/mine.jpg"}],
        "retweeted_status": {"pics": [{"url": "https://wx1.sinaimg.cn/orj360/theirs.jpg"}]},
    }

    items = weibo_media.build_media_items(mblog)

    assert items[0].url == "https://i1.wp.com/wx1.sinaimg.cn/large/mine.jpg"


def test_kuaishou_falls_back_to_manifest_representations():
    """search 接口的 photo 字段更少，manifest 是最后一道兜底"""
    item = {
        "photo": {
            "id": "1",
            "manifest": {
                "adaptationSet": [{"representation": [{"url": "https://ks/manifest.mp4"}]}]
            },
        }
    }

    items = kuaishou_media.build_media_items(item)

    video = next(entry for entry in items if entry.media_type is MediaType.VIDEO)
    assert video.url == "https://ks/manifest.mp4"


@pytest.mark.parametrize("scalar_video_resource", ["https://ks/raw.mp4", 123, None])
def test_kuaishou_tolerates_scalar_video_resource(scalar_video_resource):
    """GraphQL 里 videoResource 可能是 scalar 而非对象，不能因此抛异常"""
    item = {"photo": {"id": "1", "videoResource": scalar_video_resource, "photoUrl": "https://ks/plain.mp4"}}

    video_items = [
        entry for entry in kuaishou_media.build_media_items(item)
        if entry.media_type is MediaType.VIDEO
    ]

    assert [entry.url for entry in video_items] == ["https://ks/plain.mp4"]


# --------------------------------------------------------------------------- bilibili fixture

BILI_VIEW = {
    "aid": 114514,
    "cid": 1919810,
    "bvid": "BV1dwuKzmE26",
    "pic": "https://i0.hdslb.com/bfs/archive/cover.jpg",
}

BILI_DASH_PLAY_INFO = {
    "dash": {
        "video": [
            {"id": 32, "bandwidth": 300000, "base_url": "https://upos/32.m4s", "backup_url": ["https://upos-b/32.m4s"]},
            {"id": 80, "bandwidth": 900000, "base_url": "https://upos/80.m4s"},
            {"id": 116, "bandwidth": 2000000, "baseUrl": "https://upos/116.m4s"},
        ],
        "audio": [
            {"id": 30216, "bandwidth": 64000, "base_url": "https://upos/a64.m4s"},
            {"id": 30280, "bandwidth": 192000, "base_url": "https://upos/a192.m4s", "backup_url": ["https://upos-b/a192.m4s"]},
        ],
    }
}

BILI_DURL_PLAY_INFO = {
    "durl": [
        {"url": "https://upos/seg1.mp4", "size": 1000, "backup_url": ["https://upos-b/seg1.mp4"]},
        {"url": "https://upos/seg2.mp4", "size": 5000},
    ]
}


# --------------------------------------------------------------------------- bilibili 用例


def test_bilibili_cover_item_from_view_pic():
    item = bili_media.build_cover_item(BILI_VIEW, "BV1dwuKzmE26")

    assert item is not None
    assert item.url == "https://i0.hdslb.com/bfs/archive/cover.jpg"
    assert item.stem == "cover"
    assert item.content_id == "BV1dwuKzmE26"


def test_bilibili_cover_item_missing_pic():
    assert bili_media.build_cover_item({"aid": 1}, "BV1") is None
    assert bili_media.build_cover_item({}, "BV1") is None


def test_bilibili_pick_video_stream_respects_configured_quality(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 80)

    stream = bili_media.pick_video_stream(BILI_DASH_PLAY_INFO)

    assert stream["id"] == 80


def test_bilibili_pick_video_stream_falls_back_to_lowest_when_all_exceed(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 16)

    stream = bili_media.pick_video_stream(BILI_DASH_PLAY_INFO)

    assert stream["id"] == 32


def test_bilibili_pick_video_stream_picks_highest_when_all_below(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 127)

    stream = bili_media.pick_video_stream(BILI_DASH_PLAY_INFO)

    assert stream["id"] == 116


def test_bilibili_pick_audio_stream_takes_highest_bandwidth():
    stream = bili_media.pick_audio_stream(BILI_DASH_PLAY_INFO)

    assert stream["id"] == 30280


def test_bilibili_prefers_avc_over_hevc_at_same_quality(monkeypatch):
    """同一清晰度下应选兼容性最好的 AVC，而不是码率更高但兼容性差的 HEVC"""
    monkeypatch.setattr(config, "BILI_QN", 80)
    play_info = {
        "dash": {
            "video": [
                {"id": 80, "codecid": 12, "bandwidth": 2000000, "base_url": "https://upos/hevc.m4s"},
                {"id": 80, "codecid": 7, "bandwidth": 1500000, "base_url": "https://upos/avc.m4s"},
                {"id": 80, "codecid": 13, "bandwidth": 1200000, "base_url": "https://upos/av1.m4s"},
            ],
            "audio": [{"id": 30280, "base_url": "https://upos/a.m4s"}],
        }
    }

    assert bili_media.pick_video_stream(play_info)["base_url"] == "https://upos/avc.m4s"
    assert bili_media.build_dash_item(play_info, "BV1").url == "https://upos/avc.m4s"


def test_bilibili_falls_back_to_hevc_when_avc_unavailable(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 80)
    play_info = {
        "dash": {
            "video": [
                {"id": 80, "codecid": 12, "bandwidth": 2000000, "base_url": "https://upos/hevc.m4s"},
            ],
            "audio": [{"id": 30280, "base_url": "https://upos/a.m4s"}],
        }
    }

    assert bili_media.pick_video_stream(play_info)["base_url"] == "https://upos/hevc.m4s"


def test_bilibili_build_dash_item(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 80)

    item = bili_media.build_dash_item(BILI_DASH_PLAY_INFO, "BV1dwuKzmE26")

    assert item is not None
    assert item.is_dash is True
    assert item.url == "https://upos/80.m4s"
    assert item.audio_url == "https://upos/a192.m4s"
    assert item.audio_backup_urls == ("https://upos-b/a192.m4s",)
    assert item.media_type is MediaType.VIDEO


def test_bilibili_build_dash_item_supports_camel_case_base_url(monkeypatch):
    monkeypatch.setattr(config, "BILI_QN", 127)

    item = bili_media.build_dash_item(BILI_DASH_PLAY_INFO, "BV1")

    assert item.url == "https://upos/116.m4s"


def test_bilibili_build_dash_item_requires_audio():
    play_info = {"dash": {"video": [{"id": 80, "base_url": "https://upos/v.m4s"}]}}

    assert bili_media.build_dash_item(play_info, "BV1") is None


def test_bilibili_build_durl_item_takes_largest_segment():
    item = bili_media.build_durl_item(BILI_DURL_PLAY_INFO, "BV1")

    assert item is not None
    assert item.url == "https://upos/seg2.mp4"
    assert item.is_dash is False


def test_bilibili_build_durl_item_keeps_backup_urls():
    play_info = {"durl": [{"url": "https://upos/only.mp4", "size": 1, "backup_url": ["https://upos-b/only.mp4"]}]}

    item = bili_media.build_durl_item(play_info, "BV1")

    assert item.backup_urls == ("https://upos-b/only.mp4",)


@pytest.mark.parametrize("play_info", [{}, {"durl": []}, None])
def test_bilibili_build_durl_item_empty(play_info):
    assert bili_media.build_durl_item(play_info or {}, "BV1") is None


def test_bilibili_counts_durl_segments():
    assert bili_media.count_durl_segments(BILI_DURL_PLAY_INFO) == 2
    assert bili_media.count_durl_segments(BILI_DASH_PLAY_INFO) == 0
    assert bili_media.count_durl_segments(None) == 0
    assert bili_media.count_durl_segments({"durl": ["oops", {"no_url": 1}]}) == 0


@pytest.mark.parametrize("payload", ["oops", 123, [], None])
def test_douyin_extractors_tolerate_malformed_payload(payload):
    """接口偶发返回非 dict 结构时不能抛异常，否则会中断整轮爬取"""
    assert douyin_media.build_media_items(payload) == []


@pytest.mark.parametrize("payload", ["oops", 123, [], None])
def test_kuaishou_extractors_tolerate_malformed_payload(payload):
    assert kuaishou_media.build_media_items(payload) == []


@pytest.mark.parametrize("payload", ["oops", 123, [], None])
def test_bilibili_extractors_tolerate_malformed_payload(payload):
    assert bili_media.pick_video_stream(payload or {}) is None
    assert bili_media.pick_audio_stream(payload or {}) is None
    assert bili_media.build_dash_item(payload or {}, "BV1") is None
    assert bili_media.build_durl_item(payload or {}, "BV1") is None


@pytest.mark.parametrize("payload", ["oops", 123, [], None])
def test_weibo_extractors_tolerate_malformed_payload(payload):
    assert weibo_media.build_media_items(payload) == []


def test_xhs_extractors_tolerate_malformed_video_field():
    """实测：video 字段是字符串时旧逻辑会 AttributeError"""
    assert xhs_media.build_media_items({"note_id": "n1", "type": "video", "video": "oops"}) == []
    assert xhs_media.build_media_items({"note_id": "n1", "type": "video", "video": None}) == []
    assert (
        xhs_media.build_media_items(
            {"note_id": "n1", "type": "video", "video": {"media": "oops", "cover": "oops"}}
        )
        == []
    )


def test_bilibili_tolerates_non_dict_stream_entries():
    play_info = {
        "dash": {
            "video": ["oops", {"id": 80, "base_url": "https://upos/ok.m4s"}],
            "audio": [{"id": 30280, "base_url": "https://upos/a.m4s"}],
        }
    }

    item = bili_media.build_dash_item(play_info, "BV1")

    assert item is not None
    assert item.url == "https://upos/ok.m4s"
