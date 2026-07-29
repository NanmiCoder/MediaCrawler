# 小红书风控暂停与部分结果保存设计

## 1. 背景

关键词队列当前通过本地 API 为每个关键词启动一个独立的 MediaCrawler 子进程。runner 只根据子进程退出码判断结果：退出码为 `0` 时标记为 `succeeded`，其他退出码一律标记为 `failed`。

小红书搜索列表请求成功后，MediaCrawler 会并发获取笔记详情。当前实现等待全部详情请求完成后才统一写入 JSON。当任意详情请求持续返回 `461/471` 时，程序最多等待人工验证 5 分钟；如果风控仍未解除，`CaptchaRequiredError` 会中断整批请求。即使部分详情已经获取成功，它们也可能尚未进入保存循环。子进程随后以非零退出码结束，runner 将整个关键词标记为普通失败。

另外，`461/471` 只表示后台接口要求验证或触发风险控制，并不保证普通搜索页面会呈现可操作的滑块或验证码。当前打开搜索页的行为只能帮助人工观察，不能被视为验证一定可完成。

## 2. 目标

本次改造采用“结构化风控状态 + 增量保存”方案，目标如下：

1. 每条笔记详情成功获取后尽快写入 JSON，避免后续风控导致已获取结果丢失。
2. 将风控超时与普通程序失败区分开，使用 `needs_review` 表示需要人工确认。
3. runner 遇到 `needs_review` 后立即保存进度并暂停整个队列，不再启动后续关键词。
4. API 返回本轮实际保存数量、目标数量和停止原因，不再只暴露退出码。
5. 保留现有每词 20 条、关闭评论、串行执行关键词、JSON 输出和断点续跑行为。
6. 不自动识别、点击或绕过验证码，也不尝试规避平台风险控制。

## 3. 非目标

本次不实现以下内容：

- 不把 MediaCrawler 攚造成长期驻留的关键词工作进程。
- 不让多个关键词并行采集。
- 不自动处理滑块、扫码或其他验证。
- 不根据输出文件内容猜测任务状态。
- 不改变关键词 JSON 格式。
- 不增加数据库或 Excel 输出。
- 不解决关键词重跑时的业务去重；继续沿用现有 `(note_id, source_keyword)` 去重约定。

## 4. 状态模型

### 4.1 子进程结果

子进程结果分为三类：

| 结果 | 含义 | 退出码 |
|---|---|---:|
| `succeeded` | 本轮正常完成 | `0` |
| `needs_review` | 遇到 `461/471`，人工等待结束后仍未恢复 | `2` |
| `failed` | 参数错误、启动失败、未处理异常等普通失败 | 其他非零值 |

退出码 `2` 只用于受控的人工复核结果，不用于一般异常。

### 4.2 API 任务状态

API 的运行状态继续使用 `running`、`stopping` 和 `idle`。子进程结束后 API 回到 `idle`，并通过新增的结果字段描述刚刚结束的任务：

```json
{
  "status": "idle",
  "task_id": "c3e6ff24-3811-47fb-9a80-07224b0aa4dc",
  "last_exit_code": 2,
  "outcome": "needs_review",
  "saved_count": 8,
  "expected_count": 20,
  "stop_reason": "captcha_or_risk_control",
  "error_message": "后台接口持续返回 461/471，人工验证等待超时",
  "finished_at": "2026-07-29T15:22:10+08:00"
}
```

API 保持 `idle` 是为了表明子进程已经结束，避免把“需要人工复核”误解为仍有任务占用 API。runner 负责根据 `outcome` 暂停队列。

### 4.3 runner 进度状态

runner 为每个关键词继续使用 `pending`、`running`、`succeeded`、`failed` 和 `needs_review`。`needs_review` 项新增以下可选字段：

```json
{
  "keyword": "重庆别墅装修",
  "status": "needs_review",
  "attempts": 3,
  "saved_count": 8,
  "expected_count": 20,
  "stop_reason": "captcha_or_risk_control",
  "error": "检测到风控，已保存 8/20 条，队列已暂停"
}
```

这些字段必须进行类型校验。布尔值不能作为整数数量接受；数量不得为负数，且 `saved_count` 不得大于 `expected_count`。

## 5. MediaCrawler 数据流

### 5.1 搜索与增量保存

搜索列表仍一次获取最多 20 个候选笔记。详情请求保留当前并发限制，但每个详情任务完成后必须在保存锁内执行以下操作：

1. 验证详情结果非空。
2. 调用现有 `xhs_store.update_xhs_note` 写入 JSON。
3. 完成媒体保存逻辑（仅在现有配置开启时）。
4. 将本轮 `saved_count` 增加 1。

保存锁只保护写入和计数，不包围网络请求，避免把现有详情并发退化为串行。不得引入新的第三方依赖。

### 5.2 并发任务收尾

当某个详情任务在 5 分钟等待后仍抛出 `CaptchaRequiredError` 时：

1. 取消本页尚未完成的其他详情任务。
2. 等待这些任务完成取消，防止后台遗留任务继续请求。
3. 保留此前已经成功写入的记录。
4. 生成受控的 `needs_review` 结果。
5. 执行现有浏览器和数据库清理。
6. 子进程以退出码 `2` 结束。

如果单条笔记是已删除、不可见或普通 `DataFetchError`，沿用现有“记录并跳过”的行为，不把它升级为整词 `needs_review`。只有明确的 `CaptchaRequiredError` 才触发整队暂停。

### 5.3 验证页面行为

首次收到 `461/471` 时继续执行以下行为：

- 将专用 Chrome 页面置前；
- 打开当前关键词的官方搜索页；
- 日志明确说明“后台接口触发风控，页面不一定显示验证码”；
- 记录响应中的 `Verifytype` 和 `Verifyuuid`（若存在）；
- 每次重试前继续刷新 Cookie、重新生成签名。

仍保留最长 5 分钟人工处理窗口。程序只等待用户自行完成平台提供的验证，不自动操作验证控件。5 分钟内接口恢复则继续本轮；超时则进入 `needs_review`。

## 6. 子进程到 API 的结果传递

采用标准输出中的单行机器结果，不新增临时文件或数据库表。子进程在受控结束前输出一个固定前缀的 JSON 行，例如：

```text
MEDIACRAWLER_RESULT:{"outcome":"needs_review","saved_count":8,"expected_count":20,"stop_reason":"captcha_or_risk_control","error_message":"..."}
```

约束如下：

- JSON 使用单行格式；中文按 UTF-8 输出。
- API 进程只解析精确匹配固定前缀的行，其他日志保持原样。
- API 对字段进行严格类型和值域校验，不信任子进程输出。
- 合法结果保存到当前任务状态；畸形结果忽略并记录警告。
- 退出码 `2` 但缺少合法机器结果时，API 仍返回 `outcome = needs_review`，数量字段为 `null`，避免错误地降级为普通失败。
- 其他非零退出码即使携带未知结果，也按 `failed` 处理。

该方式复用现有 stdout 读取链路，避免增加跨进程结果文件的创建、清理和并发命名问题。

## 7. runner 行为

runner 轮询到 API `status = idle` 后按以下顺序处理：

1. 校验 `task_id` 与进度文件一致。
2. 校验 `last_exit_code`、`outcome` 和数量字段。
3. `outcome = succeeded`：标记 `succeeded`，继续下一个关键词。
4. `outcome = needs_review`：写入数量与停止原因，标记 `needs_review`，原子保存进度，立即退出队列，返回现有的人工复核退出码 `2`。
5. `outcome = failed`：标记 `failed`，沿用当前“记录失败后继续”的策略。

兼容规则：如果 API 暂未返回 `outcome`，runner 继续按退出码判断；退出码 `0` 视为成功，退出码 `2` 视为 `needs_review`，其他非零值视为失败。

`--retry-failed` 仍然只重置 `failed`，不得自动重置 `needs_review`。人工处理后继续沿用现有安全流程：检查输出与进度文件，再明确决定将该项改为 `succeeded` 或 `failed`；只有改为 `failed` 后才可通过 `--retry-failed` 重跑。

## 8. 异常与边界条件

- 搜索列表请求本身触发风控且尚未保存任何详情：`saved_count = 0`，状态仍为 `needs_review`。
- 已保存部分详情后触发风控：保留数据并准确报告数量。
- 20 条全部保存后，清理阶段发生普通异常：不得误报为 `needs_review`，按现有失败规则处理并保留数据。
- API 在任务结束前重启或连接中断：runner 沿用现有 `needs_review` 安全停队规则，不猜测结果。
- 进度文件中的数量字段畸形：拒绝加载，防止错误续跑。
- 多个并发详情任务同时收到风控：只生成一次任务级 `needs_review` 结果和一次用户提示。
- 用户中断 runner 不会自动停止 API 中已启动的爬虫任务；恢复时仍先按 `task_id` 接管正在运行的任务。

## 9. 测试策略

### 9.1 MediaCrawler

新增或调整聚焦测试，至少覆盖：

1. 部分详情成功后另一个详情触发 `CaptchaRequiredError`，成功详情已经写入。
2. 风控发生后未完成任务被取消并回收。
3. 风控超时生成退出码 `2` 和合法机器结果。
4. 机器结果只输出一次。
5. `Verifytype`、`Verifyuuid` 缺失时仍能进入 `needs_review`。
6. 普通 `DataFetchError` 不触发整词暂停。
7. 完全成功仍返回退出码 `0`。
8. 现有 CAPTCHA 等待、Cookie 刷新、签名刷新和页面呈现测试继续通过。

### 9.2 API

至少覆盖：

1. 解析合法 `MEDIACRAWLER_RESULT` 行。
2. 拒绝畸形 JSON、负数、布尔数量和未知 outcome。
3. 退出码 `2` 映射为 `needs_review`。
4. 退出码 `2` 且机器结果缺失时使用安全回退。
5. 退出码 `0` 与其他非零退出码保持原行为。

### 9.3 runner

至少覆盖：

1. `needs_review` 保存进度并停止后续关键词。
2. 部分数量正确写入进度文件。
3. `--retry-failed` 不重置 `needs_review`。
4. 缺少 `outcome` 时按退出码兼容。
5. 畸形结果进入 `needs_review` 安全停队，而不是继续执行。
6. 原有 40 个 runner 回归测试继续通过。

## 10. 验收标准

在一个包含至少两个关键词的测试队列中，模拟第一个关键词保存 8 条后触发持续风控，应满足：

1. JSON 中保留第一个关键词已成功获取的 8 条详情。
2. API 最终为 `idle`，且最后结果为 `outcome = needs_review`、`saved_count = 8`、`expected_count = 20`。
3. runner 将第一个关键词标记为 `needs_review` 并原子保存进度。
4. 第二个关键词保持 `pending`，没有调用启动 API。
5. runner 以人工复核退出码 `2` 结束。
6. 日志不声称一定存在可见验证码，并包含可用的风控诊断信息。
7. 全部现有聚焦测试与新增测试通过。

## 11. 实施范围

预计只修改以下现有区域，不引入新服务或第三方依赖：

- `media_platform/xhs/client.py`：风控诊断与受控异常信息。
- `media_platform/xhs/core.py`：详情增量保存、取消与任务结果计数。
- `main.py`：输出受控机器结果并使用退出码 `2`。
- `api/services/crawler_manager.py`：解析子进程结果并扩展最后任务状态。
- `api/schemas.py` 或对应响应模型：增加可选结果字段。
- `keyword_crawl_runner/run_keywords.py`：识别 `needs_review`、保存数量并暂停。
- 两个项目的相关测试和中文使用说明。

实现必须测试先行，且不得修改用户现有的未跟踪研究文档。
