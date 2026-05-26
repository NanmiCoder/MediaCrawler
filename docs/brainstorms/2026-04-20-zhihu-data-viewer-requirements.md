---
date: 2026-04-20
topic: zhihu-data-viewer
---

# 知乎数据展示专栏

## Problem Frame

用户已经成功爬取了知乎数据（用户回答、文章等），现有前端只能展示小红书数据。需要在前端添加知乎专栏，让用户可以浏览已爬取的知乎内容。

## Requirements

**数据展示**
- R1. 前端新增"知乎"标签页，与"小红书"标签并列
- R2. 知乎内容以卡片列表形式展示（类似小红书的瀑布流布局）
- R3. 卡片显示：用户头像、昵称、回答摘要、点赞数、评论数、时间
- R4. 点击卡片可查看完整回答内容

**后端支持**
- R5. 新增知乎数据 API 接口 `/api/zhihu/notes`
- R6. 新增知乎统计 API 接口 `/api/zhihu/stats`
- R7. 支持按创作者筛选

**UI/UX**
- R8. 知乎卡片使用知乎品牌色（蓝色 #0066FF）
- R9. 与小红书界面风格保持一致

## Success Criteria

- 用户可以切换到知乎标签页查看已爬取的知乎数据
- 知乎数据以卡片形式正确展示
- 点击卡片可以看到完整的回答内容

## Scope Boundaries

- 本次只支持"回答"类型内容展示，暂不支持文章、视频
- 暂不支持知乎图片/视频下载（爬虫已禁用媒体下载）
- 暂不支持评论爬取和展示

## Key Decisions

- 复用小红书的前端架构（纯 HTML/CSS/JS），添加知乎相关模块
- 知乎数据存储在 `data/zhihu/jsonl/` 目录，与小红书类似

## Data Structure

知乎回答数据字段：
```json
{
  "content_id": "回答ID",
  "content_type": "answer",
  "content_text": "回答内容",
  "content_url": "回答链接",
  "question_id": "问题ID",
  "title": "",
  "desc": "回答摘要",
  "created_time": 1234567890,
  "voteup_count": 10,
  "comment_count": 2,
  "user_nickname": "用户昵称",
  "user_avatar": "用户头像URL"
}
```

## Next Steps

→ /ce:plan 进行技术实现规划
