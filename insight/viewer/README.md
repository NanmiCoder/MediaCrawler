# 小红书数据查看器（XHS Data Viewer）

基于 Streamlit 的本地查看工具，复用上游 `database/sqlite_tables.db`。
仅做基础查看：笔记列表 + 点进去看评论。不修改任何上游文件。

## 一次性准备

```bash
# 确保上游 SQLite 表结构已创建
uv run python main.py --init_db sqlite
```

## 启动

从项目根目录执行：

```bash
uv run --with streamlit streamlit run insight/viewer/app.py
```

- 自动打开浏览器 `http://localhost:8501`
- 数据通过 `database/sqlite_tables.db` 实时读取，**不修改任何数据**
- 默认 60 秒缓存；点页面右上 🔄 立即重读
- Ctrl+C 停止

## 界面

```
顶部： 共 N 条笔记 / M 条评论         [🔄 刷新]
中段：  笔记列表（按发布时间倒序，可点击选中）
底段：  选中笔记的详情（作者/时间/关键词/正文）+ 评论列表
```

## 错误提示

| 情况 | 提示 |
|---|---|
| 数据库文件不存在 | 未找到数据库 ...，请先运行爬虫 |
| 数据库被爬取进程持锁 | 数据库正忙，请稍后重试 |
| `xhs_note` 表不存在 | 数据库缺少表 xhs_note，请先执行 `uv run python main.py --init_db sqlite` |
| 笔记表为空 | 暂无数据 |
| 选中笔记无评论 | 该笔记暂无评论 |

## 依赖

- Python 3.11+
- Streamlit（通过 `uv run --with streamlit` 临时拉取，**不**写入 `pyproject.toml` / `requirements.txt`）

## 相关

- 设计文档：[`docs/superpowers/specs/2026-06-06-xhs-data-viewer-design.md`](../../specs/2026-06-06-xhs-data-viewer-design.md)
- 数据来源：[`insight/` 爬取包](../../README.md)