# 小红书评论采集与定时管道（XHS Insight Pipeline）设计文档

- 日期：2026-06-05
- 状态：已确认设计，待编写实现计划
- 作者：Jake (chuangjieren@gmail.com)

## 1. 背景与目标

基于 MediaCrawler（本仓库为 `DNNinfo/MediaCrawler` fork）做二次开发，实现：

1. **定时**爬取小红书（XHS）的笔记与评论原始数据。
2. 把原始数据落入 **SQLite**，供后续分析使用。
3. 保持本项目代码与上游 MediaCrawler **可持续同步更新**，同时**不影响**自己开发的代码。

> 本期范围**仅包含**「定时爬取 + 原始数据入库 + 运行日志」。**不包含 LLM / 文本分析**。文本分析（计划使用本地 Ollama + Qwen）作为后续迭代，在不改动本期代码的前提下扩展。

## 2. 核心隔离策略（最重要的约束）

- 自研代码全部放入**单一新增顶层包 `insight/`**。
- **不修改** MediaCrawler 既有任何文件（`main.py`、`media_platform/`、`store/`、`database/`、`config/` 等保持上游原样）。
- `insight/` 通过两种方式与上游交互，均为「只读 / 旁路」：
  - **调用**：以**子进程**方式运行 `uv run main.py …`。
  - **读取**：读取爬虫写入的 SQLite 表（`xhs_note` / `xhs_note_comment`）。
- Git 层面：新增 `upstream` 远程，定期 `fetch` + `merge`/`rebase`。由于自研代码都是 `insight/` 下的**新增文件**，几乎不会与上游产生冲突。

### Git 同步工作流

```bash
# 一次性
git remote add upstream https://github.com/NanmiCoder/MediaCrawler.git

# 定期同步
git fetch upstream
git merge upstream/main      # 或 git rebase upstream/main
```

- 不在上游文件中写任何自研配置；所有自研配置在 `insight/config.py` 自行声明。
- `insight/` 产生的数据/缓存通过 `.gitignore` 忽略（若需改 `.gitignore`，仅追加自研条目，尽量减少与上游接触面）。
- `insight/README.md` 记录上述同步步骤备忘。

## 3. 目录结构

```
MediaCrawler/                  # 上游，零改动
├─ main.py, media_platform/, store/, database/, config/ …
└─ insight/                    # ← 自研全部代码
   ├─ __init__.py
   ├─ config.py                # db 路径、job 定义、爬虫参数
   ├─ cli.py                   # 入口：crawl-once / run-daemon / status
   ├─ runner.py                # 子进程封装 uv run main.py …
   ├─ db.py                    # 写/读 insight_runs；按需读 xhs_* 校验数据
   ├─ schema.sql               # insight_runs 表定义
   ├─ scheduler/
   │  ├─ __init__.py
   │  └─ daemon.py             # APScheduler，每日触发
   └─ README.md                # 上游同步步骤 + 使用说明

tests/
└─ insight/                    # 自研测试，独立目录
```

## 4. 数据流（一次调度周期）

1. **APScheduler**（`insight/scheduler/daemon.py`）到点触发某个 job。
2. **runner.py** 启动子进程：`uv run main.py --platform xhs --type search|detail|creator …`，并强制 `SAVE_DATA_OPTION=sqlite`（通过命令行/环境变量传入，不改上游配置文件）。
3. 爬虫将原始数据写入上游既有表 `xhs_note` / `xhs_note_comment`。
4. **db.py** 在 `insight_runs` 记录本次运行：job 名、开始/结束时间、子进程退出码、爬取条数、状态/错误信息。
5. 周期结束。原始数据留存于 SQLite，供后续分析迭代使用。

> 设计上爬取与记录是可独立运行的步骤：`insight crawl-once <job>` 可手动跑单次；`insight run-daemon` 启动常驻调度；`insight status` 查看最近运行记录。

## 5. 数据模型

### 5.1 上游既有表（只读，不改）

- `xhs_note`：`note_id`、`title`、`desc`、`source_keyword`、`time`、`liked_count`、`comment_count`、`collected_count` 等。
- `xhs_note_comment`：`comment_id`、`note_id`、`content`、`create_time`、`like_count`、`parent_comment_id`、`sub_comment_count`、`ip_location`、`nickname`、`user_id` 等。

### 5.2 自研表（`insight/schema.sql`，本期唯一新增表）

**`insight_runs`** — 每次调度周期一行：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `job_name` | TEXT | 对应 `config.JOBS[].name` |
| `crawler_type` | TEXT | search / detail / creator |
| `started_ts` | INTEGER | 开始时间戳 |
| `finished_ts` | INTEGER | 结束时间戳（可空，运行中为空） |
| `exit_code` | INTEGER | 子进程退出码（可空） |
| `notes_crawled` | INTEGER | 本次新增/涉及笔记数（尽力统计） |
| `comments_crawled` | INTEGER | 本次新增/涉及评论数（尽力统计） |
| `status` | TEXT | running / success / error / timeout |
| `error_msg` | TEXT | 失败信息（可空） |

> 表名以 `insight_` 前缀与上游表隔离。后续分析迭代时新增的表同样使用该前缀。

## 6. Job 配置（`insight/config.py` 示例形态）

```python
# SQLite 路径（与爬虫共用同一文件）
DB_PATH = "./data/mediacrawler.db"

# 子进程超时（秒）
SUBPROCESS_TIMEOUT = 1800

# 调度任务定义
JOBS = [
    {"name": "kw_daily",      "type": "search",  "keywords": "编程副业,编程兼职", "hour": 2, "max_notes": 20},
    {"name": "watch_notes",   "type": "detail",  "note_ids": ["xxx", "yyy"],      "hour": 3},
    {"name": "creator_daily", "type": "creator", "creator_ids": ["zzz"],          "hour": 4},
]
```

- 每个 job 映射为一次 `main.py` 调用；`type`→`--type`，其余字段→对应命令行参数/环境变量。
- 默认每日触发（`hour` 指定时刻）。

## 7. 运行环境与前置条件

- **登录态**：XHS 需扫码登录。调度运行在本机已登录的 Chrome（CDP 模式，`ENABLE_CDP_MODE=True`）。登录失效时子进程失败并记入 `insight_runs`，daemon 不崩溃。
- **常驻进程**：APScheduler 为进程内守护（B 方案）。本机重启后需**手动重启** daemon。
- **依赖**：APScheduler 作为自研依赖引入（评估加入 `pyproject.toml` / 单独 requirements，尽量不污染上游依赖声明，具体在实现计划中确定）。

## 8. 错误处理

- **子进程**：检查退出码 + 超时（`SUBPROCESS_TIMEOUT`）。失败 → `insight_runs` 记 `error`/`timeout`，不影响其他 job。
- **登录失效**：子进程失败被捕获并记录，等待下次调度或人工介入。
- **幂等**：重复运行安全——上游 SQLite 存储按主键/唯一键去重。
- **错过触发**：APScheduler 使用 `misfire_grace_time` 容忍短暂错过。

## 9. 测试策略

- `runner`：mock subprocess，验证命令拼装、超时与退出码处理。
- `db`：临时 SQLite，验证 `insight_runs` 写入/查询。
- `scheduler`：可控触发，验证 job → runner → 日志 串联，以及单 job 失败不影响其他 job。
- 测试位于 `tests/insight/`，与上游测试隔离。

## 10. 后续迭代（本期不实现，仅预留）

- 在 `insight/analysis/` 增加本地 Ollama（Qwen）分析模块：逐评论结构化打标 + 逐笔记聚合简报。
- 新增分析结果表（`insight_*` 前缀），按 `comment_id` 左连接做增量分析。
- 这些扩展均为新增文件，不改动本期代码，符合隔离策略。

## 11. 未决/待实现计划阶段确认的细节

- APScheduler 依赖的具体引入方式（pyproject vs 独立 requirements）。
- `notes_crawled` / `comments_crawled` 的统计方式（运行前后对表计数差值）。
- `SAVE_DATA_OPTION=sqlite` 的传参方式（命令行参数 vs 环境变量 vs 临时配置覆盖）——需在实现时确认上游 `main.py` 支持的覆盖手段，仍以「不改上游」为前提。
