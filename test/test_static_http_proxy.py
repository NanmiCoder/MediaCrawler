# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/test_static_http_proxy.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from proxy.providers.static_http_proxy import (
    new_static_http_proxy,
    parse_static_http_proxies,
    parse_static_http_proxy,
)


class TestStaticHttpProxy(IsolatedAsyncioTestCase):
    def test_parse_static_http_proxy_with_auth(self):
        proxy = parse_static_http_proxy("http://user:pass@127.0.0.1:8899")

        self.assertEqual(proxy.ip, "127.0.0.1")
        self.assertEqual(proxy.port, 8899)
        self.assertEqual(proxy.user, "user")
        self.assertEqual(proxy.password, "pass")
        self.assertIsNone(proxy.expired_time_ts)

    def test_parse_static_http_proxy_accepts_bare_host_port(self):
        proxy = parse_static_http_proxy("127.0.0.1:8899")

        self.assertEqual(proxy.ip, "127.0.0.1")
        self.assertEqual(proxy.port, 8899)
        self.assertEqual(proxy.user, "")
        self.assertEqual(proxy.password, "")

    def test_parse_static_http_proxies_accepts_comma_separated_list(self):
        proxies = parse_static_http_proxies(
            "http://user:pass@127.0.0.1:8899,127.0.0.2:9900",
        )

        self.assertEqual(len(proxies), 2)
        self.assertEqual(proxies[0].ip, "127.0.0.1")
        self.assertEqual(proxies[0].port, 8899)
        self.assertEqual(proxies[0].user, "user")
        self.assertEqual(proxies[1].ip, "127.0.0.2")
        self.assertEqual(proxies[1].port, 9900)

    async def test_provider_reads_static_proxy_from_config(self):
        provider = new_static_http_proxy()

        with patch("config.STATIC_PROXY_URL", "http://127.0.0.1:8899,http://127.0.0.2:9900", create=True):
            proxies = await provider.get_proxy(3)

        self.assertEqual(len(proxies), 2)
        self.assertEqual(proxies[0].ip, "127.0.0.1")
        self.assertEqual(proxies[0].port, 8899)
        self.assertEqual(proxies[1].ip, "127.0.0.2")
        self.assertEqual(proxies[1].port, 9900)
