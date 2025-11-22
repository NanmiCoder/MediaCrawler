# MediaCrawler使用方法

## 推荐：使用 uv 管理依赖

### 1. 前置依赖
- 安装 [uv](https://docs.astral.sh/uv/getting-started/installation)，并用 `uv --version` 验证。
- Python 版本建议使用 **3.11**（当前依赖基于该版本构建）。
- 安装 Node.js（抖音、知乎等平台需要），版本需 `>= 16.0.0`。

### 2. 同步 Python 依赖
```shell
# 进入项目根目录
cd MediaCrawler

# 使用 uv 保证 Python 版本和依赖一致性
uv sync
```

### 3. 安装 Playwright 浏览器驱动
```shell
uv run playwright install
```
> 项目已支持使用 Playwright 连接本地 Chrome。如需使用 CDP 方式，可在 `config/base_config.py` 中调整 `xhs` 和 `dy` 的相关配置。

### 4. 运行爬虫程序
```shell
# 项目默认未开启评论爬取，如需评论请在 config/base_config.py 中修改 ENABLE_GET_COMMENTS
# 其他功能开关也可在 config/base_config.py 查看，均有中文注释

# 从配置中读取关键词搜索并爬取帖子与评论
uv run main.py --platform xhs --lt qrcode --type search

# 从配置中读取指定帖子ID列表并爬取帖子与评论
uv run main.py --platform xhs --lt qrcode --type detail

# 使用 SQLite 数据库存储数据（推荐个人用户使用）
uv run main.py --platform xhs --lt qrcode --type search --save_data_option sqlite

# 使用 MySQL 数据库存储数据
uv run main.py --platform xhs --lt qrcode --type search --save_data_option db

# 其他平台示例
uv run main.py --help
```

## 备选：Python 原生 venv（不推荐）
> 如果爬取抖音或知乎，需要提前安装 Node.js，版本 `>= 16`。
```shell
# 进入项目根目录
cd MediaCrawler

# 创建虚拟环境（示例 Python 版本：3.11，requirements 基于该版本）
python -m venv venv

# macOS & Linux 激活虚拟环境
source venv/bin/activate

# Windows 激活虚拟环境
venv\Scripts\activate
```
```shell
# 安装依赖与驱动
pip install -r requirements.txt
playwright install
```
```shell
# 运行爬虫程序（venv 环境）
python main.py --platform xhs --lt qrcode --type search
python main.py --platform xhs --lt qrcode --type detail
python main.py --platform xhs --lt qrcode --type search --save_data_option sqlite
python main.py --platform xhs --lt qrcode --type search --save_data_option db
python main.py --help
```

## 💾 数据存储

支持多种数据存储方式：
- **CSV 文件**: 支持保存至 CSV (位于 `data/` 目录下)
- **JSON 文件**: 支持保存至 JSON (位于 `data/` 目录下)
- **数据库存储**
  - 使用 `--init_db` 参数进行数据库初始化 (使用 `--init_db` 时，无需其他可选参数)
  - **SQLite 数据库**: 轻量级数据库，无需服务器，适合个人使用 (推荐)
    1. 初始化: `--init_db sqlite`
    2. 数据存储: `--save_data_option sqlite`
  - **MySQL 数据库**: 支持保存至关系型数据库 MySQL (需提前创建数据库)
    1. 初始化: `--init_db mysql`
    2. 数据存储: `--save_data_option db` (db 参数为兼容历史更新保留)

## 免责声明
> **免责声明：**
> 
> 大家请以学习为目的使用本仓库，爬虫违法违规的案件：https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China  <br>
>
>本项目的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。
