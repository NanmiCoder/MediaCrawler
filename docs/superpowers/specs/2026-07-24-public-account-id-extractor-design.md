# 公开笔记作者 ID 提取器设计

> 日期：2026-07-24
>
> 状态：已确认，待实施
> 范围：阶段一，仅处理人工确认后的公开笔记

## 1. 目标

在 `D:\red_note_rich_search` 下新增一个独立的小工具，从人工审核通过的公开小红书笔记 JSON 中提取笔记作者的公开 `user_id`，并生成公开主页链接，供后续 MediaCrawler 创作者模式使用。

本阶段只打通以下链路：

```text
人工审核后的笔记 JSON
  -> 读取 accepted 记录
  -> 复用 MediaCrawler 获取笔记详情
  -> 提取公开作者 user_id
  -> 生成公开主页链接
  -> 输出 JSON
```

## 2. 非目标

本阶段不实现：

- AI 初筛或复筛。
- 创作者全部笔记采集。
- 目标账号数据库。
- WebUI 审核页面。
- 作者主页详情采集。
- 评论用户 ID 采集。
- 跨平台身份匹配、联系方式提取或自动营销触达。
- 修改 MediaCrawler 当前匿名内容存储逻辑。

## 3. 目录与运行边界

新增独立目录：

```text
D:\red_note_rich_search\public_account_id_extractor
├── extract_ids.py
├── reviewed_notes.json
├── extracted_ids.json
└── README.md
```

工具代码与输入、输出文件放在独立目录中，但运行时复用相邻 `MediaCrawler` 项目的代码和虚拟环境，不复制小红书登录、签名、Cookie、CDP 或请求实现。

推荐运行方式：

```powershell
cd D:\red_note_rich_search\MediaCrawler

uv run python `
  ..\public_account_id_extractor\extract_ids.py `
  --input ..\public_account_id_extractor\reviewed_notes.json `
  --output ..\public_account_id_extractor\extracted_ids.json
```

## 4. 输入格式

输入文件为 UTF-8 JSON 数组。每条记录至少包含：

```json
[
  {
    "note_id": "公开笔记 ID",
    "note_url": "https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search",
    "source_keyword": "重庆企业主资产配置",
    "review_status": "accepted",
    "suspected_marketing": false
  }
]
```

处理条件：

```text
review_status == "accepted"
AND suspected_marketing == false
AND note_url 非空
```

其他记录必须跳过，不尝试获取作者 ID。

`note_url` 应保留搜索结果中的 `xsec_token` 和 `xsec_source` 参数，以复用 MediaCrawler 现有笔记详情获取逻辑。

## 5. 输出格式

输出文件为 UTF-8 JSON 对象：

```json
{
  "results": [
    {
      "note_id": "公开笔记 ID",
      "public_user_id": "公开作者 ID",
      "profile_url": "https://www.xiaohongshu.com/user/profile/公开作者ID",
      "source_keyword": "重庆企业主资产配置",
      "evidence_note_url": "公开笔记链接",
      "extracted_at": "2026-07-24T16:00:00+08:00"
    }
  ],
  "errors": [
    {
      "note_id": "失败的笔记 ID",
      "note_url": "失败的笔记链接",
      "error": "简短错误原因"
    }
  ]
}
```

本阶段的输出只是后续流程的中间文件，不承担正式账号库、人工终审或长期保存职责。

## 6. 复用 MediaCrawler 的方式

新工具定义一个继承 `media_platform.xhs.core.XiaoHongShuCrawler` 的轻量适配器。

适配器复用：

- `CDPBrowserManager` 连接 Chrome 9222 调试端口。
- MediaCrawler 的浏览器上下文和 Cookie 转换。
- `XiaoHongShuClient` 的请求签名和笔记详情接口。
- `parse_note_info_from_note_url()` 解析笔记链接。
- `get_note_detail_async_task()` 获取原始笔记详情。
- 现有登录状态检查和二维码登录回退流程。

适配器只覆盖详情模式的结果处理：获取原始笔记详情后读取 `note_detail["user"]["user_id"]`，生成主页链接并写入本工具的结果集合，不调用 `store.xhs.update_xhs_note()`。

因此，MediaCrawler 当前将原始 ID 转为 `creator_hash` 的匿名存储流程及其测试保持不变。

## 7. 数据流

1. 解析命令行中的输入、输出路径。
2. 校验输入文件存在且顶层为 JSON 数组。
3. 过滤出人工审核通过且非营销的记录。
4. 对 `note_url` 去重，避免重复访问同一笔记。
5. 将 MediaCrawler 配置为小红书详情模式、关闭评论和媒体下载。
6. 通过 MediaCrawler 连接已启用远程调试的 Chrome。
7. 对每条通过审核的笔记调用现有详情获取方法。
8. 从原始详情读取公开作者 ID。
9. 生成公开主页链接并保留来源关键词和证据笔记链接。
10. 将成功和失败结果一次性写入输出 JSON。
11. 正常关闭本工具创建的页面和 MediaCrawler 客户端；不主动关闭用户已有的 Chrome。

## 8. 访问控制与节流

- 只访问输入中已人工确认的公开笔记。
- 默认串行处理，避免新增并发压力。
- 沿用 MediaCrawler 的请求间隔配置。
- 不访问生成的作者主页链接。
- 不请求评论接口。
- 不下载图片或视频。
- 不输出 Cookie、请求头、签名参数或登录凭证。

## 9. 错误处理

以下错误只记录到 `errors`，不终止整个批次：

- 输入记录缺少 `note_url`。
- 链接无法解析笔记 ID。
- 笔记已删除、不可见或接口返回空结果。
- 原始详情缺少 `user.user_id`。
- 单条请求超时或平台临时拒绝。

以下错误应立即失败并返回非零退出码：

- 输入文件不存在或不是合法 JSON。
- 输入 JSON 顶层不是数组。
- MediaCrawler 项目无法导入。
- 无法连接 Chrome 9222 且登录流程无法建立可用浏览器上下文。
- 输出目录不可写。

即使批次中存在单条错误，只要初始化和输出成功，程序仍以成功状态结束，并在控制台汇总成功、跳过和失败数量。

## 10. 去重与幂等

本阶段按 `note_url` 去重输入，并按 `(note_id, public_user_id)` 去重结果。

重复运行时重新生成完整输出文件，而不是追加旧结果。这样不需要引入数据库、状态文件或增量同步逻辑，也避免一次失败留下半写入文件。

输出应先写入同目录临时文件，写入成功后再原子替换目标文件，防止中断导致 JSON 损坏。

## 11. 测试与验收

至少提供以下自动化检查：

1. 只选择 `accepted` 且非营销的记录。
2. 拒绝非数组 JSON 输入。
3. 重复笔记链接只处理一次。
4. 能从模拟笔记详情提取 `user.user_id` 并生成主页链接。
5. 缺少 `user_id` 时写入单条错误而不中断后续记录。
6. 输出不包含 Cookie、手机号、微信、住址或评论用户信息。

人工验收使用一条已确认的公开笔记：

1. Chrome 9222 连接成功。
2. 工具仅请求该笔记详情。
3. 输出包含正确的 `public_user_id`、`profile_url` 和证据笔记链接。
4. MediaCrawler 原有匿名存储测试继续通过。
5. 工具不会打开或采集作者主页详情。

## 12. 后续接口

阶段一输出的 `public_user_id` 可在后续阶段转换为 MediaCrawler 创作者模式输入：

```text
https://www.xiaohongshu.com/user/profile/{public_user_id}
```

后续阶段可以读取 `extracted_ids.json`，调用现有创作者模式抓取公开笔记，再进行 AI 复筛和人工终审。该能力不在本阶段实现。

## 13. 使用边界

- 仅用于个人、非商业研究。
- 仅处理公开笔记及其公开发布者标识。
- 不依据笔记内容断言作者的真实职业、资产、身份或意图。
- 不用于自动营销、联系人挖掘或跨平台真人匹配。
- 输入和输出仅保存在本机，不提交 Git，不上传公共云盘。
- 研究结束后删除不再需要的账号级中间数据。
