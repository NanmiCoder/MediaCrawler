# MediaCrawler 项目指南

## 项目概述

MediaCrawler 是一个小红书爬虫项目，支持爬取笔记数据并提供 Web 可视化界面。

## 技术栈

- **后端**: Python + FastAPI
- **前端**: 纯 HTML/CSS/JavaScript（无框架）
- **数据存储**: JSONL 文件

## 开发规范

### Git 分支与 PR 规范

#### 分支命名

- `feat/xxx` - 新功能开发
- `fix/xxx` - Bug 修复
- `refactor/xxx` - 代码重构
- `docs/xxx` - 文档更新

#### PR 目标分支

**重要**: 所有 PR 必须提交到 `main` 分支，而非其他特性分支。

```
正确: feature/xxx → main
错误: feature/xxx → feat/xxx
```

#### 远程仓库配置

项目有两个远程仓库：

| 名称 | 地址 | 用途 |
|------|------|------|
| `origin` | git@github.com:NanmiCoder/MediaCrawler.git | 上游原始仓库 |
| `myfork` | git@github.com:J1anYi/MediaCrawler.git | 个人 Fork 仓库 |

推送代码到 Fork 仓库：
```bash
git push myfork feat/xxx:feat/xxx
```

创建 PR 时，确保：
- **Base 仓库**: J1anYi/MediaCrawler
- **Base 分支**: main
- **Head 分支**: feat/xxx

### 代码风格

#### Python

- 使用 4 空格缩进
- 遵循 PEP 8 规范
- 函数必须有类型注解
- 安全相关的输入验证必须完善

#### JavaScript

- 使用 2 空格缩进
- 使用 ES6+ 语法
- 避免全局变量污染，使用 `window.xxx` 导出

#### CSS

- 使用 BEM 命名规范
- 响应式设计优先

### 安全规范

1. **路径遍历防护**: 所有文件路径相关的用户输入必须验证
2. **输入验证**: 使用 FastAPI Query/Path 验证器
3. **类型注解**: 函数必须有返回类型注解

## 目录结构

```
MediaCrawler/
├── api/                    # FastAPI 后端
│   └── routers/
│       └── notes.py        # 笔记 API
├── viewer/                 # 前端可视化界面
│   ├── index.html
│   └── static/
│       ├── css/
│       └── js/
│           ├── app.js      # 主应用逻辑
│           ├── api.js      # API 封装
│           ├── modal.js    # 模态框组件
│           └── monitor.js  # 监控组件
├── data/                   # 数据目录
│   └── xhs/
│       ├── jsonl/          # 笔记数据
│       └── images/         # 图片资源
└── docs/                   # 文档
```

## 开发流程

1. 从 `main` 分支创建特性分支
2. 开发并测试
3. 运行代码审查
4. 推送到 Fork 仓库
5. 创建 PR 到 `main` 分支

## 本地开发

启动开发服务器：
```bash
python api/main.py
```

访问：
- 可视化界面: http://localhost:8080/viewer/index.html
- API 文档: http://localhost:8080/docs
