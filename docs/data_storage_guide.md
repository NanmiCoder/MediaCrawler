# 数据保存指南 / Data Storage Guide


### 💾 数据保存

MediaCrawler 支持多种数据存储方式，您可以根据需求选择最适合的方案：

#### 存储方式

- **CSV 文件**：支持保存到 CSV 中（`data/` 目录下）
- **JSON 文件**：支持保存到 JSON 中（`data/` 目录下）
- **Excel 文件**：支持保存到格式化的 Excel 文件（`data/` 目录下）✨ 新功能
  - 多工作表支持（内容、评论、创作者）
  - 专业格式化（标题样式、自动列宽、边框）
  - 易于分析和分享
- **数据库存储**
  - 使用参数 `--init_db` 进行数据库初始化（使用`--init_db`时不需要携带其他optional）
  - **SQLite 数据库**：轻量级数据库，无需服务器，适合个人使用（推荐）
    1. 初始化：`--init_db sqlite`
    2. 数据存储：`--save_data_option sqlite`
  - **MySQL 数据库**：支持关系型数据库 MySQL 中保存（需要提前创建数据库）
    1. 初始化：`--init_db mysql`
    2. 数据存储：`--save_data_option db`（db 参数为兼容历史更新保留）
  - **PostgreSQL 数据库**：支持高级关系型数据库 PostgreSQL 中保存（推荐生产环境使用）
    1. 初始化：`--init_db postgres`
    2. 数据存储：`--save_data_option postgres`

#### 使用示例

```shell
# 使用 Excel 存储数据（推荐用于数据分析）✨ 新功能
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# 初始化 SQLite 数据库
uv run main.py --init_db sqlite
# 使用 SQLite 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
```

```shell
# 初始化 MySQL 数据库
uv run main.py --init_db mysql
# 使用 MySQL 存储数据（为适配历史更新，db参数进行沿用）
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db
```

```shell
# 初始化 PostgreSQL 数据库
uv run main.py --init_db postgres
# 使用 PostgreSQL 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option postgres
```

```shell
# 使用 CSV 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option csv

# 使用 JSON 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option json
```

#### 详细文档

- **Excel 导出详细指南**：查看 [Excel 导出指南](excel_export_guide.md)
- **数据库配置**：参考 [常见问题](常见问题.md)

---
