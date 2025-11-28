# 数据保存指南 / Data Storage Guide

[English](#english) | [中文](#中文)

---

## 中文

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
# 使用 CSV 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option csv

# 使用 JSON 存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option json
```

#### 详细文档

- **Excel 导出详细指南**：查看 [Excel 导出指南](excel_export_guide.md)
- **数据库配置**：参考 [常见问题](常见问题.md)

---

## English

### 💾 Data Storage

MediaCrawler supports multiple data storage methods. Choose the one that best fits your needs:

#### Storage Options

- **CSV Files**: Supports saving to CSV (under `data/` directory)
- **JSON Files**: Supports saving to JSON (under `data/` directory)
- **Excel Files**: Supports saving to formatted Excel files (under `data/` directory) ✨ New Feature
  - Multi-sheet support (Contents, Comments, Creators)
  - Professional formatting (styled headers, auto-width columns, borders)
  - Easy to analyze and share
- **Database Storage**
  - Use the `--init_db` parameter for database initialization (when using `--init_db`, no other optional arguments are needed)
  - **SQLite Database**: Lightweight database, no server required, suitable for personal use (recommended)
    1. Initialization: `--init_db sqlite`
    2. Data Storage: `--save_data_option sqlite`
  - **MySQL Database**: Supports saving to relational database MySQL (database needs to be created in advance)
    1. Initialization: `--init_db mysql`
    2. Data Storage: `--save_data_option db` (the db parameter is retained for compatibility with historical updates)

#### Usage Examples

```shell
# Use Excel to store data (recommended for data analysis) ✨ New Feature
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Initialize SQLite database
uv run main.py --init_db sqlite
# Use SQLite to store data
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
```

```shell
# Initialize MySQL database
uv run main.py --init_db mysql
# Use MySQL to store data (the db parameter is retained for compatibility with historical updates)
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db
```

```shell
# Use CSV to store data
uv run main.py --platform xhs --lt qrcode --type search --save_data_option csv

# Use JSON to store data
uv run main.py --platform xhs --lt qrcode --type search --save_data_option json
```

#### Detailed Documentation

- **Excel Export Guide**: See [Excel Export Guide](excel_export_guide.md)
- **Database Configuration**: Refer to [FAQ](常见问题.md)
