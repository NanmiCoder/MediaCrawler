# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_redis_json_cache.py
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

import json
import pickle
from unittest.mock import Mock

import pytest

from cache.redis_cache import RedisCache


@pytest.fixture
def redis_cache(monkeypatch):
    client = Mock()
    monkeypatch.setattr(RedisCache, "_connet_redis", lambda self: client)
    return RedisCache(), client


@pytest.mark.parametrize("value", ["验证码123456", 10, True, None, [1, "二"], {"ip": "127.0.0.1"}])
def test_redis_uses_json_and_preserves_supported_values(redis_cache, value):
    cache, client = redis_cache
    cache.set("key", value, 30)
    encoded = client.set.call_args.args[1]
    assert json.loads(encoded) == value
    client.get.return_value = encoded.encode() if isinstance(encoded, str) else encoded
    assert cache.get("key") == value
    assert client.set.call_args.kwargs["ex"] == 30


def test_redis_never_deserializes_legacy_pickle(redis_cache, monkeypatch):
    cache, client = redis_cache
    client.get.return_value = pickle.dumps({"legacy": "cache"})
    deserialize = Mock(side_effect=AssertionError("pickle must never be executed"))
    monkeypatch.setattr(pickle, "loads", deserialize)
    assert cache.get("key") is None
    deserialize.assert_not_called()


def test_redis_corrupt_entry_is_a_cache_miss(redis_cache):
    cache, client = redis_cache
    client.get.return_value = b"not-json"
    assert cache.get("key") is None
