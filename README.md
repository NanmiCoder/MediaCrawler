# 🔥 MediaCrawler - Multi-Platform Media Crawler 🕷️

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



> **Disclaimer:**
> 
> Please use this repository for learning purposes only ⚠️⚠️⚠️⚠️, [Cases of illegal crawler activities](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)  <br>
>
>All contents of this repository are for learning and reference only, and are prohibited for commercial use. No individual or organization may use the contents of this repository for illegal purposes or to infringe on the legitimate rights and interests of others. The crawler technology involved in this repository is for learning and research only and may not be used for large-scale crawling of other platforms or other illegal activities. This repository does not assume any responsibility for any legal liability arising from the use of the contents. By using the contents of this repository, you agree to all terms and conditions of this disclaimer.
>
> Click here to view a more detailed disclaimer. [Jump to Disclaimer](#disclaimer)




## 📖 Project Overview

A powerful **multi-platform self-media data collection tool**, supporting public information scraping from major platforms such as Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, and Zhihu.

### 🔧 Technical Principles

- **Core Technology**: Based on [Playwright](https://playwright.dev/) browser automation framework for login session persistence
- **No JS Reverse Engineering Required**: Uses a browser context that preserves the login state to obtain signature parameters via JS expressions
- **Advantages**: No need to reverse complex encryption algorithms, greatly reducing technical barriers

## ✨ Features
| Platform | Keyword Search | Specific Post ID Crawl | Secondary Comments | Specific Creator Homepage | Login Session Cache | IP Proxy Pool | Generate Comment Wordcloud |
| -------- | --------------- | ---------------------- | ------------------ | ------------------------- | ------------------- | -------------- | -------------------------- |
| Xiaohongshu | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Douyin   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kuaishou | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bilibili | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Weibo    | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tieba    | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zhihu    | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |


<details id="pro-version">
<summary>🔗 <strong>🚀 MediaCrawlerPro Released! More features, better architecture design!</strong></summary>

### 🚀 MediaCrawlerPro Released!

> Focus on learning mature project architecture design, not just crawler technology. The Pro version's code design ideas are also worth studying in depth!

[MediaCrawlerPro](https://github.com/MediaCrawlerPro) key advantages compared to the open source version:

#### 🎯 Core Function Upgrades
- ✅ **Breakpoint Resume** (Key Feature)
- ✅ **Multi-Account + IP Proxy Pool Support** (Key Feature)
- ✅ **Removed Playwright Dependency**, simpler to use
- ✅ **Full Linux Environment Support**

#### 🏗️ Architecture Design Optimization
- ✅ **Refactored and Optimized Code**, easier to read and maintain (decoupled JS signature logic)
- ✅ **Enterprise-Level Code Quality**, suitable for building large crawler projects
- ✅ **Perfect Architecture Design**, high scalability, greater source code learning value

#### 🎁 Extra Features
- ✅ **Desktop Self-Media Video Downloader** (good for full-stack development learning)
- ✅ **Multi-Platform Homepage Feed Recommendation** (HomeFeed)
- [ ] **AI Agent Based on Self-Media Platform in Development 🚀🚀**

Click to view: [MediaCrawlerPro Project Homepage](https://github.com/MediaCrawlerPro) for more info
</details>

## 🚀 Quick Start

> 💡 **Open source is not easy. If this project helps you, please give it a ⭐ Star for support!**

## 📋 Prerequisites

### 🚀 Install uv (Recommended)

Before proceeding, make sure uv is installed on your computer:

- **Installation Guide**: [uv Official Installation Guide](https://docs.astral.sh/uv/getting-started/installation)
- **Verify Installation**: Run `uv --version` in terminal; if the version number is displayed, installation is successful.
- **Why uv**: uv is currently the most powerful Python package manager, fast and with accurate dependency resolution.

### 🟢 Install Node.js

This project requires Node.js. Please download and install it from the official website:

- **Download**: https://nodejs.org/en/download/
- **Version Requirement**: >= 16.0.0

### 📦 Install Python Packages

```shell
# Enter project directory
cd MediaCrawler

# Use uv sync to ensure consistent Python version and dependencies
uv sync
```

### 🌐 Install Browser Driver

```shell
# Install browser driver
uv run playwright install
```

> **💡 Tip**: MediaCrawler now supports using playwright to connect to your local Chrome browser, resolving issues caused by Webdriver.
>
> Currently, `xhs` and `dy` support connecting to the local browser using CDP. See `config/base_config.py` for configuration options if needed.

## 🚀 Run the Crawler

```shell
# By default, comment crawling is disabled. To enable it, modify ENABLE_GET_COMMENTS in config/base_config.py
# Other supported options can also be found in config/base_config.py with Chinese comments.

# Crawl posts and comments using keywords from config file
uv run main.py --platform xhs --lt qrcode --type search

# Get information and comments for specified post IDs from config file
uv run main.py --platform xhs --lt qrcode --type detail

# Scan the QR code in the corresponding app to log in

# For other platforms, run the command below for help
uv run main.py --help
```

<details>
<summary>🔗 <strong>Using Python native venv for environment management (Not Recommended)</strong></summary>

#### Create and Activate Python Virtual Environment

> For Douyin and Zhihu crawling, you need to install Node.js >= version 16

```shell
# Enter project root directory
cd MediaCrawler

# Create virtual environment
# My Python version: 3.9.6, requirements.txt is based on this version.
# For other Python versions, some packages may be incompatible; resolve manually.
python -m venv venv

# macOS & Linux activate virtual environment
source venv/bin/activate

# Windows activate virtual environment
venv\Scripts\activate
```

#### Install Dependencies

```shell
pip install -r requirements.txt
```

#### Install playwright Browser Driver

```shell
playwright install
```

#### Run Crawler (Native Environment)

```shell
# By default, comment crawling is disabled. To enable it, modify ENABLE_GET_COMMENTS in config/base_config.py
# Other supported options can also be found in config/base_config.py with Chinese comments.

# Crawl posts and comments using keywords from config file
python main.py --platform xhs --lt qrcode --type search

# Get information and comments for specified post IDs from config file
python main.py --platform xhs --lt qrcode --type detail

# Scan the QR code in the corresponding app to log in

# For other platforms, run the command below for help
python main.py --help
```

</details>


## 💾 Data Storage

Supports multiple storage options:

- **MySQL Database**: Save to MySQL relational database (create database in advance)
  - Run `python db.py` to initialize database tables (only for first run)
- **CSV File**: Save to CSV (`data/` directory)
- **JSON File**: Save to JSON (`data/` directory)

---

[🚀 MediaCrawlerPro Released 🚀! More features, better architecture design!](https://github.com/MediaCrawlerPro)

## 🤝 Community and Support

### 💬 Group Chat
- **WeChat Group**: [Join here](https://nanmicoder.github.io/MediaCrawler/%E5%BE%AE%E4%BF%A1%E4%BA%A4%E6%B5%81%E7%BE%A4.html)

### 📚 Docs and Tutorials
- **Online Docs**: [Complete MediaCrawler Docs](https://nanmicoder.github.io/MediaCrawler/)
- **Crawler Tutorials**: [CrawlerTutorial Free Tutorials](https://github.com/NanmiCoder/CrawlerTutorial)
  

# For other common issues, check the online documentation
> 
> The online docs include usage guides, FAQs, how to join the group chat, and more.
> [MediaCrawler Online Docs](https://nanmicoder.github.io/MediaCrawler/)
> 

# Knowledge Services Provided by the Author
> If you want to quickly learn how to use this project, understand its source code architecture, learn programming techniques, or explore the source code design of MediaCrawlerPro, check out my paid knowledge column.

[Author's Paid Knowledge Column Introduction](https://nanmicoder.github.io/MediaCrawler/%E7%9F%A5%E8%AF%86%E4%BB%98%E8%B4%B9%E4%BB%8B%E7%BB%8D.html)


---

## ⭐ Star History Chart

If this project helps you, please give it a ⭐ Star to support and let more people discover MediaCrawler!

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)

### 💰 Sponsor Display


<img src="docs/static/images/img_5.png" alt="Swiftproxy Banner">

<br>

<a href="https://www.swiftproxy.net/?ref=nanmi">
  <strong>Swiftproxy</strong> - 90M+ high-quality global residential IPs, register to get free 500MB test traffic, dynamic traffic never expires!  
  <br>
  <blockquote>Exclusive discount code: <strong>GHB5</strong> for 10% off!</blockquote>
</a>

<br><br>

<a href="https://sider.ai/ad-land-redirect?source=github&p1=mi&p2=kk">
  <strong>Sider</strong> - The hottest ChatGPT plugin on the web, ultimate experience!
</a>


### 🤝 Become a Sponsor

Become a sponsor and showcase your product here, getting massive daily exposure!

**Contact Info**:
- WeChat: `yzglan`
- Email: `relakkes@gmail.com`


## 📚 References

- **Xiaohongshu Client**: [ReaJason's xhs repository](https://github.com/ReaJason/xhs)
- **SMS Forwarding**: [SmsForwarder Reference Repository](https://github.com/pppscn/SmsForwarder)
- **Intranet Penetration Tool**: [ngrok Official Docs](https://ngrok.com/docs/)


# Disclaimer
<div id="disclaimer"> 

## 1. Project Purpose and Nature
This project (hereinafter referred to as “the Project”) was created as a tool for technical research and learning, intended to explore and study web data scraping technologies. This Project focuses on the study of data scraping technology for self-media platforms and is provided for learners and researchers for technical communication only.

## 2. Legal Compliance Statement
The Project developers (hereinafter referred to as “Developers”) solemnly remind users to strictly comply with the relevant laws and regulations of the People’s Republic of China, including but not limited to the Cybersecurity Law of the People’s Republic of China, the Counter-Espionage Law of the People’s Republic of China, and all other applicable national laws and policies when downloading, installing, and using the Project. Users shall bear all legal responsibility arising from their use of the Project.

## 3. Usage Purpose Restriction
This Project is strictly prohibited from being used for any illegal purpose or for commercial activities other than learning or research. This Project may not be used for any form of illegal intrusion into other computer systems, nor for infringing the intellectual property rights or other legitimate rights and interests of others. Users must ensure that their use of this Project is solely for personal learning and technical research and must not be used for any form of illegal activity.

## 4. Disclaimer
The Developers have made every effort to ensure the legitimacy and security of this Project but assume no responsibility for any direct or indirect loss that may result from the use of this Project, including but not limited to data loss, equipment damage, legal proceedings, etc.

## 5. Intellectual Property Statement
The intellectual property of this Project belongs to the Developers. This Project is protected by copyright law and international copyright treaties, as well as other intellectual property laws and treaties. Users may download and use this Project in compliance with this statement and relevant laws and regulations.

## 6. Final Interpretation Right
The final right of interpretation of this Project belongs to the Developers. The Developers reserve the right to modify or update this disclaimer at any time without prior notice.
</div>


## 🙏 Acknowledgements

### JetBrains Open Source License Support

Thanks to JetBrains for providing free open source license support for this Project!

<a href="https://www.jetbrains.com/?from=MediaCrawler">
    <img src="https://www.jetbrains.com/company/brand/img/jetbrains_logo.png" width="100" alt="JetBrains" />
</a>
