# -*- coding: utf-8 -*-
"""
抖音评论爬取脚本 v2 - 增量写入，每爬完一个视频就保存
使用 MediaCrawler 的 DouYinClient 逐条获取视频评论
"""
import asyncio
import csv
import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from playwright.async_api import async_playwright

import config
from media_platform.douyin.client import DouYinClient
from media_platform.douyin.help import parse_video_info_from_url
from tools import utils
from tools.cdp_browser import CDPBrowserManager


async def create_client(playwright_page, browser_context):
    """创建 DouYinClient"""
    cookie_str, cookie_dict = await utils.convert_browser_context_cookies(
        browser_context,
        urls=["https://douyin.com", "https://www.douyin.com", "https://creator.douyin.com"],
    )
    douyin_client = DouYinClient(
        proxy=None,
        headers={
            "User-Agent": await playwright_page.evaluate("() => navigator.userAgent"),
            "Cookie": cookie_str,
            "Host": "www.douyin.com",
            "Origin": "https://www.douyin.com/",
            "Referer": "https://www.douyin.com/",
            "Content-Type": "application/json;charset=UTF-8",
        },
        playwright_page=playwright_page,
        cookie_dict=cookie_dict,
    )
    return douyin_client


def append_comments_to_file(filepath, comments):
    """同步追加评论到文件（在 async 上下文外调用）"""
    with open(filepath, "a", encoding="utf-8") as f:
        for comment in comments:
            f.write(json.dumps(comment, ensure_ascii=False) + "\n")


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return ""


def get_aweme_id(record: Dict[str, Any]) -> str:
    return str(first_value(
        record.get("aweme_id"),
        record.get("video_id"),
        record.get("note_id"),
        record.get("item_id"),
    )).strip()


def split_video_ids(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_video_records(input_path: Optional[str], raw_video_ids: Optional[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for video_id in split_video_ids(raw_video_ids):
        records.append({"aweme_id": video_id, "video_id": video_id})

    if input_path:
        suffix = os.path.splitext(input_path)[1].lower()
        if suffix == ".csv":
            with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                records.extend(dict(row) for row in reader)
        else:
            with open(input_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    records.append(json.loads(line.strip()))

    seen = set()
    unique_records: List[Dict[str, Any]] = []
    for record in records:
        aweme_id = get_aweme_id(record)
        if not aweme_id or aweme_id in seen:
            continue
        seen.add(aweme_id)
        unique_records.append(record)
    return unique_records


def resolve_output_path(output_arg: Optional[str], input_path: Optional[str]) -> str:
    if output_arg:
        return os.path.abspath(output_arg)
    if input_path:
        return os.path.join(os.path.dirname(os.path.abspath(input_path)), "search_comments.jsonl")
    return os.path.abspath(os.path.join("data", "douyin", "jsonl", "search_comments.jsonl"))


def standardize_comment(
    video_record: Dict[str, Any],
    comment_item: Dict[str, Any],
    source_task_id: str = "",
) -> Dict[str, Any]:
    user_info = comment_item.get("user") or {}
    aweme_id = get_aweme_id(video_record)
    video_id = str(first_value(video_record.get("video_id"), aweme_id)).strip()
    aweme_url = str(first_value(
        video_record.get("aweme_url"),
        video_record.get("url"),
        f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
    ))
    return {
        "source_keyword": str(first_value(
            video_record.get("source_keyword"),
            video_record.get("keyword"),
            video_record.get("search_keyword"),
        )),
        "platform": "douyin",
        "source_task_id": str(first_value(source_task_id, video_record.get("source_task_id"))),
        "video_id": video_id,
        "aweme_id": aweme_id,
        "aweme_url": aweme_url,
        "comment_id": str(first_value(comment_item.get("cid"), comment_item.get("comment_id"))),
        "parent_comment_id": str(first_value(
            comment_item.get("reply_id"),
            comment_item.get("parent_comment_id"),
            "0",
        )),
        "user_id": str(first_value(user_info.get("uid"), user_info.get("user_id"))),
        "sec_uid": str(first_value(user_info.get("sec_uid"), comment_item.get("sec_uid"))),
        "nickname": str(first_value(user_info.get("nickname"), comment_item.get("nickname"))),
        "content": str(first_value(comment_item.get("text"), comment_item.get("content"))),
        "liked_count": safe_int(first_value(
            comment_item.get("digg_count"),
            comment_item.get("like_count"),
            comment_item.get("liked_count"),
            0,
        )),
        "reply_count": safe_int(first_value(
            comment_item.get("reply_comment_total"),
            comment_item.get("reply_count"),
            comment_item.get("sub_comment_count"),
            0,
        )),
        "create_time": str(first_value(comment_item.get("create_time"), "")),
        "ip_location": str(first_value(comment_item.get("ip_label"), comment_item.get("ip_location"))),
        "raw_comment": comment_item,
        "crawl_time": datetime.utcnow().isoformat() + "Z",
    }


async def crawl_comments_for_video(
    dy_client,
    video_record,
    source_task_id="",
    max_comments=200,
    crawl_interval=2,
):
    """获取单个视频的评论"""
    if isinstance(video_record, str):
        video_record = {"aweme_id": video_record, "video_id": video_record}
    aweme_id = get_aweme_id(video_record)
    comments = []
    cursor = 0
    has_more = 1

    while has_more and len(comments) < max_comments:
        try:
            res = await dy_client.get_aweme_comments(aweme_id, cursor)
            has_more = res.get("has_more", 0)
            cursor = res.get("cursor", 0)
            batch = res.get("comments", [])

            if not batch:
                break

            # 截断到 max_comments
            remaining = max_comments - len(comments)
            if len(batch) > remaining:
                batch = batch[:remaining]

            for comment_item in batch:
                comments.append(standardize_comment(video_record, comment_item, source_task_id))

            utils.logger.info(f"[crawl] {aweme_id}: {len(comments)}/{max_comments} comments, has_more={has_more}")
            await asyncio.sleep(crawl_interval)

        except Exception as e:
            utils.logger.error(f"[crawl] {aweme_id} error: {e}")
            raise

    return comments


async def main():
    parser = argparse.ArgumentParser(description="抖音评论爬取脚本 v2")
    parser.add_argument("--input", default=None,
                        help="视频数据 JSONL/CSV 文件路径")
    parser.add_argument("--output", default=None,
                        help="评论 JSONL 输出路径")
    parser.add_argument("--video-ids", default=None,
                        help="逗号分隔的视频 ID 列表")
    parser.add_argument("--source-task-id", default="",
                        help="来源搜索任务 ID")
    parser.add_argument("--max-comments", type=int, default=200,
                        help="每个视频最大评论数（默认200）")
    parser.add_argument("--interval", type=int, default=2,
                        help="请求间隔秒数（默认2）")
    parser.add_argument("--skip-existing", action="store_true",
                        help="跳过已有评论的视频（断点续传）")
    parser.add_argument("--cdp-port", type=int, default=19222,
                        help="CDP 调试端口（默认19222）")
    args = parser.parse_args()

    if not 1 <= args.cdp_port <= 65535:
        parser.error("--cdp-port 必须在 1-65535 之间")
    config.CDP_DEBUG_PORT = args.cdp_port
    utils.logger.info(f"[main] Using Chrome CDP port: {config.CDP_DEBUG_PORT}")

    video_records = load_video_records(args.input, args.video_ids)
    if not video_records:
        raise ValueError("No video records found from --input or --video-ids")

    # 输出文件
    output_path = resolve_output_path(args.output, args.input)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    open(output_path, "a", encoding="utf-8").close()

    # 读取已有评论（断点续传）
    existing_videos = set()
    if os.path.exists(output_path) and args.skip_existing:
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    existing_videos.add(item.get("aweme_id", ""))
        utils.logger.info(f"[main] Found {len(existing_videos)} videos with existing comments, will skip")

    # 过滤掉已爬取的视频
    todo_records = [record for record in video_records if get_aweme_id(record) not in existing_videos]
    utils.logger.info(f"[main] Total {len(video_records)} videos, {len(existing_videos)} already done, {len(todo_records)} remaining")

    if not todo_records:
        utils.logger.info("[main] All videos already crawled!")
        return

    # 统计变量
    total_comments = 0
    success_count = 0
    fail_count = 0
    pending_comments = []  # 当前批次待写入的评论

    # 启动浏览器
    async with async_playwright() as playwright:
        cdp_manager = CDPBrowserManager()
        browser_context = await cdp_manager.launch_and_connect(
            playwright=playwright,
            playwright_proxy=None,
            user_agent=None,
            headless=False,
        )
        await cdp_manager.add_stealth_script()

        context_page = await browser_context.new_page()
        await context_page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=60000)

        # 创建客户端
        dy_client = await create_client(context_page, browser_context)

        # 检查登录
        if not await dy_client.pong(browser_context=browser_context):
            utils.logger.info("[main] Not logged in, please scan QR code...")
            from media_platform.douyin.login import DouYinLogin
            login_obj = DouYinLogin(
                login_type="qrcode",
                login_phone="",
                browser_context=browser_context,
                context_page=context_page,
                cookie_str="",
            )
            await login_obj.begin()
            await dy_client.update_cookies(
                browser_context=browser_context,
                urls=["https://douyin.com", "https://www.douyin.com"],
            )

        utils.logger.info("[main] Login OK, starting comment crawl...")

        for i, video_record in enumerate(todo_records):
            aweme_id = get_aweme_id(video_record)
            utils.logger.info(f"[main] [{i+1}/{len(todo_records)}] Crawling {aweme_id}...")
            try:
                comments = await crawl_comments_for_video(
                    dy_client, video_record,
                    source_task_id=args.source_task_id,
                    max_comments=args.max_comments,
                    crawl_interval=args.interval,
                )

                total_comments += len(comments)
                success_count += 1
                pending_comments.extend(comments)
                utils.logger.info(f"[main] [{i+1}/{len(todo_records)}] Got {len(comments)} comments for {aweme_id}, total: {total_comments}")

            except Exception as e:
                fail_count += 1
                utils.logger.error(f"[main] [{i+1}/{len(todo_records)}] Failed for {aweme_id}: {e}")

            # 每爬完一个视频，立即追加写入文件
            if pending_comments:
                try:
                    append_comments_to_file(output_path, pending_comments)
                    utils.logger.info(f"[main] Saved {len(pending_comments)} comments to file (total written: {total_comments})")
                    pending_comments = []
                except OSError as write_err:
                    utils.logger.error(f"[main] Write error: {write_err}, keeping {len(pending_comments)} in memory for retry")

            # 视频间间隔
            await asyncio.sleep(args.interval)

        # 清理浏览器
        await cdp_manager.cleanup()

    if fail_count and success_count == 0:
        raise RuntimeError(
            f"Comment collection failed for all {fail_count} videos; "
            f"check Chrome CDP port {config.CDP_DEBUG_PORT} and login state"
        )

    # 写入任何剩余的评论（如最后一批因浏览器断连没来得及写）
    if pending_comments:
        try:
            append_comments_to_file(output_path, pending_comments)
            utils.logger.info(f"[main] Final save: {len(pending_comments)} remaining comments")
        except OSError as write_err:
            # 最后手段：写到备用路径
            fallback = os.path.join(output_dir, "search_comments_fallback.jsonl")
            utils.logger.error(f"[main] Cannot write to {output_path}: {write_err}, trying fallback: {fallback}")
            with open(fallback, "w", encoding="utf-8") as f:
                for comment in pending_comments:
                    f.write(json.dumps(comment, ensure_ascii=False) + "\n")

    utils.logger.info(f"[main] Done! {total_comments} comments from {success_count} videos, {fail_count} failures")
    utils.logger.info(f"[main] Output: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
