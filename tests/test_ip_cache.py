# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_ip_cache.py
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
import logging

from proxy.base_proxy import IpCache


class FakeCacheClient:
    def __init__(self, data):
        self.data = data

    def keys(self, pattern):
        prefix = pattern.rstrip("*")
        return [key for key in self.data if key.startswith(prefix)]

    def get(self, key):
        return self.data.get(key)


def _ip_json(ip):
    return json.dumps(
        {"ip": ip, "port": 8080, "user": "u", "password": "p", "expired_time_ts": 2000000000}
    )


def test_load_all_ip_skips_bad_entry_and_keeps_the_rest(caplog):
    ip_cache = IpCache.__new__(IpCache)
    ip_cache.cache_client = FakeCacheClient(
        {
            "kuaidaili_1.1.1.1": _ip_json("1.1.1.1"),
            "kuaidaili_2.2.2.2": "not-json",
            "kuaidaili_3.3.3.3": _ip_json("3.3.3.3"),
        }
    )

    with caplog.at_level(logging.ERROR):
        ip_list = ip_cache.load_all_ip(proxy_brand_name="kuaidaili")

    assert [ip.ip for ip in ip_list] == ["1.1.1.1", "3.3.3.3"]
    error_messages = [record.getMessage() for record in caplog.records]
    assert len(error_messages) == 1
    assert "kuaidaili_2.2.2.2" in error_messages[0]
