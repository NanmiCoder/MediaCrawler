# 首次捕获作者 ID 与候选 Creator 自动采集设计

> 日期：2026-07-31
>
> 状态：已确认，待实施

## 1. 目标

在第一次关键词搜索成功取得笔记详情时、匿名化存储之前，旁路捕获公开作者的 24 位
`user_id`。AI 粗筛完成后，只保留 `potential_customer` 且证据等级为 `strong` 或
`medium` 的候选作者，将其与旁路 ID 映射关联，并自动调用现有 creator 模式采集候选
作者主页下的公开笔记。

```text
关键词搜索取得原始 note_detail
  ├─ 现有匿名存储：creator_hash + 笔记内容
  └─ 本地临时映射：note_id + creator_hash + user_id
                     ↓
AI 粗筛（不接收 user_id）
  -> potential_customer + strong/medium
  -> 关联本地临时映射
  -> candidate_creators.json（含 user_id）
  -> 自动调用 creator 模式
  -> 保存候选作者的公开笔记，供第二轮 AI 筛选
```

主流程不依赖粗筛后重新获取旧笔记详情，因此不会因原笔记 `xsec_token` 过期而丢失
作者 ID。

## 2. 候选规则

候选证据笔记必须同时满足：

```text
status in {"screened", "cached"}
AND label == "potential_customer"
AND evidence_level in {"strong", "medium"}
AND evidence_quotes 为非空字符串数组
```

只有至少包含一条上述证据笔记的作者才进入 `candidate_creators.json`。`weak`、`none`、
`service_provider`、`media_or_educator`、`unclear` 和 `irrelevant` 不进入候选列表。

这仍是内容证据驱动的研究候选，不是对作者真实身份、资产、职业或意图的事实判断。

## 3. 首次抓取时捕获 ID

新增一个默认关闭的研究开关。关键词运行器通过 API 启动小红书搜索时显式开启；普通
MediaCrawler 命令、详情模式、creator 模式和其他平台不捕获原始 ID。

捕获点位于 `media_platform/xhs/core.py`：`get_note_detail_async_task()` 已返回完整
`note_detail`，但尚未调用 `store.xhs.update_xhs_note()`。捕获记录只包含：

```json
{
  "note_id": "公开笔记 ID",
  "creator_hash": "与匿名笔记一致的 SHA-256 截断值",
  "public_user_id": "24 位公开用户 ID",
  "profile_url": "https://www.xiaohongshu.com/user/profile/公开用户ID",
  "captured_at": "带时区的 ISO 8601 时间"
}
```

不保存昵称、头像、简介、IP、Cookie、请求头、签名、评论用户或联系方式。记录按
`(note_id, public_user_id)` 幂等写入本地私有旁路文件。写入失败应终止该次关键词任务，
避免出现“笔记已保存但 ID 静默丢失”的不一致状态。

现有 `store/xhs/__init__.py` 不修改，搜索内容仍只保存 `creator_hash`。

## 4. API 与关键词运行器

MediaCrawler API 的搜索请求新增布尔字段 `capture_creator_ids`，默认 `false`。进程管理器
只在该值为真时向 `main.py` 传递对应命令行开关。

`keyword_crawl_runner/run_keywords.py` 启动小红书搜索时固定传递
`capture_creator_ids: true`，从而确保本研究流程每次首次取得详情时同步捕获 ID。

旁路文件保存在 MediaCrawler 的本地数据目录中，并按日期生成，便于和
`search_contents_YYYY-MM-DD.json` 对齐。旁路文件加入 `.gitignore`，不得提交 Git。

## 5. AI 粗筛与 ID 关联

`keyword_crawl_runner/screen_data.py` 继续只把匿名笔记内容发送给 AI。原始 `user_id`、
主页链接和旁路映射不得进入提示词、缓存或 `screened_notes.jsonl`。

模型响应全部完成且通过结构校验后：

1. 使用现有 strong/medium 合格判断聚合作者。
2. 丢弃没有合格证据笔记的作者。
3. 通过 `creator_hash` 将候选作者与本地旁路映射关联。
4. 一个哈希对应多个不同 `user_id` 时记录冲突并不自动采集。
5. 缺少映射的候选写入 `candidate_creator_errors.json`，不尝试用旧 token 重抓详情。
6. 成功关联的候选在 `candidate_creators.json` 中增加 `public_user_id` 和 `profile_url`。

候选输出是本地研究中间文件，不上传 AI，不提交 Git。

## 6. 自动 Creator 采集

粗筛命令新增显式开关 `--crawl-creators`。启用时，`screen_data.py` 写完全部筛选输出后：

1. 按 `public_user_id` 去重。
2. 通过现有本地 MediaCrawler API 提交 creator 任务。
3. 关闭评论和媒体下载。
4. 使用 `--creator-max-notes` 控制每位作者的最大公开笔记数，该值必须为正整数。
5. 等待任务结束并把成功、失败和需要人工复核的状态写入运行清单。

未指定 `--crawl-creators` 时只输出候选及 ID，不访问作者主页。显式开关既支持全自动
运行，也保留用户对主页采集时机的控制。

Creator 模式使用新登录态和已捕获的 `user_id`，不再依赖候选证据笔记的旧
`xsec_token`。平台仍可能因登录状态、频率限制或风控拒绝 creator 请求；这种失败应记录
并可重试，但不能回退为手工打开候选笔记恢复 ID。

## 7. 第二轮 AI 筛选

Creator 输出保持 MediaCrawler 现有匿名笔记格式。第二轮 AI 筛选复用现有
`screen_data.py`，通过输入路径或文件匹配模式指向 creator 输出。本阶段不引入新的模型
提示词或对个人身份作额外推断。

## 8. 错误处理与恢复

- 捕获开关关闭：完全保持现有行为。
- 原始详情缺少合法 24 位 `user_id`：记录捕获错误，笔记仍可按匿名流程保存。
- 旁路文件不可写：关键词任务失败，保留已写入的原子记录供重试审计。
- 候选缺少 ID 映射或发生哈希冲突：写入错误文件，不启动该作者的 creator 任务。
- AI 粗筛存在单条失败：不影响其他已验证 strong/medium 候选。
- Creator 单个任务失败：记录状态，后续候选继续处理。
- 输出目录非空等现有安全检查继续生效。

不新增数据库、WebUI、联系人提取、跨平台匹配或自动营销功能。

## 9. 测试与验收

自动测试覆盖：

1. 捕获开关默认关闭，关闭时不写旁路数据。
2. 开启时从原始详情捕获合法 24 位 `user_id`，并生成与现有逻辑一致的
   `creator_hash`。
3. 捕获输出不包含昵称、Cookie、请求头、评论用户等字段。
4. API 只在请求开启捕获时传递命令行参数。
5. 关键词运行器固定开启捕获。
6. 候选只包含 `potential_customer` 的 strong/medium 证据作者。
7. ID 映射不会进入 AI 请求或筛选缓存。
8. 缺失映射和哈希冲突不会启动 creator。
9. `--crawl-creators` 关闭时不访问主页，开启时只提交去重后的候选 ID。
10. Creator 失败被记录且不阻止后续候选。
11. 原有匿名存储与关键词运行器测试继续通过。

人工验收至少执行一条新关键词搜索，确认首次详情阶段生成旁路映射；随后执行粗筛，
确认候选仅含 strong/medium、候选 ID 正确、旧笔记 token 不再被请求，并确认 creator
输出可作为第二轮 AI 筛选输入。

## 10. 使用与数据边界

- 仅用于个人、非商业研究和公开内容分析。
- 候选结论只表示公开内容证据满足筛选规则，不表示个人事实。
- 不采集评论用户 ID、联系方式、非公开主页信息或跨平台身份。
- 旁路映射和候选 ID 仅保存在本机，不提交 Git；研究结束后删除不再需要的数据。
