# 🔥 MediaCrawler - 自媒体平台爬虫 🕷️

<div align="center">

<a href="https://trendshift.io/repositories/8291" target="_blank">
  <img src="https://trendshift.io/api/badge/repositories/8291" alt="NanmiCoder%2FMediaCrawler | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
</a>

[![GitHub Stars](https://img.shields.io/github/stars/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/pulls)
[![License](https://img.shields.io/github/license/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE)
[![中文](https://img.shields.io/badge/🇨🇳_中文-当前-blue)](README.md)
[![English](https://img.shields.io/badge/🇺🇸_English-Available-green)](README_en.md)
[![Español](https://img.shields.io/badge/🇪🇸_Español-Available-green)](README_es.md)
</div>



> **免责声明：**
> 
> 大家请以学习为目的使用本仓库⚠️⚠️⚠️⚠️，[爬虫违法违规的案件](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)  <br>
>
>本仓库的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。
>
> 点击查看更为详细的免责声明。[点击跳转](#disclaimer)




## 📖 项目简介

一个功能强大的**多平台自媒体数据采集工具**，支持小红书、抖音、快手、B站、微博、贴吧、知乎等主流平台的公开信息抓取。

### 🔧 技术原理

- **核心技术**：基于 [Playwright](https://playwright.dev/) 浏览器自动化框架登录保存登录态
- **无需JS逆向**：利用保留登录态的浏览器上下文环境，通过 JS 表达式获取签名参数
- **优势特点**：无需逆向复杂的加密算法，大幅降低技术门槛

## ✨ 功能特性
| 平台   | 关键词搜索 | 指定帖子ID爬取 | 二级评论 | 指定创作者主页 | 登录态缓存 | IP代理池 | 生成评论词云图 | 智能URL解析 | 交互式输入 |
| ------ | ---------- | -------------- | -------- | -------------- | ---------- | -------- | -------------- | ------------ | ---------- |
| 小红书 | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| 抖音   | ✅          | 🔥**增强**      | ✅        | 🔥**增强**      | ✅          | ✅        | ✅              | 🔥**新功能**   | 🔥**新功能** |
| 快手   | ✅          | 🔥**增强**      | ✅        | 🔥**增强**      | ✅          | ✅        | ✅              | 🔥**新功能**   | 🔥**新功能** |
| B 站   | ✅          | 🔥**增强**      | ✅        | 🔥**增强**      | ✅          | ✅        | ✅              | 🔥**新功能**   | 🔥**新功能** |
| 微博   | ✅          | 🔥**增强**      | ✅        | 🔥**增强**      | ✅          | ✅        | ✅              | 🔥**新功能**   | 🔥**新功能** |
| 贴吧   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| 知乎   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |

### 🔥 新增强功能亮点

#### 🎯 统一交互式输入
- **智能输入检测**：当配置文件为空时，自动启用交互式输入模式
- **格式化提示**：提供详细的输入格式示例和说明
- **混合输入支持**：支持同时输入多种格式（URL、短链接、ID）

#### 🔗 智能URL解析引擎
- **短链接重定向**：智能解析分享短链接，自动重定向获取真实URL
- **多格式兼容**：支持完整URL、短链接、直接ID等多种输入格式
- **验证机制**：内置ID验证，防止无效输入导致的错误

#### 📱 统一命令行接口
**新的统一命令格式**：
```bash
# 统一使用 --urls 参数，支持所有平台
uv run main.py --platform [dy|ks|wb|bili] --lt qrcode --type [search|detail|creator] --urls "URL1" "URL2" "URL3"
```

### 🔥 抖音增强功能

| 输入格式 | 示例 | 解析方式 |
|---------|------|----------|
| 完整用户主页URL | `https://www.douyin.com/user/MS4wLjABAAAA...` | 直接提取sec_user_id |
| 完整视频URL | `https://www.douyin.com/video/7525082444551310602` | 直接提取video_id |
| 分享短链接 | `https://v.douyin.com/J7v_LxD7vUQ/` | 智能重定向解析 |
| 直接ID | `MS4wLjABAAAA...` 或 `7525082444551310602` | 直接使用 |

### 🔥 快手增强功能

| 输入格式 | 示例 | 解析方式 |
|---------|------|----------|
| 完整视频URL | `https://www.kuaishou.com/short-video/3xf8enb8dbj6uig` | 直接提取video_id |
| 完整用户主页URL | `https://www.kuaishou.com/profile/3xi4kwp2pg8tp8k` | 直接提取user_id |
| 分享短链接 | `https://v.kuaishou.com/2F50ZXj` | 智能重定向解析 |
| 直接ID | `3xf8enb8dbj6uig` 或 `3xi4kwp2pg8tp8k` | 直接使用 |

### 🔥 B站增强功能

| 输入格式 | 示例 | 解析方式 |
|---------|------|----------|
| 完整视频URL | `https://www.bilibili.com/video/BV1Q2MXzgEgW` | 直接提取BVID/AID |
| 完整用户空间URL | `https://space.bilibili.com/449342345` | 直接提取UID |
| 分享短链接 | `https://b23.tv/B6gPE4M` | 智能重定向解析 |
| 直接ID | `BV1Q2MXzgEgW` 或 `449342345` | 直接使用 |

### 🔥 微博增强功能

| 输入格式 | 示例 | 解析方式 |
|---------|------|----------|
| 桌面版分享链接 | `https://weibo.com/7643904561/5182160183232445` | 直接提取post_id |
| 手机版URL | `https://m.weibo.cn/detail/5182160183232445` | 直接提取post_id |
| 用户主页URL | `https://weibo.com/u/5533390220` | 直接提取user_id |
| 直接ID | `5182160183232445` 或 `5533390220` | 直接使用 |

<details id="pro-version">
<summary>🔗 <strong>🚀 MediaCrawlerPro 重磅发布！更多的功能，更好的架构设计！</strong></summary>

### 🚀 MediaCrawlerPro 重磅发布！

> 专注于学习成熟项目的架构设计，不仅仅是爬虫技术，Pro 版本的代码设计思路同样值得深入学习！

[MediaCrawlerPro](https://github.com/MediaCrawlerPro) 相较于开源版本的核心优势：

#### 🎯 核心功能升级
- ✅ **断点续爬功能**（重点特性）
- ✅ **多账号 + IP代理池支持**（重点特性）
- ✅ **去除 Playwright 依赖**，使用更简单
- ✅ **完整 Linux 环境支持**

#### 🏗️ 架构设计优化
- ✅ **代码重构优化**，更易读易维护（解耦 JS 签名逻辑）
- ✅ **企业级代码质量**，适合构建大型爬虫项目
- ✅ **完美架构设计**，高扩展性，源码学习价值更大

#### 🎁 额外功能
- ✅ **自媒体视频下载器桌面端**（适合学习全栈开发）
- ✅ **多平台首页信息流推荐**（HomeFeed）
- [ ] **基于自媒体平台的AI Agent正在开发中 🚀🚀**

点击查看：[MediaCrawlerPro 项目主页](https://github.com/MediaCrawlerPro) 更多介绍
</details>

## 🚀 快速开始

> 💡 **开源不易，如果这个项目对您有帮助，请给个 ⭐ Star 支持一下！**

## 📋 前置依赖

### 🚀 uv 安装（推荐）

在进行下一步操作之前，请确保电脑上已经安装了 uv：

- **安装地址**：[uv 官方安装指南](https://docs.astral.sh/uv/getting-started/installation)
- **验证安装**：终端输入命令 `uv --version`，如果正常显示版本号，证明已经安装成功
- **推荐理由**：uv 是目前最强的 Python 包管理工具，速度快、依赖解析准确

### 🟢 Node.js 安装

项目依赖 Node.js，请前往官网下载安装：

- **下载地址**：https://nodejs.org/en/download/
- **版本要求**：>= 16.0.0

### 📦 Python 包安装

```shell
# 进入项目目录
cd MediaCrawler

# 使用 uv sync 命令来保证 python 版本和相关依赖包的一致性
uv sync
```

### 🌐 浏览器驱动安装

```shell
# 安装浏览器驱动
uv run playwright install
```

> **💡 提示**：MediaCrawler 目前已经支持使用 playwright 连接你本地的 Chrome 浏览器了，一些因为 Webdriver 导致的问题迎刃而解了。
>
> 目前开放了 `xhs` 和 `dy` 这两个使用 CDP 的方式连接本地浏览器，如有需要，查看 `config/base_config.py` 中的配置项。

## 🚀 运行爬虫程序

### 基础使用

```shell
# 项目默认是没有开启评论爬取模式，如需评论请在 config/base_config.py 中的 ENABLE_GET_COMMENTS 变量修改
# 一些其他支持项，也可以在 config/base_config.py 查看功能，写的有中文注释

# 关键词搜索爬取
uv run main.py --platform xhs --lt qrcode --type search

# 指定帖子ID爬取
uv run main.py --platform xhs --lt qrcode --type detail

# 创作者主页爬取
uv run main.py --platform xhs --lt qrcode --type creator

# 其他平台爬虫使用示例，执行下面的命令查看
uv run main.py --help
```

### 🔥 统一智能URL解析功能

**无需手动提取ID，支持直接粘贴分享链接，所有平台统一操作方式**：

#### 交互式输入模式（推荐）
```shell
# 抖音平台 - 清空配置文件后自动进入交互式输入
uv run main.py --platform dy --lt qrcode --type creator
uv run main.py --platform dy --lt qrcode --type detail

# 快手平台 - 支持短链接智能解析
uv run main.py --platform ks --lt qrcode --type creator
uv run main.py --platform ks --lt qrcode --type detail

# B站平台 - 支持b23.tv短链接解析
uv run main.py --platform bili --lt qrcode --type creator
uv run main.py --platform bili --lt qrcode --type detail

# 微博平台 - 支持多种URL格式
uv run main.py --platform wb --lt qrcode --type creator
uv run main.py --platform wb --lt qrcode --type detail
```

#### 命令行直接输入
```shell
# 统一使用 --urls 参数，支持所有平台
uv run main.py --platform dy --lt qrcode --type creator --urls "https://v.douyin.com/J7v_LxD7vUQ/"
uv run main.py --platform ks --lt qrcode --type detail --urls "https://v.kuaishou.com/2F50ZXj"
uv run main.py --platform bili --lt qrcode --type detail --urls "https://b23.tv/B6gPE4M"
uv run main.py --platform wb --lt qrcode --type creator --urls "https://weibo.com/u/5533390220"

# 批量爬取多个目标
uv run main.py --platform dy --lt qrcode --type detail --urls "URL1" "URL2" "URL3"
```

**支持的输入格式示例**：
- **抖音**：`https://v.douyin.com/J7v_LxD7vUQ/`、`https://www.douyin.com/video/7525082444551310602`
- **快手**：`https://v.kuaishou.com/2F50ZXj`、`https://www.kuaishou.com/short-video/3xf8enb8dbj6uig`
- **B站**：`https://b23.tv/B6gPE4M`、`https://www.bilibili.com/video/BV1Q2MXzgEgW`
- **微博**：桌面版、手机版URL或直接ID

<details>
<summary>🔗 <strong>使用 Python 原生 venv 管理环境（不推荐）</strong></summary>

#### 创建并激活 Python 虚拟环境

> 如果是爬取抖音和知乎，需要提前安装 nodejs 环境，版本大于等于：`16` 即可

```shell
# 进入项目根目录
cd MediaCrawler

# 创建虚拟环境
# 我的 python 版本是：3.9.6，requirements.txt 中的库是基于这个版本的
# 如果是其他 python 版本，可能 requirements.txt 中的库不兼容，需自行解决
python -m venv venv

# macOS & Linux 激活虚拟环境
source venv/bin/activate

# Windows 激活虚拟环境
venv\Scripts\activate
```

#### 安装依赖库

```shell
pip install -r requirements.txt
```

#### 安装 playwright 浏览器驱动

```shell
playwright install
```

#### 运行爬虫程序（原生环境）

```shell
# 项目默认是没有开启评论爬取模式，如需评论请在 config/base_config.py 中的 ENABLE_GET_COMMENTS 变量修改
# 一些其他支持项，也可以在 config/base_config.py 查看功能，写的有中文注释

# 从配置文件中读取关键词搜索相关的帖子并爬取帖子信息与评论
python main.py --platform xhs --lt qrcode --type search

# 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
python main.py --platform xhs --lt qrcode --type detail

# 打开对应APP扫二维码登录

# 其他平台爬虫使用示例，执行下面的命令查看
python main.py --help
```

</details>


## 💾 数据保存

支持多种数据存储方式：

- **MySQL 数据库**：支持关系型数据库 MySQL 中保存（需要提前创建数据库）
  - 执行 `python db.py` 初始化数据库表结构（只在首次执行）
- **CSV 文件**：支持保存到 CSV 中（`data/` 目录下）
- **JSON 文件**：支持保存到 JSON 中（`data/` 目录下）

### 📊 抖音创作者爬取数据文件

creator模式下会生成三个数据文件：

#### CSV格式 (`SAVE_DATA_OPTION = "csv"`)
```
data/douyin/
├── 1_creator_contents_2025-07-12.csv    # 所有视频详细信息
├── 1_creator_comments_2025-07-12.csv    # 视频评论信息（如果开启）
└── 1_creator_creator_2025-07-12.csv     # 创作者基本信息
```

#### JSON格式 (`SAVE_DATA_OPTION = "json"`)
```
data/douyin/json/
├── creator_contents_2025-07-12.json     # 所有视频详细信息
├── creator_comments_2025-07-12.json     # 视频评论信息
└── creator_creator_2025-07-12.json      # 创作者基本信息
```

**数据内容说明**：
- **contents文件**：包含创作者所有视频的详细信息（标题、描述、播放量、点赞数、发布时间、下载链接等）
- **creator文件**：包含创作者基本信息（昵称、头像、简介、粉丝数、关注数等）
- **comments文件**：包含所有视频的评论信息（评论内容、评论者、点赞数等，需开启`ENABLE_GET_COMMENTS`）

## ⚙️ 配置说明

### 统一智能URL解析配置

在 `config/base_config.py` 中可以配置各平台的URL列表，所有平台都支持智能解析：

#### 抖音平台配置
```python
# 指定抖音创作者主页URL列表 - 支持三种格式自动识别和解析
DY_CREATOR_URL_LIST = [
    # "https://www.douyin.com/user/MS4wLjABAAAA...",  # 完整用户主页URL
    # "https://v.douyin.com/J7v_LxD7vUQ/",           # 分享短链接（智能重定向解析）
    # "MS4wLjABAAAA...",                             # 直接的sec_user_id
]

# 指定抖音视频列表 - 支持三种格式自动识别和解析
DY_SPECIFIED_ID_LIST = [
    # "https://www.douyin.com/video/7525082444551310602",  # 完整视频URL
    # "https://v.douyin.com/XfjzKi_ZFLA/",                 # 分享短链接（智能重定向解析）
    # "7525082444551310602",                               # 直接的video_id
]
```

#### 快手平台配置
```python
# 指定快手视频列表 - 支持三种格式自动识别和解析
KS_SPECIFIED_ID_LIST = [
    # "https://www.kuaishou.com/short-video/3xf8enb8dbj6uig",  # 完整视频URL
    # "https://v.kuaishou.com/2F50ZXj",                        # 分享短链接（智能重定向解析）
    # "3xf8enb8dbj6uig",                                       # 直接的video_id
]

# 指定快手创作者列表 - 支持四种格式自动识别和解析
KS_CREATOR_ID_LIST = [
    # "https://www.kuaishou.com/profile/3x4sm73aye7jq7i",  # 完整用户主页URL
    # "https://live.kuaishou.com/profile/3xqrp5h7gg392vg", # 完整直播用户主页URL
    # "https://v.kuaishou.com/2HJ1YXC",                    # 分享短链接（智能重定向解析）
    # "3xqrp5h7gg392vg",                                   # 直接的creator_id
]
```

#### B站平台配置
```python
# 指定B站视频列表 - 支持四种格式自动识别和解析
BILI_SPECIFIED_ID_LIST = [
    # "https://www.bilibili.com/video/BV1Q2MXzgEgW",  # 完整视频URL（BVID格式）
    # "https://b23.tv/B6gPE4M",                       # 分享短链接（智能重定向解析）
    # "BV1Q2MXzgEgW",                                 # 直接的BVID
    # "87654321",                                     # 直接的AID
]

# 指定B站创作者列表 - 支持三种格式自动识别和解析
BILI_CREATOR_ID_LIST = [
    # "https://space.bilibili.com/449342345",  # 完整用户空间URL
    # "https://b23.tv/9ljhRio",                # 分享短链接（智能重定向解析）
    # "449342345",                             # 直接的UID
]
```

#### 微博平台配置
```python
# 指定微博帖子列表 - 支持三种格式自动识别和解析
WEIBO_SPECIFIED_ID_LIST = [
    # "https://weibo.com/7643904561/5182160183232445",  # 桌面版分享链接
    # "https://m.weibo.cn/detail/5182160183232445",     # 手机版URL
    # "5182160183232445",                               # 直接的post_id
]

# 指定微博创作者列表 - 支持四种格式自动识别和解析
WEIBO_CREATOR_ID_LIST = [
    # "https://weibo.com/u/5533390220",      # 完整用户主页URL
    # "https://m.weibo.cn/u/5533390220",     # 手机版用户主页URL
    # "5533390220",                          # 直接的user_id
]
```

### 常用配置项

```python
# 爬取模式设置
PLATFORM = "dy"              # 平台选择 (xhs/dy/ks/bili/wb/tieba/zhihu)
CRAWLER_TYPE = "creator"     # 爬取类型（search/detail/creator）

# 数据保存设置
SAVE_DATA_OPTION = "csv"     # 数据保存格式（csv/db/json）

# 评论爬取设置
ENABLE_GET_COMMENTS = True                           # 是否爬取评论
ENABLE_GET_SUB_COMMENTS = False                      # 是否爬取二级评论
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10         # 单视频最大评论数

# 并发控制
MAX_CONCURRENCY_NUM = 1      # 并发数量控制

# 交互式输入提示
# 如果要使用交互式输入，请确保对应平台的配置列表为空：
# - 抖音：DY_SPECIFIED_ID_LIST = [] 或 DY_CREATOR_URL_LIST = []
# - 快手：KS_SPECIFIED_ID_LIST = [] 或 KS_CREATOR_ID_LIST = []
# - B站：BILI_SPECIFIED_ID_LIST = [] 或 BILI_CREATOR_ID_LIST = []
# - 微博：WEIBO_SPECIFIED_ID_LIST = [] 或 WEIBO_CREATOR_ID_LIST = []
```

---

[🚀 MediaCrawlerPro 重磅发布 🚀！更多的功能，更好的架构设计！](https://github.com/MediaCrawlerPro)

## 🤝 社区与支持

### 💬 交流群组
- **微信交流群**：[点击加入](https://nanmicoder.github.io/MediaCrawler/%E5%BE%AE%E4%BF%A1%E4%BA%A4%E6%B5%81%E7%BE%A4.html)

### 📚 文档与教程
- **在线文档**：[MediaCrawler 完整文档](https://nanmicoder.github.io/MediaCrawler/)
- **爬虫教程**：[CrawlerTutorial 免费教程](https://github.com/NanmiCoder/CrawlerTutorial)
  

# 其他常见问题可以查看在线文档
> 
> 在线文档包含使用方法、常见问题、加入项目交流群等。
> [MediaCrawler在线文档](https://nanmicoder.github.io/MediaCrawler/)
> 

# 作者提供的知识服务
> 如果想快速入门和学习该项目的使用、源码架构设计等、学习编程技术、亦或者想了解MediaCrawlerPro的源代码设计可以看下我的知识付费栏目。

[作者的知识付费栏目介绍](https://nanmicoder.github.io/MediaCrawler/%E7%9F%A5%E8%AF%86%E4%BB%98%E8%B4%B9%E4%BB%8B%E7%BB%8D.html)


---

## ⭐ Star 趋势图

如果这个项目对您有帮助，请给个 ⭐ Star 支持一下，让更多的人看到 MediaCrawler！

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)

### 💰 赞助商展示

<a href="https://www.swiftproxy.net/?ref=nanmi">
<img src="docs/static/images/img_5.png">
<br>
**Swiftproxy** - 90M+ 全球高质量纯净住宅IP，注册可领免费 500MB 测试流量，动态流量不过期！
> 专属折扣码：**GHB5** 立享九折优惠！
</a>

<br><br>

<a href="https://sider.ai/ad-land-redirect?source=github&p1=mi&p2=kk">**Sider** - 全网最火的 ChatGPT 插件，体验拉满！</a>

### 🤝 成为赞助者

成为赞助者，可以将您的产品展示在这里，每天获得大量曝光！

**联系方式**：
- 微信：`yzglan`
- 邮箱：`relakkes@gmail.com`


## 📚 参考

- **小红书客户端**：[ReaJason 的 xhs 仓库](https://github.com/ReaJason/xhs)
- **短信转发**：[SmsForwarder 参考仓库](https://github.com/pppscn/SmsForwarder)
- **内网穿透工具**：[ngrok 官方文档](https://ngrok.com/docs/)


# 免责声明
<div id="disclaimer"> 

## 1. 项目目的与性质
本项目（以下简称“本项目”）是作为一个技术研究与学习工具而创建的，旨在探索和学习网络数据采集技术。本项目专注于自媒体平台的数据爬取技术研究，旨在提供给学习者和研究者作为技术交流之用。

## 2. 法律合规性声明
本项目开发者（以下简称“开发者”）郑重提醒用户在下载、安装和使用本项目时，严格遵守中华人民共和国相关法律法规，包括但不限于《中华人民共和国网络安全法》、《中华人民共和国反间谍法》等所有适用的国家法律和政策。用户应自行承担一切因使用本项目而可能引起的法律责任。

## 3. 使用目的限制
本项目严禁用于任何非法目的或非学习、非研究的商业行为。本项目不得用于任何形式的非法侵入他人计算机系统，不得用于任何侵犯他人知识产权或其他合法权益的行为。用户应保证其使用本项目的目的纯属个人学习和技术研究，不得用于任何形式的非法活动。

## 4. 免责声明
开发者已尽最大努力确保本项目的正当性及安全性，但不对用户使用本项目可能引起的任何形式的直接或间接损失承担责任。包括但不限于由于使用本项目而导致的任何数据丢失、设备损坏、法律诉讼等。

## 5. 知识产权声明
本项目的知识产权归开发者所有。本项目受到著作权法和国际著作权条约以及其他知识产权法律和条约的保护。用户在遵守本声明及相关法律法规的前提下，可以下载和使用本项目。

## 6. 最终解释权
关于本项目的最终解释权归开发者所有。开发者保留随时更改或更新本免责声明的权利，恕不另行通知。
</div>


## 🙏 致谢

### JetBrains 开源许可证支持

感谢 JetBrains 为本项目提供免费的开源许可证支持！

<a href="https://www.jetbrains.com/?from=MediaCrawler">
    <img src="https://www.jetbrains.com/company/brand/img/jetbrains_logo.png" width="100" alt="JetBrains" />
</a>
