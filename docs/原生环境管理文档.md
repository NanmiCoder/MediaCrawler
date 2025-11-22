# 本地原生环境管理

## 推荐方案：使用 uv 管理依赖

### 1. 前置依赖
- 安装 [uv](https://docs.astral.sh/uv/getting-started/installation)，并使用 `uv --version` 验证。
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

# 其他平台示例
uv run main.py --help
```

## 备选方案：Python 原生 venv（不推荐）

### 创建并激活虚拟环境
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

### 安装依赖与驱动
```shell
pip install -r requirements.txt
playwright install
```

### 运行爬虫程序（venv 环境）
```shell
# 从配置中读取关键词搜索并爬取帖子与评论
python main.py --platform xhs --lt qrcode --type search

# 从配置中读取指定帖子ID列表并爬取帖子与评论
python main.py --platform xhs --lt qrcode --type detail

# 更多示例
python main.py --help
```
