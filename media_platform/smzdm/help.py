# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/smzdm/help.py
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1

from typing import List
from parsel import Selector


class SmzdmExtractor:
    def extract_post(self, postId: str, url: str, html: str) -> dict:
        """
        从商品/文章页面 HTML 提取文章主信息
        """
        sel = Selector(text=html)
        title = sel.xpath("//title/text()").get() or ""
        title = title.split("|")[0].strip()

        descList = sel.xpath("//article//text() | //div[@class='article-content']//text() | //div[@class='item-box']//text()").getall()
        desc = " ".join([d.strip() for d in descList if d.strip()])

        author = sel.xpath("//span[@class='username']/text() | //a[contains(@class, 'name')]/text()").get() or ""
        author = author.strip()

        return {
            "post_id": postId,
            "title": title,
            "content": desc[:1000],
            "post_url": url,
            "publish_time": "",
            "like_count": 0,
            "comment_count": 0,
            "author_nickname": author
        }

    def extract_comments_from_html(self, postId: str, html: str) -> List[dict]:
        """
        从文章详情页 HTML 解析提取一级和二级评论
        """
        sel = Selector(text=html)
        commentsList: List[dict] = []

        # 查找所有一级评论元素 (class 包含 comment-main-list-item)
        items = sel.xpath("//li[contains(@class, 'comment-main-list-item')]")
        for item in items:
            # 1. 提取评论 ID
            commentId = item.xpath("@data-comment-id").get() or item.xpath("@id").get() or ""
            commentId = "".join([c for c in commentId if c.isdigit()])
            if not commentId:
                # 备用方案，从 data-item 属性中提取评论 ID
                dataItem = item.xpath(".//div[contains(@class, 'J_zan')]/@data-item").get() or ""
                if dataItem:
                    parts = dataItem.split(",")
                    if len(parts) >= 3:
                        commentId = parts[2].strip()

            if not commentId:
                continue

            # 2. 提取评论内容
            contentNodes = item.xpath(".//div[contains(@class, 'comment-main-list-item-content-comment')]/text() | .//div[contains(@class, 'comment-main-list-item-content-comment')]//span/text()").getall()
            contentText = "".join([n.strip() for n in contentNodes]).strip()

            # 3. 提取作者昵称
            authorName = item.xpath(".//div[contains(@class, 'comment-main-list-item-content-header')]//h4[contains(@class, 'display-name')]/a/text()").get()
            if not authorName:
                authorName = item.xpath(".//div[contains(@class, 'comment-main-list-item-content-header')]//h4[contains(@class, 'display-name')]/text()").get()
            if not authorName:
                authorName = item.xpath(".//a[contains(@class, 'username')]/text()").get()
            authorName = (authorName or "").strip()

            # 4. 提取头像 URL
            avatarUrl = item.xpath(".//div[contains(@class, 'comment-main-list-item-avatar')]//img/@src").get()
            if not avatarUrl:
                avatarUrl = item.xpath(".//div[contains(@class, 'avatar')]//img/@src | .//img[contains(@class, 'avatar')]/@src").get()
            avatarUrl = (avatarUrl or "").strip()

            # 5. 提取发布时间与 IP 属地
            infoSpans = item.xpath(".//div[contains(@class, 'comment-main-list-item-content-info')]//div[contains(@class, 'content-info')]/span/text()").getall()
            if not infoSpans:
                infoSpans = item.xpath(".//div[contains(@class, 'comment-main-list-item-content-info')]/span/text()").getall()

            timeText = ""
            ipText = ""
            if infoSpans:
                infoSpans = [s.strip() for s in infoSpans if s.strip()]
                if len(infoSpans) >= 1:
                    timeText = infoSpans[0]
                if len(infoSpans) >= 2:
                    ipText = infoSpans[-1]
                    if ipText == timeText:
                        ipText = ""

            # 6. 提取点赞数
            likeText = item.xpath(".//div[contains(@class, 'J_zan')]//span/text()").get() or "0"
            likeCount = int("".join([c for c in likeText if c.isdigit()]) or 0)

            # 7. 提取子回复元素并计数
            subItems = item.xpath(".//div[contains(@class, 'comment-main-list-item-child')]")
            subCount = len(subItems)

            commentsList.append({
                "comment_id": commentId,
                "parent_comment_id": "",
                "content": contentText,
                "publish_time": timeText,
                "ip_location": ipText,
                "like_count": likeCount,
                "sub_comment_count": subCount,
                "post_id": postId,
                "user_id": "",
                "user_nickname": authorName,
                "user_avatar": avatarUrl
            })

            # 循环遍历并解析二级子回复
            for subItem in subItems:
                subId = subItem.xpath("@data-comment-id").get() or ""
                subId = "".join([c for c in subId if c.isdigit()])
                if not subId:
                    continue

                subContentNodes = subItem.xpath(".//div[contains(@class, 'comment-main-list-item-content-comment')]/text() | .//div[contains(@class, 'comment-main-list-item-content-comment')]//span/text()").getall()
                subContent = "".join([n.strip() for n in subContentNodes]).strip()

                subAuthor = subItem.xpath(".//div[contains(@class, 'comment-main-list-item-content-header-child')]//h4[contains(@class, 'display-name')]/a/text()").get()
                if not subAuthor:
                    subAuthor = subItem.xpath(".//div[contains(@class, 'comment-main-list-item-content-header-child')]//h4[contains(@class, 'display-name')]/text()").get()
                subAuthor = (subAuthor or "").strip()

                subAvatar = subItem.xpath(".//div[contains(@class, 'avatar')]//img/@src | .//img[contains(@class, 'avatar')]/@src").get() or ""

                subInfoSpans = subItem.xpath(".//div[contains(@class, 'comment-main-list-item-content-info')]//div[contains(@class, 'content-info')]/span/text()").getall()
                if not subInfoSpans:
                    subInfoSpans = subItem.xpath(".//div[contains(@class, 'comment-main-list-item-content-info')]/span/text()").getall()

                subTime = ""
                subIp = ""
                if subInfoSpans:
                    subInfoSpans = [s.strip() for s in subInfoSpans if s.strip()]
                    if len(subInfoSpans) >= 1:
                        subTime = subInfoSpans[0]
                    if len(subInfoSpans) >= 2:
                        subIp = subInfoSpans[-1]
                        if subIp == subTime:
                            subIp = ""

                subLikeText = subItem.xpath(".//div[contains(@class, 'J_zan')]//span/text()").get() or "0"
                subLikeCount = int("".join([c for c in subLikeText if c.isdigit()]) or 0)

                commentsList.append({
                    "comment_id": subId,
                    "parent_comment_id": commentId,
                    "content": subContent,
                    "publish_time": subTime,
                    "ip_location": subIp,
                    "like_count": subLikeCount,
                    "sub_comment_count": 0,
                    "post_id": postId,
                    "user_id": "",
                    "user_nickname": subAuthor,
                    "user_avatar": subAvatar
                })

        return commentsList
