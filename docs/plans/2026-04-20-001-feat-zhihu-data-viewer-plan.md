---
title: 知乎数据展示标签页
type: feat
status: completed
date: 2026-04-20
origin: docs/brainstorms/2026-04-20-zhihu-data-viewer-requirements.md
---

# 知乎数据展示标签页

## Overview

在前端添加知乎标签页，复用小红书的卡片式布局展示已爬取的知乎回答数据。新增知乎 API 路由，支持数据列表、统计、筛选等功能。

## Problem Frame

用户已成功爬取知乎数据（25条回答），但现有前端只能展示小红书数据。需要添加知乎标签页，让用户可以浏览知乎内容。

## Requirements Trace

- R1. 前端新增"知乎"标签页 → Unit 2
- R2. 知乎内容以卡片列表形式展示 → Unit 2
- R3. 卡片显示用户信息、回答摘要、互动数据 → Unit 2
- R4. 点击卡片可查看完整回答 → Unit 3
- R5. 新增知乎数据 API `/api/zhihu/notes` → Unit 1
- R6. 新增知乎统计 API `/api/zhihu/stats` → Unit 1
- R7. 支持按创作者筛选 → Unit 1
- R8. 知乎卡片使用知乎品牌色 → Unit 2
- R9. 与小红书界面风格保持一致 → Unit 2

## Scope Boundaries

- 只支持"回答"类型内容，不支持文章、视频
- 不支持知乎图片/视频下载
- 不支持评论展示

## Context & Research

### Relevant Code and Patterns

- **API 路由模式**: `api/routers/notes.py` - 小红书 API 实现，包含 JSONL 读取、分页、筛选
- **前端架构**: `viewer/static/` - 纯 HTML/CSS/JS，无框架
- **数据存储**: `data/zhihu/jsonl/creator_contents_2026-04-20.jsonl` - 已有知乎数据
- **API 封装**: `viewer/static/js/api.js` - fetch 封装模式
- **CSS 变量**: `style.css` 使用 `:root` 定义主题变量

### Data Structure

知乎回答数据字段：
- `content_id`: 回答ID（主键）
- `content_type`: "answer"
- `content_text`: 回答完整内容
- `content_url`: 回答链接
- `question_id`: 问题ID
- `desc`: 回答摘要（用于卡片展示）
- `created_time`: 创建时间戳
- `voteup_count`: 点赞数
- `comment_count`: 评论数
- `user_nickname`: 用户昵称
- `user_avatar`: 用户头像URL
- `user_url_token`: 用户 URL token（用于创作者筛选）

## Key Technical Decisions

- **复用小红书 API 结构**: 知乎 API 路由结构与 `notes.py` 保持一致
- **标签页切换**: 使用纯 CSS/JS 实现标签页，无需引入框架
- **知乎品牌色**: 定义 CSS 变量 `--zhihu-primary: #0066FF`
- **文本优先卡片**: 知乎卡片采用文本优先布局，区别于小红书的图片优先布局
- **ARIA 可访问性**: 标签导航实现完整的 ARIA 属性和键盘导航

## Implementation Units

- [ ] **Unit 1: 创建知乎 API 路由**

**Goal:** 创建知乎数据 API 接口，支持列表、统计、筛选

**Requirements:** R5, R6, R7

**Dependencies:** None

**Files:**
- Create: `api/routers/zhihu.py`
- Modify: `api/routers/__init__.py`
- Modify: `api/main.py`

**Approach:**
- 复用 `notes.py` 的结构，适配知乎数据字段
- 读取 `data/zhihu/jsonl/` 目录下所有 JSONL 文件并合并
- 支持按 `creator` 参数筛选（对应 `user_url_token` 字段）
- 在 `__init__.py` 中导出 `zhihu_router`
- 在 `main.py` 中注册路由

**Patterns to follow:**
- `api/routers/notes.py` - API 结构、分页、JSONL 读取

**Test scenarios:**
- Happy path: GET /api/zhihu/notes 返回知乎回答列表（200 OK）
- Happy path: GET /api/zhihu/stats 返回统计数据
- Happy path: GET /api/zhihu/notes?creator=xxx 按创作者筛选
- Edge case: 空数据目录时返回空列表
- Error path: 无效的 creator 参数时返回空列表

**Verification:**
- GET /api/zhihu/notes 返回 200 OK，包含 25 条回答
- GET /api/zhihu/stats 返回正确的统计数据
- 访问 http://localhost:8080/docs 可看到知乎 API

---

- [ ] **Unit 2: 添加知乎前端标签页和卡片展示**

**Goal:** 在前端添加知乎标签页，以卡片形式展示知乎回答

**Requirements:** R1, R2, R3, R8, R9

**Dependencies:** Unit 1

**Files:**
- Modify: `viewer/static/index.html`
- Modify: `viewer/static/css/style.css`
- Create: `viewer/static/js/zhihu-api.js`
- Create: `viewer/static/js/zhihu-app.js`

**Approach:**

**标签导航设计:**
- 在 header 添加平台切换标签（小红书/知乎）
- ARIA 属性：`role="tablist"`, `role="tab"`, `aria-selected`
- 键盘导航：左右箭头切换标签
- 交互状态：
  - Active: 底部蓝色下划线 + 加粗文字
  - Hover: 文字颜色渐变
  - Focus: 2px 蓝色 focus ring

**知乎卡片设计（文本优先）:**
- 布局：水平卡片，左侧内容区，右侧可选缩略图
- 内容区：
  - 回答摘要（截断 150 字符）
  - 用户头像 + 昵称
  - 点赞数 + 评论数
- 品牌色：左边框 4px `#0066FF`
- 响应式：700px 以下切换为垂直布局

**CSS 变量:**
```css
--zhihu-primary: #0066FF;
--zhihu-light: #E8F3FF;
```

**筛选器适配:**
- 小红书标签：关键词筛选 + 搜索
- 知乎标签：创作者筛选 + 搜索

**Patterns to follow:**
- `viewer/static/js/app.js` - 数据加载、卡片渲染模式
- `viewer/static/css/style.css` - 卡片样式、响应式断点

**Test scenarios:**
- Happy path: 点击知乎标签显示知乎数据
- Happy path: 卡片显示用户头像、昵称、回答摘要、互动数据
- Happy path: Tab 键导航标签，箭头键切换
- Edge case: 无知乎数据时显示空状态
- Edge case: 700px 以下响应式布局正确

**Verification:**
- 标签页可切换，知乎数据正确展示
- 键盘导航正常工作
- 响应式布局在 700px 以下正确

---

- [ ] **Unit 3: 添加知乎详情模态框**

**Goal:** 点击知乎卡片显示完整回答内容

**Requirements:** R4

**Dependencies:** Unit 1, Unit 2

**Files:**
- Modify: `viewer/static/index.html`
- Create: `viewer/static/js/zhihu-modal.js`

**Approach:**

**模态框结构:**
- 问题标题（如果有）或 "知乎回答"
- 完整回答文本（保留换行格式）
- 用户信息：头像 + 昵称 + IP 属地
- 互动数据：点赞数 + 评论数
- 原链接按钮：跳转到知乎

**交互:**
- 点击卡片打开模态框
- ESC 键关闭
- 点击遮罩关闭
- 长文本滚动

**Patterns to follow:**
- `viewer/static/js/modal.js` - 模态框交互模式

**Test scenarios:**
- Happy path: 点击卡片打开模态框显示完整回答
- Happy path: 点击原链接跳转到知乎
- Edge case: ESC 键关闭模态框
- Edge case: 长回答文本可滚动
- Edge case: 缺失用户头像显示占位符

**Verification:**
- 点击卡片可查看完整回答内容
- 所有交互正常工作

## System-Wide Impact

- **API 扩展**: 新增 `/api/zhihu/*` 路由，不影响现有 `/api/notes/*`
- **前端扩展**: 新增标签页，不影响小红书展示功能
- **CSS 扩展**: 新增知乎相关 CSS 类和变量，不覆盖现有样式

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| 知乎数据格式变化 | 使用与爬虫一致的模型字段 |
| 长文本渲染性能 | 截断摘要，完整内容在模态框展示 |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-04-20-zhihu-data-viewer-requirements.md](docs/brainstorms/2026-04-20-zhihu-data-viewer-requirements.md)
- Related code: `api/routers/notes.py`, `viewer/static/js/app.js`, `viewer/static/js/modal.js`
