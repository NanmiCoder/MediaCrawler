# insight — 小红书评论定时采集（MediaCrawler 二次开发）

本包是对 MediaCrawler 的二次开发，**不修改任何上游文件**，全部代码在 `insight/` 内。
本期范围：定时爬取 + 原始数据入库（复用上游 SQLite）+ 运行日志。**不含文本分析**（后续迭代）。

## 一次性准备

```bash
# 1. 初始化上游 SQLite 表结构（创建 xhs_note / xhs_note_comment 等）
uv run python main.py --init_db sqlite

# 2. 确保已登录小红书（CDP 模式，复用本机 Chrome 登录态）
#    参见项目根 README 的 Chrome 远程调试配置
```

## 配置

编辑 `insight/config.py` 的 `JOBS` 列表（job 类型 search/detail/creator、关键词/笔记ID/创作者ID、触发时刻 hour/minute、max_notes 等）。

## 使用

```bash
# 立即跑一次某个 job（不依赖 apscheduler）
uv run python -m insight.cli crawl-once kw_daily

# 查看最近运行记录（不依赖 apscheduler）
uv run python -m insight.cli status --limit 20

# 启动定时守护进程（前台运行，Ctrl+C 退出；需 apscheduler）
uv run --with "apscheduler>=3.10,<4" python -m insight.cli run-daemon
```

> 守护进程为前台常驻进程；本机重启后需手动重新启动。

## 运行测试

```bash
uv run --with "apscheduler>=3.10,<4" pytest tests/insight -v
```

## 与上游 MediaCrawler 同步更新

```bash
# 一次性：添加上游远程
git remote add upstream https://github.com/NanmiCoder/MediaCrawler.git

# 定期同步
git fetch upstream
git merge upstream/main        # 或 git rebase upstream/main
```

因为本包全部是 `insight/` 下的新增文件、未改动任何上游文件，合并几乎不会冲突。
唯一与上游耦合的假设：
- 上游 CLI 参数（`--platform/--type/--keywords/--specified_id/--creator_id/--save_data_option` 等）保持不变；
- SQLite 路径仍为 `database/sqlite_tables.db`（见 `config/db_config.py`）；
- `main.main` / `main.async_cleanup` / `tools.app_runner.run` 接口保持不变。
同步后若上述任一处变化，只需相应调整 `insight/runner.py`、`insight/config.py`、`insight/crawl_entry.py`。
