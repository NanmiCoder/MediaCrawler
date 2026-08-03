# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/kuaishou/help.py
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

import re

from playwright.async_api import Page

from model.m_kuaishou import VideoUrlInfo, CreatorUrlInfo

# 快手网页端签名（__NS_hxfalcon）支持。
# 快手网页端已将批量列表接口迁移到带签名的 REST 端点，
# 通过页面加载时注入的捕获脚本获取页面内置签名环境的调用入口，
# 再调用 $encode 生成签名。仅复用页面自身已加载的 JS 环境，
# 不引入额外的签名代码文件。

KS_SIGN_CAPTURE_SCRIPT = """
// 捕获快手页面内置签名环境的调用入口（学习用途）
(() => {
  if (window.__ks_realm) return;
  let done = false;
  const setter = function (v) {
    if (!done && this && typeof this === "object" && this !== window &&
        typeof this.$encode === "function" &&
        typeof this.$getCatVersion === "function") {
      done = true;
      window.__ks_realm = this;
      // 捕获成功后移除钩子，避免影响页面其他行为
      try { delete Object.prototype.caver; } catch (e) {}
    }
    Object.defineProperty(this, "caver", {
      value: v, writable: true, enumerable: true, configurable: true,
    });
  };
  try {
    Object.defineProperty(Object.prototype, "caver", { set: setter, configurable: true });
  } catch (e) {}
})();
"""


async def get_ks_sign_from_playwright(page: Page, url: str, query: dict, body: dict) -> str:
    """
    通过浏览器页面生成快手 __NS_hxfalcon 签名
    Args:
        page: 已加载快手页面的 playwright page（需先注入 KS_SIGN_CAPTURE_SCRIPT）
        url: 请求路径，如 /rest/v/profile/feed
        query: 请求 query 参数，如 {"caver": 2}
        body: 请求 body（JSON 对象）
    Returns:
        签名串
    """
    try:
        await page.wait_for_function("() => !!window.__ks_realm", timeout=15000)
    except Exception:
        # 页面可能在 cookie 注入前就已加载（未登录态），此时签名环境未初始化，
        # 重载页面让其在登录态下加载并触发签名请求，捕获脚本将随新 document 生效
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_function("() => !!window.__ks_realm", timeout=20000)
    return await page.evaluate(
        """([u, q, b]) => new Promise((resolve, reject) => {
            window.__ks_realm.call('$encode', [
                { url: u, query: q, form: {}, requestBody: b },
                { suc: s => resolve(s), err: e => reject(new Error(String(e))) }
            ]);
        })""",
        [url, query, body],
    )


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from Kuaishou video URL
    Supports the following formats:
    1. Full video URL: "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search"
    2. Pure video ID: "3x3zxz4mjrsc8ke"

    Args:
        url: Kuaishou video link or video ID
    Returns:
        VideoUrlInfo: Object containing video ID
    """
    # If it doesn't contain http and doesn't contain kuaishou.com, consider it as pure ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return VideoUrlInfo(video_id=url, url_type="normal")

    # Extract ID from standard video URL: /short-video/video_ID
    video_pattern = r'/short-video/([a-zA-Z0-9_-]+)'
    match = re.search(video_pattern, url)
    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id, url_type="normal")

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator ID from Kuaishou creator homepage URL
    Supports the following formats:
    1. Creator homepage: "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
    2. Pure ID: "3x4sm73aye7jq7i"

    Args:
        url: Kuaishou creator homepage link or user_id
    Returns:
        CreatorUrlInfo: Object containing creator ID
    """
    # If it doesn't contain http and doesn't contain kuaishou.com, consider it as pure ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return CreatorUrlInfo(user_id=url)

    # Extract user_id from creator homepage URL: /profile/xxx
    user_pattern = r'/profile/([a-zA-Z0-9_-]+)'
    match = re.search(user_pattern, url)
    if match:
        user_id = match.group(1)
        return CreatorUrlInfo(user_id=user_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    print("=== Video URL Parsing Test ===")
    test_video_urls = [
        "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search&area=searchxxnull&searchKey=python",
        "3xf8enb8dbj6uig",
    ]
    for url in test_video_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")

    # Test creator URL parsing
    print("=== Creator URL Parsing Test ===")
    test_creator_urls = [
        "https://www.kuaishou.com/profile/3x84qugg4ch9zhs",
        "3x4sm73aye7jq7i",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"✓ URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"✗ URL: {url}")
            print(f"  Error: {e}\n")
