# 订阅 MediaCrawlerPro 版本源码访问权限

> **免责声明**：本项目的所有源代码内容仅供个人学习和参考之用，禁止用于任何商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。

## 获取 Pro 版本的访问权限

> 如果感兴趣可以加我微信，订阅 Pro 版本访问权限，有门槛 💰。订阅后可以访问下方仓库列表中全部项目的源代码。
>
> ⚠️⚠️ **仅针对个人想学习 Pro 版本源码实现的用户，如果是公司或者商业化盈利性质的就不要加我了，谢谢 🙏**
>
> 代码设计扩展性强，可以自行扩展更多爬虫平台和数据存储方式，适合学习爬虫项目的架构设计。
>
> **MediaCrawlerPro 项目主页（含完整 UI 截图与最新更新日志）**：[https://github.com/MediaCrawlerPro](https://github.com/MediaCrawlerPro)

扫描下方我的个人微信，备注：**pro版本**

> 如果两个微信扫码都显示频繁添加的话，可以尝试通过搜索微信号：`nmcode`、`relakkes` 这两个都可以。

<table>
  <tr>
    <td align="center">
      <img alt="个人微信 nmcode" src="./static/images/nmcode_wechat.jpg" width="200"><br>
      <b>个人微信</b>
    </td>
    <td align="center">
      <img alt="个人微信2 relakkes" src="./static/images/relakkes_weichat.jpg" width="200"><br>
      <b>个人微信2（备用）</b>
    </td>
  </tr>
</table>

## MediaCrawlerPro 项目介绍

### [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的 Pro 版本 Python 实现

支持 **小红书**、**抖音**、**快手**、**B站**、**微博**、**知乎**、**贴吧**、**Reddit** 等多平台公开数据采集与多种存储方式，最重要的是**支持多账号 + IP 代理池机制，适合深入学习爬虫工程架构**。

相较于开源版 MediaCrawler，Pro 版本最大的变化：
- 增加**断点续爬**，可以恢复上次爬取的进度
- 支持**多账号 + IP 代理池**，学习更稳定的调度机制
- **去掉 Playwright 依赖**，爬虫主干更轻量，完整支持 Linux 与 Docker 部署
- 新增独立**签名服务**，解耦签名逻辑，架构更灵活
- 支持多个平台的**首页信息流推荐（HomeFeed）**和**热搜榜单**
- 新增**自媒体视频下载器桌面端**（适合学习全栈开发）
- 附赠多个 **AI Agent 项目源码**：内容拆解、图片生成、评论分析

### 🤖 AI Agent Skill 支持（OpenClaw 🦞 / Claude Code / Codex）

MediaCrawlerPro 的 CLI 能力支持以 **Skill** 的形式安装到 AI Coding Agent 中，让 Agent 具备自媒体数据采集能力，对 Agent 说句话就能自动调用：

- **[OpenClaw](https://openclaw.ai/) 🦞** — 一键安装 Skill
- **Claude Code** — 复制到 `~/.claude/skills/` 目录
- **Codex** — 复制到 `~/.codex/skills/` 目录
- **Cursor / Windsurf** — 复制到项目规则目录

<details>
<summary><b>🤖 附赠：ContentRemixAgent - AI 内容分析 Agent</b></summary>

基于 **LangGraph Agent** 架构的内容分析工具，帮助学习如何用 Agent 解析内容、提取爆款结构。

核心功能：
- **多平台内容解析**：支持小红书、抖音、B站、快手等平台链接解析
- **视频转文字**：自动提取视频音频并转录为文字
- **爆款元素拆解**：AI 分析内容结构、选题技巧、情绪价值等爆款因素
- **分析报告生成**：基于分析结果生成结构化的内容拆解报告

技术栈：FastAPI + LangGraph + React + TailwindCSS
</details>

<details>
<summary><b>🎨 附赠：PicTacticAgent - AI 智能图片生成工具</b></summary>

基于 **LangGraph** 多轮迭代工作流的图片生成工具，彻底解决文生图“抽卡”问题。同样支持以 **Skill** 形式安装到 **[OpenClaw](https://openclaw.ai/) 🦞** 和 **Claude Code** 中。

核心功能：
- **OpenClaw / Claude Code Skill 集成**：安装 Skill 后，对 Agent 说“帮我生成一张封面图”即可自动调用
- **多轮迭代生成**：自动评估 + 迭代优化，告别手动“抽卡”
- **199 条精选模板库**：经 Vision LLM 锦标赛筛选的高质量提示词模板

技术栈：FastAPI + LangGraph + React 19 + TailwindCSS 4，支持 Web / CLI / Skill 三种使用方式
</details>

<details>
<summary><b>🆕 新上线：VoxAgent - AI 评论分析 Agent</b></summary>

输入关键词、博主主页或内容链接，自动调用 MediaCrawlerPro 采集评论，由大模型逐条标注，再由程序统计并生成研究报告。

核心功能：
- **三种研究入口**：关键词、博主主页、单条内容链接，支持 B站、小红书、抖音、Reddit
- **逐条标注**：情绪、意图、立场、讨论方面
- **结论可核对**：报告里的数字由程序统计，每段结论都能回到原评论
- **断点继续**：研究可随时暂停，从已保存的进度继续，已完成的标注不重复计费
- **报告导出**：HTML、Markdown、PDF

技术栈：Python + TypeScript（Fastify + React），模型调用基于 Pi Agent，支持 DeepSeek、Kimi、智谱 GLM、通义千问、Claude、OpenAI 等模型
</details>

## 功能列表

| 平台 | 断点续爬 | 关键词搜索 | 指定帖子ID爬取 | 二级评论 | 创作者主页 | 首页推荐信息流 | 账号池 + IP代理池 | 热搜 |
| ---- | -------- | ---------- | -------------- | -------- | ---------- | -------------- | ----------------- | ---- |
| 小红书 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 抖音 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 快手 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| B 站 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 知乎 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 微博 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Pro 源代码仓库学习列表

订阅后可访问以下全部仓库的源代码：

- 🧹 **MediaCrawlerPro-Python**：开源项目 MediaCrawler 的重构，移除 Playwright、增加多账号 + IP 代理池、代码优化
- 🎯 **MediaCrawlerPro-SignSrv**：爬虫 JS 签名逻辑单独抽出来作为最底层依赖服务
- 🔗 **MediaCrawlerPro-Downloader**：自媒体平台视频（图片）下载器，全栈项目（前端 + 后端 + 爬虫），适合学习全栈开发
- 🍪 **MediaCrawlerPro-CookieBridge**：Chrome Extension + Server，自动同步浏览器 Cookie，告别手动复制粘贴
- 🛠️ **MediaCrawlerPro-Golang**：Golang 语言版本，目前实现了最基本的 xhs 流程，开发中
- 🤖 **MediaCrawlerPro-ContentRemixAgent**：AI 驱动的内容分析 Agent，基于 LangGraph 架构，支持多平台内容解析、视频转文字、爆款元素拆解与报告生成
- 🎨 **PicTacticAgent**：AI 智能图片生成工具，支持 OpenClaw / Claude Code Skill 集成，基于 LangGraph 多轮迭代工作流，内置 199 条精选模板库
- 💬 **MediaCrawlerPro-VoxAgent**：🆕 AI 评论分析 Agent，输入关键词或链接，自动采集评论、逐条标注，生成可回到原评论核对的研究报告

> 👉 查看各项目 UI 截图与完整更新日志，请前往 **[MediaCrawlerPro GitHub 主页](https://github.com/MediaCrawlerPro)**。
