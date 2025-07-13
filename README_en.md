# 🔥 MediaCrawler - Social Media Platform Crawler 🕷️

<div align="center">

<a href="https://trendshift.io/repositories/8291" target="_blank">
  <img src="https://trendshift.io/api/badge/repositories/8291" alt="NanmiCoder%2FMediaCrawler | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
</a>

[![GitHub Stars](https://img.shields.io/github/stars/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/pulls)
[![License](https://img.shields.io/github/license/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE)
[![中文](https://img.shields.io/badge/🇨🇳_中文-Available-blue)](README.md)
[![English](https://img.shields.io/badge/🇺🇸_English-Current-green)](README_en.md)
[![Español](https://img.shields.io/badge/🇪🇸_Español-Available-green)](README_es.md)

</div>

> **Disclaimer:**
> 
> Please use this repository for learning purposes only ⚠️⚠️⚠️⚠️, [Web scraping illegal cases](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)  <br>
>
>All content in this repository is for learning and reference purposes only, and commercial use is prohibited. No person or organization may use the content of this repository for illegal purposes or infringe upon the legitimate rights and interests of others. The web scraping technology involved in this repository is only for learning and research, and may not be used for large-scale crawling of other platforms or other illegal activities. This repository assumes no legal responsibility for any legal liability arising from the use of the content of this repository. By using the content of this repository, you agree to all terms and conditions of this disclaimer.
>
> Click to view a more detailed disclaimer. [Click to jump](#disclaimer)

## 📖 Project Introduction

A powerful **multi-platform social media data collection tool** that supports crawling public information from mainstream platforms including Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, Zhihu, and more.

### 🔧 Technical Principles

- **Core Technology**: Based on [Playwright](https://playwright.dev/) browser automation framework for login and maintaining login state
- **No JS Reverse Engineering Required**: Uses browser context environment with preserved login state to obtain signature parameters through JS expressions
- **Advantages**: No need to reverse complex encryption algorithms, significantly lowering the technical barrier

## ✨ Features
| Platform | Keyword Search | Specific Post ID Crawling | Secondary Comments | Specific Creator Homepage | Login State Cache | IP Proxy Pool | Generate Comment Word Cloud | Smart URL Parsing | Interactive Input |
| ------ | ---------- | -------------- | -------- | -------------- | ---------- | -------- | -------------- | ------------ | ---------- |
| Xiaohongshu | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| Douyin   | ✅          | 🔥**Enhanced**  | ✅        | 🔥**Enhanced**  | ✅          | ✅        | ✅              | 🔥**New Feature** | 🔥**New Feature** |
| Kuaishou   | ✅          | 🔥**Enhanced**  | ✅        | 🔥**Enhanced**  | ✅          | ✅        | ✅              | 🔥**New Feature** | 🔥**New Feature** |
| Bilibili   | ✅          | 🔥**Enhanced**  | ✅        | 🔥**Enhanced**  | ✅          | ✅        | ✅              | 🔥**New Feature** | 🔥**New Feature** |
| Weibo   | ✅          | 🔥**Enhanced**  | ✅        | 🔥**Enhanced**  | ✅          | ✅        | ✅              | 🔥**New Feature** | 🔥**New Feature** |
| Tieba   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |
| Zhihu   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              | ❌            | ❌          |

### 🔥 Enhanced Features Highlights

#### 🎯 Unified Interactive Input
- **Smart Input Detection**: Automatically enables interactive input mode when configuration files are empty
- **Formatted Prompts**: Provides detailed input format examples and instructions
- **Mixed Format Support**: Supports simultaneous input of multiple formats (URLs, short links, IDs)

#### 🔗 Smart URL Parsing Engine
- **Short Link Redirection**: Intelligently parses shared short links and automatically redirects to get real URLs
- **Multi-Format Compatibility**: Supports complete URLs, short links, direct IDs and other input formats
- **Validation Mechanism**: Built-in ID validation to prevent errors from invalid input

#### 📱 Unified Command Line Interface
**New unified command format**:
```bash
# Unified use of --urls parameter, supports all platforms
uv run main.py --platform [dy|ks|wb|bili] --lt qrcode --type [search|detail|creator] --urls "URL1" "URL2" "URL3"
```

### 🔥 Douyin Enhanced Features

| Input Format | Example | Parsing Method |
|---------|------|----------|
| Complete User Homepage URL | `https://www.douyin.com/user/MS4wLjABAAAA...` | Extract sec_user_id directly |
| Complete Video URL | `https://www.douyin.com/video/7525082444551310602` | Extract video_id directly |
| Share Short Link | `https://v.douyin.com/J7v_LxD7vUQ/` | Smart redirection parsing |
| Direct ID | `MS4wLjABAAAA...` or `7525082444551310602` | Use directly |

### 🔥 Kuaishou Enhanced Features

| Input Format | Example | Parsing Method |
|---------|------|----------|
| Complete Video URL | `https://www.kuaishou.com/short-video/3xf8enb8dbj6uig` | Extract video_id directly |
| Complete User Homepage URL | `https://www.kuaishou.com/profile/3xi4kwp2pg8tp8k` | Extract user_id directly |
| Share Short Link | `https://v.kuaishou.com/2F50ZXj` | Smart redirection parsing |
| Direct ID | `3xf8enb8dbj6uig` or `3xi4kwp2pg8tp8k` | Use directly |

### 🔥 Bilibili Enhanced Features

| Input Format | Example | Parsing Method |
|---------|------|----------|
| Complete Video URL | `https://www.bilibili.com/video/BV1Q2MXzgEgW` | Extract BVID/AID directly |
| Complete User Space URL | `https://space.bilibili.com/449342345` | Extract UID directly |
| Share Short Link | `https://b23.tv/B6gPE4M` | Smart redirection parsing |
| Direct ID | `BV1Q2MXzgEgW` or `449342345` | Use directly |

### 🔥 Weibo Enhanced Features

| Input Format | Example | Parsing Method |
|---------|------|----------|
| Desktop Share Link | `https://weibo.com/7643904561/5182160183232445` | Extract post_id directly |
| Mobile URL | `https://m.weibo.cn/detail/5182160183232445` | Extract post_id directly |
| User Homepage URL | `https://weibo.com/u/5533390220` | Extract user_id directly |
| Direct ID | `5182160183232445` or `5533390220` | Use directly |


<details id="pro-version">
<summary>🔗 <strong>🚀 MediaCrawlerPro Major Release! More features, better architectural design!</strong></summary>

### 🚀 MediaCrawlerPro Major Release!

> Focus on learning mature project architectural design, not just crawling technology. The code design philosophy of the Pro version is equally worth in-depth study!

[MediaCrawlerPro](https://github.com/MediaCrawlerPro) core advantages over the open-source version:

#### 🎯 Core Feature Upgrades
- ✅ **Resume crawling functionality** (Key feature)
- ✅ **Multi-account + IP proxy pool support** (Key feature)
- ✅ **Remove Playwright dependency**, easier to use
- ✅ **Complete Linux environment support**

#### 🏗️ Architectural Design Optimization
- ✅ **Code refactoring optimization**, more readable and maintainable (decoupled JS signature logic)
- ✅ **Enterprise-level code quality**, suitable for building large-scale crawler projects
- ✅ **Perfect architectural design**, high scalability, greater source code learning value

#### 🎁 Additional Features
- ✅ **Social media video downloader desktop app** (suitable for learning full-stack development)
- ✅ **Multi-platform homepage feed recommendations** (HomeFeed)
- [ ] **AI Agent based on social media platforms is under development 🚀🚀**

Click to view: [MediaCrawlerPro Project Homepage](https://github.com/MediaCrawlerPro) for more information
</details>

## 🚀 Quick Start

> 💡 **Open source is not easy, if this project helps you, please give a ⭐ Star to support!**

## 📋 Prerequisites

### 🚀 uv Installation (Recommended)

Before proceeding with the next steps, please ensure that uv is installed on your computer:

- **Installation Guide**: [uv Official Installation Guide](https://docs.astral.sh/uv/getting-started/installation)
- **Verify Installation**: Enter the command `uv --version` in the terminal. If the version number is displayed normally, the installation was successful
- **Recommendation Reason**: uv is currently the most powerful Python package management tool, with fast speed and accurate dependency resolution

### 🟢 Node.js Installation

The project depends on Node.js, please download and install from the official website:

- **Download Link**: https://nodejs.org/en/download/
- **Version Requirement**: >= 16.0.0

### 📦 Python Package Installation

```shell
# Enter project directory
cd MediaCrawler

# Use uv sync command to ensure consistency of python version and related dependency packages
uv sync
```

### 🌐 Browser Driver Installation

```shell
# Install browser driver
uv run playwright install
```

> **💡 Tip**: MediaCrawler now supports using playwright to connect to your local Chrome browser, solving some issues caused by Webdriver.
>
> Currently, `xhs` and `dy` are available using CDP mode to connect to local browsers. If needed, check the configuration items in `config/base_config.py`.

## 🚀 Run Crawler Program

### Basic Usage

```shell
# The project does not enable comment crawling mode by default. If you need comments, please modify the ENABLE_GET_COMMENTS variable in config/base_config.py
# Other supported options can also be viewed in config/base_config.py with Chinese comments

# Keyword search crawling
uv run main.py --platform xhs --lt qrcode --type search

# Specified post ID crawling
uv run main.py --platform xhs --lt qrcode --type detail

# Creator homepage crawling
uv run main.py --platform xhs --lt qrcode --type creator

# For other platform crawler usage examples, execute the following command to view
uv run main.py --help
```

### 🔥 Unified Smart URL Parsing Feature

**No need to manually extract IDs, supports direct paste of share links, unified operation for all platforms**:

#### Interactive Input Mode (Recommended)
```shell
# Douyin Platform - Automatically enters interactive input after clearing configuration file
uv run main.py --platform dy --lt qrcode --type creator
uv run main.py --platform dy --lt qrcode --type detail

# Kuaishou Platform - Supports smart short link parsing
uv run main.py --platform ks --lt qrcode --type creator
uv run main.py --platform ks --lt qrcode --type detail

# Bilibili Platform - Supports b23.tv short link parsing
uv run main.py --platform bili --lt qrcode --type creator
uv run main.py --platform bili --lt qrcode --type detail

# Weibo Platform - Supports multiple URL formats
uv run main.py --platform wb --lt qrcode --type creator
uv run main.py --platform wb --lt qrcode --type detail
```

#### Command Line Direct Input
```shell
# Unified use of --urls parameter, supports all platforms
uv run main.py --platform dy --lt qrcode --type creator --urls "https://v.douyin.com/J7v_LxD7vUQ/"
uv run main.py --platform ks --lt qrcode --type detail --urls "https://v.kuaishou.com/2F50ZXj"
uv run main.py --platform bili --lt qrcode --type detail --urls "https://b23.tv/B6gPE4M"
uv run main.py --platform wb --lt qrcode --type creator --urls "https://weibo.com/u/5533390220"

# Batch crawling multiple targets
uv run main.py --platform dy --lt qrcode --type detail --urls "URL1" "URL2" "URL3"
```

**Supported Input Format Examples**:
- **Douyin**: `https://v.douyin.com/J7v_LxD7vUQ/`, `https://www.douyin.com/video/7525082444551310602`
- **Kuaishou**: `https://v.kuaishou.com/2F50ZXj`, `https://www.kuaishou.com/short-video/3xf8enb8dbj6uig`
- **Bilibili**: `https://b23.tv/B6gPE4M`, `https://www.bilibili.com/video/BV1Q2MXzgEgW`
- **Weibo**: Desktop, mobile URLs or direct IDs

<details>
<summary>🔗 <strong>Using Python native venv environment management (Not recommended)</strong></summary>

#### Create and activate Python virtual environment

> If crawling Douyin and Zhihu, you need to install nodejs environment in advance, version greater than or equal to: `16`

```shell
# Enter project root directory
cd MediaCrawler

# Create virtual environment
# My python version is: 3.9.6, the libraries in requirements.txt are based on this version
# If using other python versions, the libraries in requirements.txt may not be compatible, please resolve on your own
python -m venv venv

# macOS & Linux activate virtual environment
source venv/bin/activate

# Windows activate virtual environment
venv\Scripts\activate
```

#### Install dependency libraries

```shell
pip install -r requirements.txt
```

#### Install playwright browser driver

```shell
playwright install
```

#### Run crawler program (native environment)

```shell
# The project does not enable comment crawling mode by default. If you need comments, please modify the ENABLE_GET_COMMENTS variable in config/base_config.py
# Other supported options can also be viewed in config/base_config.py with Chinese comments

# Read keywords from configuration file to search related posts and crawl post information and comments
python main.py --platform xhs --lt qrcode --type search

# Read specified post ID list from configuration file to get information and comment information of specified posts
python main.py --platform xhs --lt qrcode --type detail

# Open corresponding APP to scan QR code for login

# For other platform crawler usage examples, execute the following command to view
python main.py --help
```

</details>


## 💾 Data Storage

Supports multiple data storage methods:

- **MySQL Database**: Supports saving to relational database MySQL (need to create database in advance)
  - Execute `python db.py` to initialize database table structure (only execute on first run)
- **CSV Files**: Supports saving to CSV (under `data/` directory)
- **JSON Files**: Supports saving to JSON (under `data/` directory)

---

[🚀 MediaCrawlerPro Major Release 🚀! More features, better architectural design!](https://github.com/MediaCrawlerPro)

## 🤝 Community & Support

### 💬 Discussion Groups
- **WeChat Discussion Group**: [Click to join](https://nanmicoder.github.io/MediaCrawler/%E5%BE%AE%E4%BF%A1%E4%BA%A4%E6%B5%81%E7%BE%A4.html)

### 📚 Documentation & Tutorials
- **Online Documentation**: [MediaCrawler Complete Documentation](https://nanmicoder.github.io/MediaCrawler/)
- **Crawler Tutorial**: [CrawlerTutorial Free Tutorial](https://github.com/NanmiCoder/CrawlerTutorial)


# Other common questions can be viewed in the online documentation
>
> The online documentation includes usage methods, common questions, joining project discussion groups, etc.
> [MediaCrawler Online Documentation](https://nanmicoder.github.io/MediaCrawler/)
>

# Author's Knowledge Services
> If you want to quickly get started and learn the usage of this project, source code architectural design, learn programming technology, or want to understand the source code design of MediaCrawlerPro, you can check out my paid knowledge column.

[Author's Paid Knowledge Column Introduction](https://nanmicoder.github.io/MediaCrawler/%E7%9F%A5%E8%AF%86%E4%BB%98%E8%B4%B9%E4%BB%8B%E7%BB%8D.html)


---

## ⭐ Star Trend Chart

If this project helps you, please give a ⭐ Star to support and let more people see MediaCrawler!

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)

### 💰 Sponsor Display

<a href="https://www.swiftproxy.net/?ref=nanmi">
<img src="docs/static/images/img_5.png">
<br>
**Swiftproxy** - 90M+ global high-quality pure residential IPs, register to get free 500MB test traffic, dynamic traffic never expires!
> Exclusive discount code: **GHB5** Get 10% off instantly!
</a>

<br><br>

<a href="https://sider.ai/ad-land-redirect?source=github&p1=mi&p2=kk">**Sider** - The hottest ChatGPT plugin on the web, amazing experience!</a>

### 🤝 Become a Sponsor

Become a sponsor and showcase your product here, getting massive exposure daily!

**Contact Information**:
- WeChat: `yzglan`
- Email: `relakkes@gmail.com`


## 📚 References

- **Xiaohongshu Client**: [ReaJason's xhs repository](https://github.com/ReaJason/xhs)
- **SMS Forwarding**: [SmsForwarder reference repository](https://github.com/pppscn/SmsForwarder)
- **Intranet Penetration Tool**: [ngrok official documentation](https://ngrok.com/docs/)


# Disclaimer
<div id="disclaimer">

## 1. Project Purpose and Nature
This project (hereinafter referred to as "this project") was created as a technical research and learning tool, aimed at exploring and learning network data collection technologies. This project focuses on research of data crawling technologies for social media platforms, intended to provide learners and researchers with technical exchange purposes.

## 2. Legal Compliance Statement
The project developer (hereinafter referred to as "developer") solemnly reminds users to strictly comply with relevant laws and regulations of the People's Republic of China when downloading, installing and using this project, including but not limited to the "Cybersecurity Law of the People's Republic of China", "Counter-Espionage Law of the People's Republic of China" and all applicable national laws and policies. Users shall bear all legal responsibilities that may arise from using this project.

## 3. Usage Purpose Restrictions
This project is strictly prohibited from being used for any illegal purposes or non-learning, non-research commercial activities. This project may not be used for any form of illegal intrusion into other people's computer systems, nor may it be used for any activities that infringe upon others' intellectual property rights or other legitimate rights and interests. Users should ensure that their use of this project is purely for personal learning and technical research, and may not be used for any form of illegal activities.

## 4. Disclaimer
The developer has made every effort to ensure the legitimacy and security of this project, but assumes no responsibility for any form of direct or indirect losses that may arise from users' use of this project. Including but not limited to any data loss, equipment damage, legal litigation, etc. caused by using this project.

## 5. Intellectual Property Statement
The intellectual property rights of this project belong to the developer. This project is protected by copyright law and international copyright treaties as well as other intellectual property laws and treaties. Users may download and use this project under the premise of complying with this statement and relevant laws and regulations.

## 6. Final Interpretation Rights
The developer has the final interpretation rights regarding this project. The developer reserves the right to change or update this disclaimer at any time without further notice.
</div>


## 🙏 Acknowledgments

### JetBrains Open Source License Support

Thanks to JetBrains for providing free open source license support for this project!

<a href="https://www.jetbrains.com/?from=MediaCrawler">
    <img src="https://www.jetbrains.com/company/brand/img/jetbrains_logo.png" width="100" alt="JetBrains" />
</a>
