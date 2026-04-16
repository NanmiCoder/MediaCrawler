# CDP模式使用指南

## 概述

CDP（Chrome DevTools Protocol）模式是一种高级的反检测爬虫技术，通过控制用户现有的Chrome/Edge浏览器来进行网页爬取。与传统的Playwright自动化相比，CDP模式具有以下优势：

### 🎯 主要优势

1. **真实浏览器环境**: 使用用户实际安装的浏览器，包含所有扩展、插件和个人设置
2. **更好的反检测能力**: 浏览器指纹更加真实，难以被网站检测为自动化工具
3. **保留用户状态**: 自动继承用户的登录状态、Cookie和浏览历史
4. **扩展支持**: 可以利用用户安装的广告拦截器、代理扩展等工具
5. **更自然的行为**: 浏览器行为模式更接近真实用户

### 📌 两种 CDP 模式

CDP模式支持两种使用方式：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **连接已有浏览器**（默认推荐） | 连接用户正在使用的 Chrome 浏览器，复用真实的 Cookie、扩展和浏览历史 | 反检测要求高，需要最大程度降低风控风险 |
| **启动新浏览器** | 自动检测并启动一个新的 Chrome/Edge 浏览器实例 | 不需要复用浏览器状态的场景 |

## 快速开始

### 方式一：连接已有浏览器（默认推荐）

这是**默认且推荐**的方式，直接连接你正在使用的 Chrome 浏览器，反检测效果最好。

#### 第一步：确保 Chrome 版本

需要 Chrome **144 或更高版本**（2026年1月起的稳定版均支持）。在地址栏输入 `chrome://version` 查看当前版本。

如果版本过低，请前往 [Chrome 官网](https://www.google.com/chrome/) 下载最新版。

#### 第二步：开启远程调试

1. 在 Chrome 地址栏输入：`chrome://inspect/#remote-debugging`
2. 勾选 **"Allow remote debugging for this browser instance"**
3. 页面会显示 `Server running at: 127.0.0.1:9222`，表示已就绪

#### 第三步：运行爬虫

```bash
uv run main.py --platform xhs --lt qrcode --type search
```

运行后，Chrome 浏览器会**弹出确认对话框**，点击"接受"即可。程序会等待用户确认（默认60秒超时）。

#### 配置说明

`config/base_config.py` 中的默认配置：

```python
# 启用CDP模式
ENABLE_CDP_MODE = True

# 连接已有浏览器（默认开启）
CDP_CONNECT_EXISTING = True

# CDP调试端口（与 chrome://inspect 页面显示的端口一致）
CDP_DEBUG_PORT = 9222
```

### 方式二：启动新浏览器

如果不想连接已有浏览器，可以让程序自动启动一个新的浏览器实例：

```python
ENABLE_CDP_MODE = True
CDP_CONNECT_EXISTING = False  # 关闭连接已有浏览器，改为启动新浏览器
```

## 配置选项详解

### 基础配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENABLE_CDP_MODE` | bool | True | 是否启用CDP模式 |
| `CDP_CONNECT_EXISTING` | bool | True | 是否连接已有浏览器（推荐开启） |
| `CDP_DEBUG_PORT` | int | 9222 | CDP调试端口 |
| `CDP_HEADLESS` | bool | False | CDP模式下的无头模式 |
| `AUTO_CLOSE_BROWSER` | bool | True | 程序结束时是否关闭浏览器 |

### 高级配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CUSTOM_BROWSER_PATH` | str | "" | 自定义浏览器路径（仅启动新浏览器模式下有效） |
| `BROWSER_LAUNCH_TIMEOUT` | int | 60 | 浏览器连接超时时间（秒） |

### 自定义浏览器路径

如果系统自动检测失败，可以手动指定浏览器路径：

```python
# Windows示例
CUSTOM_BROWSER_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# macOS示例  
CUSTOM_BROWSER_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Linux示例
CUSTOM_BROWSER_PATH = "/usr/bin/google-chrome"
```

## 支持的浏览器

### Windows
- Google Chrome (稳定版、Beta、Dev、Canary)
- Microsoft Edge (稳定版、Beta、Dev、Canary)

### macOS
- Google Chrome (稳定版、Beta、Dev、Canary)
- Microsoft Edge (稳定版、Beta、Dev、Canary)

### Linux
- Google Chrome / Chromium
- Microsoft Edge

## 使用示例

### 基本使用

```python
import asyncio
from playwright.async_api import async_playwright
from tools.cdp_browser import CDPBrowserManager

async def main():
    cdp_manager = CDPBrowserManager()
    
    async with async_playwright() as playwright:
        # 启动CDP浏览器
        browser_context = await cdp_manager.launch_and_connect(
            playwright=playwright,
            user_agent="自定义User-Agent",
            headless=False
        )
        
        # 创建页面并访问网站
        page = await browser_context.new_page()
        await page.goto("https://example.com")
        
        # 执行爬取操作...
        
        # 清理资源
        await cdp_manager.cleanup()

asyncio.run(main())
```

### 在爬虫中使用

CDP模式已集成到所有平台爬虫中，只需启用配置即可：

```python
# 在config/base_config.py中
ENABLE_CDP_MODE = True

# 然后正常运行爬虫
python main.py
```

## 故障排除

### 常见问题

#### 1. 浏览器检测失败
**错误**: `未找到可用的浏览器`

**解决方案**:
- 确保已安装Chrome或Edge浏览器
- 检查浏览器是否在标准路径下
- 使用`CUSTOM_BROWSER_PATH`指定浏览器路径

#### 2. 端口被占用
**错误**: `无法找到可用的端口`

**解决方案**:
- 关闭其他使用调试端口的程序
- 修改`CDP_DEBUG_PORT`为其他端口
- 系统会自动尝试下一个可用端口

#### 3. 浏览器启动超时
**错误**: `浏览器在30秒内未能启动`

**解决方案**:
- 增加`BROWSER_LAUNCH_TIMEOUT`值
- 检查系统资源是否充足
- 尝试关闭其他占用资源的程序

#### 4. CDP连接失败
**错误**: `CDP连接失败`

**解决方案**:
- 检查防火墙设置
- 确保localhost访问正常
- 尝试重启浏览器

### 调试技巧

#### 1. 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. 手动测试CDP连接
```bash
# 手动启动Chrome
chrome --remote-debugging-port=9222

# 访问调试页面
curl http://localhost:9222/json
```

#### 3. 检查浏览器进程
```bash
# Windows
tasklist | findstr chrome

# macOS/Linux  
ps aux | grep chrome
```

## 最佳实践

### 1. 反检测优化
- 保持`CDP_HEADLESS = False`以获得最佳反检测效果
- 使用真实的User-Agent字符串
- 避免过于频繁的请求

### 2. 性能优化
- 合理设置`AUTO_CLOSE_BROWSER`
- 复用浏览器实例而不是频繁重启
- 监控内存使用情况

### 3. 安全考虑
- 不要在生产环境中保存敏感Cookie
- 定期清理浏览器数据
- 注意用户隐私保护

### 4. 兼容性
- 测试不同浏览器版本的兼容性
- 准备回退方案（标准Playwright模式）
- 监控目标网站的反爬策略变化

## 技术原理

### 连接已有浏览器模式（推荐）

1. **用户开启远程调试**: 在 `chrome://inspect/#remote-debugging` 中勾选启用
2. **WebSocket连接**: 程序通过 `ws://localhost:9222/devtools/browser` 直接连接浏览器
3. **用户确认**: Chrome 弹出确认对话框，用户点击接受后连接建立
4. **Playwright集成**: 使用 `connectOverCDP` 方法接管浏览器控制
5. **上下文复用**: 直接使用浏览器已有的上下文（包含用户的Cookie、登录状态等）

> 💡 与传统CDP模式的区别：传统方式通过 `--remote-debugging-port` 启动新浏览器，使用 HTTP 接口 `/json/version` 获取 WebSocket URL。而连接已有浏览器方式直接通过 WebSocket 连接，Chrome 新版（136+）的远程调试不提供 HTTP 接口，需要用户在浏览器端确认授权。

### 启动新浏览器模式

1. **浏览器检测**: 自动扫描系统中的Chrome/Edge安装路径
2. **进程启动**: 使用`--remote-debugging-port`参数启动浏览器
3. **CDP连接**: 通过 HTTP 获取 WebSocket URL，再连接到浏览器的调试接口
4. **Playwright集成**: 使用`connectOverCDP`方法接管浏览器控制
5. **上下文管理**: 创建或复用浏览器上下文进行操作

两种方式都绕过了传统WebDriver的检测机制，提供了更加隐蔽的自动化能力。连接已有浏览器模式的反检测效果更好，因为使用的是用户真实的浏览器环境。

## 更新日志

### v1.0.0
- 初始版本发布
- 支持Windows和macOS的Chrome/Edge检测
- 集成到所有平台爬虫
- 提供完整的配置选项和错误处理

## 贡献

欢迎提交Issue和Pull Request来改进CDP模式功能。

## 许可证

本功能遵循项目的整体许可证条款，仅供学习和研究使用。
