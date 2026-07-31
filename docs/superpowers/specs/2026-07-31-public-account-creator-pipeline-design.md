# 公开作者 ID 到 Creator 模式自动化设计

> 日期：2026-07-31
>
> 状态：已确认，待实施
> 前置设计：`2026-07-24-public-account-id-extractor-design.md`

## 1. 目标

在不改变 MediaCrawler 匿名存储逻辑的前提下，把以下研究链路放进同一个命令：

```text
人工确认且非营销的公开笔记 JSON
  -> 获取公开笔记详情
  -> 提取 note_detail["user"]["user_id"]
  -> 去重并原子写出作者 ID 清单
  -> 在同一登录会话中调用现有 creator 模式
  -> 保存这些作者的公开笔记
```

## 2. 实现位置与命令

新增：

```text
MediaCrawler/tools/public_account_creator_pipeline.py
MediaCrawler/tests/test_public_account_creator_pipeline.py
```

从 `MediaCrawler` 目录运行：

```powershell
uv run python -m tools.public_account_creator_pipeline `
  --input ..\public_account_id_extractor\reviewed_notes.json `
  --output ..\public_account_id_extractor\extracted_ids.json `
  --creator-max-notes 50
```

不新增第三方依赖、数据库、WebUI 或常驻服务。

## 3. 输入与筛选

输入是 UTF-8 JSON 数组。仅处理同时满足以下条件的记录：

```text
review_status == "accepted"
AND suspected_marketing == false
AND note_url 非空
```

每条记录可包含 `note_id`、`note_url`、`source_keyword`、`review_status` 和
`suspected_marketing`。重复 `note_url` 只请求一次。输入文件不存在、JSON 非法或顶层
不是数组时，命令立即以非零状态结束。

## 4. 输出

提取阶段完成后，先将结果写入输出文件同目录的临时文件，再使用原子替换生成：

```json
{
  "results": [
    {
      "note_id": "公开笔记 ID",
      "public_user_id": "24 位公开用户 ID",
      "profile_url": "https://www.xiaohongshu.com/user/profile/公开用户ID",
      "source_keyword": "来源关键词",
      "evidence_note_url": "公开笔记链接",
      "extracted_at": "带时区的 ISO 8601 时间"
    }
  ],
  "errors": [
    {
      "note_id": "失败笔记 ID",
      "note_url": "失败笔记链接",
      "error": "简短错误原因"
    }
  ]
}
```

输出不得包含 Cookie、请求头、签名、手机号、微信、住址或评论用户信息。结果按
`(note_id, public_user_id)` 去重；用于 creator 阶段的作者列表按 `public_user_id` 去重。

## 5. 复用现有爬虫

新增模块提供一个 `XiaoHongShuCrawler` 的轻量子类。它复用父类的浏览器初始化、
登录状态、请求签名、`get_note_detail_async_task()`、`get_creators_and_notes()` 和关闭
流程。子类只覆盖本次任务入口：

1. 串行获取通过筛选的笔记详情。
2. 从原始详情读取 `user.user_id`，不调用 `store.xhs.update_xhs_note()`。
3. 原子写出提取结果，确保即使 creator 阶段失败，ID 清单仍可用于重试。
4. 将去重后的 24 位 ID 放入 `config.XHS_CREATOR_ID_LIST`。
5. 设置 creator 笔记上限并调用继承的 `get_creators_and_notes()`。

Creator 阶段继续使用当前存储实现，因此作者资料仍不落库，公开笔记中的作者标识仍被
转换为 `creator_hash`。本功能不修改 `store/xhs/__init__.py`。

## 6. 错误、节流与退出状态

- 笔记链接无法解析、详情为空或缺少 `user.user_id`：写入 `errors`，继续下一条。
- 单个作者 creator 抓取失败：记录日志并继续下一位作者；不得丢失已生成的 ID 文件。
- 没有成功提取任何作者：正常写出空 `results`，不启动 creator 阶段。
- 输出不可写或浏览器/登录初始化失败：命令以非零状态结束。
- 默认串行提取；沿用 `CRAWLER_MAX_SLEEP_SEC`，不新增并发。
- 关闭评论和媒体下载；creator 笔记数量由 `--creator-max-notes` 控制，必须为正整数。
- 不主动关闭用户已有的 CDP Chrome，仅清理本工具创建的页面和连接。

## 7. 测试与验收

自动测试覆盖：

1. 只选择 `accepted` 且非营销的记录，并按 URL 去重。
2. 非数组 JSON 输入被拒绝。
3. 从模拟详情提取 24 位 `user_id` 并生成主页链接。
4. 缺失 `user_id` 只产生单条错误，后续记录仍处理。
5. creator 输入按用户 ID 去重。
6. 输出使用临时文件和原子替换，且不泄露敏感字段。
7. 没有提取结果时不调用 creator 方法。
8. 原有匿名存储测试继续通过。

人工验收使用一条已确认的公开笔记，确认输出 ID 正确、creator 阶段保存公开笔记、
评论和媒体没有被请求，且原始 `user_id` 没有进入现有内容存储。

## 8. 使用边界

- 仅用于个人、非商业研究。
- 仅处理人工确认的公开笔记及其公开发布者标识。
- 不采集评论用户 ID，不提取联系方式，不进行跨平台真人匹配或自动营销触达。
- 输入和输出只保存在本机，不提交 Git；研究结束后删除不再需要的账号级中间数据。
