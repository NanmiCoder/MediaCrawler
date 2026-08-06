# 关键词 JSON 队列与 Chrome 稳定连接升级设计

> 日期：2026-07-27
>
> 状态：设计已确认，待用户审核书面规格

## 1. 背景与目标

现有外部工具（GitHub 仓库 `mediaClawerTooler`，本地目录 `keyword_crawl_runner`）已能从固定 Markdown 读取20个关键词，逐词调用 MediaCrawler API，并通过 JSON 进度文件断点恢复。第一轮运行暴露了三个限制：输入被固定为20个词、Chrome 136+ 直接 CDP 连接会为每个爬虫子进程重复请求人工授权、验证码出现后现有三次短重试会在用户完成验证前退出。

本次升级采用双仓库最小改造：

- 外部工具 `mediaClawerTooler` 负责读取任意数量的 JSON 关键词、生成独立进度文件和恢复队列。
- `MediaCrawler` 继续负责真正的小红书搜索、浏览器控制和原始 JSON 落盘。
- `start_chrome.ps1` 负责用专用用户目录启动可复用的 9222 Chrome。
- 验证码仅提供有上限的人工处理时间，不识别、点击或绕过验证码。

保持以下现有规则不变：关键词串行执行、每词最多20条、一级和二级评论关闭、保存格式为 JSON。

## 2. 非目标

本次不实现：

- 三关键词并行、分组或合并搜索。
- AI 内容粗筛。
- 用户 ID、个人主页或创作者模式采集。
- 数据库入库。
- 自动识别、点击、破解或绕过验证码。
- 自动启动或关闭 MediaCrawler API。
- 自动关闭 Chrome 或接管用户的普通 Chrome。

## 3. 总体架构与数据流

```text
关键词 JSON
  -> 外部工具校验、去空白、保持顺序去重
  -> 创建或读取 progress/<输入文件名>.progress.json
  -> 逐个调用本地 MediaCrawler API
  -> MediaCrawler 连接同一个 9222 专用 Chrome
  -> 小红书关键词搜索
  -> MediaCrawler/data/xhs/json 写入原始笔记
  -> 外部工具原子更新当前关键词状态
  -> 继续下一个关键词
```

两个 Python 项目通过现有 HTTP API 通信，不把 MediaCrawler 的爬虫逻辑复制到外部工具，也不新增第三方依赖。

## 4. JSON 输入

### 4.1 文件格式

`--source` 指向 UTF-8 JSON 文件，结构固定为：

```json
{
  "keywords": [
    "重庆企业主资产配置",
    "重庆公私资产隔离",
    "重庆家族信托"
  ]
}
```

关键词数量不限。解析规则：

1. 顶层必须为对象，`keywords` 必须为数组。
2. 数组元素必须全部为字符串；出现其他类型时拒绝整个输入。
3. 去除每个关键词首尾空白。
4. 忽略处理后为空的字符串。
5. 按首次出现顺序去重。
6. 最终没有有效关键词时停止，不调用 API。

本次删除对 Markdown 标题、代码块和“必须恰好20个词”的依赖。

### 4.2 命令行

正常运行：

```powershell
uv run python run_keywords.py --source .\inputs\keywords.json
```

`--source` 为必填参数，避免误用旧的固定 Markdown。保留现有 `--api-base`、`--progress` 和 `--retry-failed`。

## 5. 独立进度文件

未传 `--progress` 时，程序按输入文件名生成：

```text
inputs/重庆客户.json
-> progress/重庆客户.progress.json
```

`progress` 目录位于外部工具仓库根目录并自动创建，运行时进度文件不提交 Git。若不同目录存在同名输入，用户可通过 `--progress` 指定不同文件。

进度文件继续保存输入文件路径、关键词有序列表摘要、时间戳和逐词状态。允许状态保持为：

- `pending`：尚未执行。
- `running`：已经获得 MediaCrawler `task_id`，正在等待。
- `succeeded`：任务明确成功。
- `failed`：任务明确失败，可显式重试。
- `needs_review`：结果不确定，禁止自动重跑。

每次状态变化后，仍使用同目录临时文件加原子替换写盘。

如果同名进度文件已经存在，但输入的有序关键词摘要发生变化，程序拒绝覆盖或混用旧进度，并提示用户更换输入文件名或通过 `--progress` 使用新文件。

## 6. 恢复与重试

再次执行相同命令时：

1. 跳过 `succeeded`。
2. 对 `running` 使用原 `task_id` 查询 MediaCrawler 状态；任务仍存在则继续等待，结果明确则补记终态。
3. `failed` 默认跳过，只有传入 `--retry-failed` 才重置为 `pending`。
4. `needs_review` 保持不变并停止队列，提示人工检查，避免重复提交。

开始任务时若网络响应不确定，仍标记 `needs_review`；不得把无法确认的启动请求当作普通失败自动重试。

重试明确失败项：

```powershell
uv run python run_keywords.py `
  --source .\inputs\keywords.json `
  --retry-failed
```

## 7. 专用 Chrome 启动脚本

外部工具中的 `start_chrome.ps1` 负责：

1. 检查 `http://127.0.0.1:9222/json/version`。
2. 接口已可用时提示 Chrome 已运行并成功退出，不重复启动实例。
3. 接口不可用时从 Windows 常见 Chrome 安装位置查找 `chrome.exe`。
4. 使用 `--remote-debugging-port=9222` 和专用 `--user-data-dir` 启动可见 Chrome。
5. 默认专用目录为 `D:\red_note_rich_search\chrome_crawler_profile`，允许通过脚本参数覆盖。

第一次启动专用 Chrome 后，用户人工登录小红书；以后复用该目录中的登录状态。脚本不结束任何现有浏览器进程。若 9222 被其他程序占用但 `/json/version` 不是 Chrome 调试接口，脚本报错并停止。

## 8. MediaCrawler CDP 连接顺序

当 `CDP_CONNECT_EXISTING = True` 时，连接逻辑调整为：

1. 优先请求 `http://127.0.0.1:9222/json/version`；端口取自现有 `CDP_DEBUG_PORT` 配置。
2. 返回有效 `webSocketDebuggerUrl` 时，通过该地址连接命令行启动的专用 Chrome。
3. HTTP 接口不可用时，回退到现有 Chrome 136+ 直接 CDP 连接方式。
4. 进入回退模式时输出明确警告，说明浏览器可能继续要求人工授权。

这样每个关键词仍可使用现有 MediaCrawler 子进程，但都连接同一个已授权的专用 Chrome，不需要重写爬虫或改成长驻工作进程。

## 9. 验证码人工等待

小红书 HTTP 状态 `461` 或 `471` 进入专用验证码流程：

1. 记录一次清晰日志，提示用户在当前 Chrome 中人工完成验证。
2. 保持当前爬虫任务存活，固定每10秒重试当前请求。
3. 最长等待5分钟。
4. 验证通过后继续原请求和原关键词任务。
5. 超过5分钟仍返回 `461/471` 时，让任务以明确失败结束；runner 保存 `failed`，以后可用 `--retry-failed` 重跑。

验证码等待只匹配 `461/471`。其他网络异常、业务错误和笔记不存在继续沿用现有短重试或异常处理，不进入五分钟等待。实现不得模拟人工验证动作。

## 10. 错误处理

以下情况在提交新关键词前停止队列，已保存进度不丢失：

- JSON 文件不存在、编码错误或结构不合法。
- 输入摘要与已有进度不一致。
- MediaCrawler API 不在线或返回无法解释的状态。
- API 已有不属于当前进度文件的任务。
- 进度文件损坏或不可写。
- `running` 的 `task_id` 与 API 当前或最近任务不匹配。

单个关键词明确返回非零退出码时记为 `failed`，并继续下一项。验证码等待超时也属于明确失败。启动请求是否成功无法确认时记为 `needs_review` 并停止。

Chrome 调试接口在任务中途消失时，由 MediaCrawler 返回明确失败；runner 保存当前状态，后续关键词是否继续遵循现有“明确失败后继续”规则。

## 11. 测试设计

### 11.1 外部工具自动化测试

- 任意数量关键词能够读取。
- 非法 JSON、缺少 `keywords`、错误字段类型和空结果被拒绝。
- 空白词被忽略，重复词按首次出现顺序去重。
- 默认进度路径按输入文件名生成，`--progress` 能覆盖。
- 同名输入内容变化时拒绝复用旧进度。
- `succeeded` 被跳过，`running` 能按相同 `task_id` 恢复。
- `--retry-failed` 只重置 `failed`。
- `needs_review` 不自动重跑。

### 11.2 MediaCrawler 自动化测试

- `/json/version` 可用时优先使用其中的 WebSocket 地址。
- HTTP 探测失败时回退现有直接 CDP 模式。
- 无效 `/json/version` 响应不会被当作有效连接。
- `461/471` 验证后成功时继续原请求。
- `461/471` 持续5分钟时明确失败。
- 普通错误不进入长等待。

测试使用替身响应和可控时钟，不访问小红书，不在自动化测试中真实等待5分钟。

### 11.3 人工验收

1. 执行 `start_chrome.ps1`，在专用 Chrome 首次登录小红书。
2. 启动 MediaCrawler API。
3. 用至少两个测试关键词运行 JSON 队列，确认第二个任务不再弹出 CDP 授权。
4. 中断 runner 后重新运行，确认成功项被跳过、运行项能够恢复。
5. 在受控情况下出现验证码时人工完成，确认任务在五分钟窗口内继续。
6. 检查 `MediaCrawler/data/xhs/json` 和独立进度文件。

## 12. 最终使用顺序

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
.\start_chrome.ps1
```

首次使用时在打开的专用 Chrome 中登录小红书。然后启动 API：

```powershell
cd D:\red_note_rich_search\MediaCrawler
uv run uvicorn api.main:app --port 8080
```

最后在另一终端运行队列：

```powershell
cd D:\red_note_rich_search\keyword_crawl_runner
uv run python run_keywords.py --source .\inputs\keywords.json
```

## 13. 使用边界

- 仅用于个人、非商业研究和公开内容。
- 控制请求频率，关键词保持串行。
- 不采集评论、联系方式或非公开信息。
- 不把验证码处理自动化。
- 遵守 MediaCrawler 许可证、目标平台规则及适用要求。
