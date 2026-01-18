# 📝 平台Cookie配置指南

## 🎯 概述

为了使API服务支持小红书和知乎，您需要配置这两个平台的Cookie。本指南将详细说明如何获取和配置Cookie。

---

## 🔧 配置流程

### 第1步：获取Cookie

#### 获取小红书Cookie

1. **访问小红书**
   - 在本地浏览器打开：https://www.xiaohongshu.com
   - 使用您的账号登录

2. **打开开发者工具**
   - 按 `F12` 键（或右键点击页面 → 检查）
   - 切换到 `Console`（控制台）标签

3. **获取Cookie**
   - 在控制台输入以下命令并按回车：
     ```javascript
     document.cookie
     ```
   - 复制输出的完整字符串（通常很长）

4. **Cookie示例格式**
   ```
   a1=...; webId=...; gid=...; web_session=...
   ```

#### 获取知乎Cookie

1. **访问知乎**
   - 在本地浏览器打开：https://www.zhihu.com
   - 使用您的账号登录

2. **打开开发者工具**
   - 按 `F12` 键（或右键点击页面 → 检查）
   - 切换到 `Console`（控制台）标签

3. **获取Cookie**
   - 在控制台输入以下命令并按回车：
     ```javascript
     document.cookie
     ```
   - 复制输出的完整字符串

4. **Cookie示例格式**
   ```
   _zap=...; d_c0=...; __snaker__id=...; z_c0=...
   ```

---

### 第2步：配置Cookie

打开文件 `test_platform_cookies.py`，找到以下部分并粘贴您获取的Cookie：

```python
# 小红书 Cookie（从 https://www.xiaohongshu.com 获取）
XHS_COOKIES = """
在这里粘贴小红书的Cookie
"""

# 知乎 Cookie（从 https://www.zhihu.com 获取）
ZHIHU_COOKIES = """
在这里粘贴知乎的Cookie
"""
```

**配置示例：**

```python
# 小红书 Cookie
XHS_COOKIES = "a1=18d123456789abcd; webId=12345abcde; gid=y1234567890; web_session=040069b12345abcde"

# 知乎 Cookie
ZHIHU_COOKIES = "_zap=12345-abcd; d_c0=ABCD123456; __snaker__id=12345678; z_c0=2|1:0|10:1234567890"
```

---

### 第3步：验证配置

运行配置验证工具：

```bash
cd /Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler
source venv/bin/activate
python test_platform_cookies.py
```

**期望输出：**

```
╔════════════════════════════════════════════════════════════════╗
║              MediaCrawler Cookie 配置工具                      ║
╚════════════════════════════════════════════════════════════════╝

================================================================================
平台Cookie配置状态
================================================================================

【抖音 (dy)】
  状态: ✅ 已配置
  预览: __ac_referer=__ac_blank; douyin.com; enter_pc_on...

【小红书 (xhs)】
  状态: ✅ 已配置
  预览: a1=18d123456789abcd; webId=12345abcde; gid=y123...

【知乎 (zhihu)】
  状态: ✅ 已配置
  预览: _zap=12345-abcd; d_c0=ABCD123456; __snaker__id...

================================================================================
```

---

### 第4步：测试API

启动API服务：

```bash
cd /Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler
./start_api.sh
```

访问API文档：http://localhost:8080/docs

---

## 🧪 测试各平台

### 测试小红书

```bash
curl -X POST "http://localhost:8080/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "keyword": "美妆教程",
    "max_count": 5,
    "enable_comments": true,
    "enable_media": false
  }'
```

### 测试知乎

```bash
curl -X POST "http://localhost:8080/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "keyword": "Python教程",
    "max_count": 5,
    "enable_comments": true,
    "enable_media": false
  }'
```

---

## ⚠️ 重要提示

### Cookie安全

1. **不要分享Cookie**
   - Cookie包含您的登录凭证
   - 不要将Cookie发送给他人或上传到公开仓库

2. **定期更新**
   - Cookie通常有效期为几周到几个月
   - 如果爬取失败，首先检查Cookie是否过期
   - 过期后重新获取并更新配置

3. **账号安全**
   - 使用非主账号进行测试
   - 注意平台的反爬虫策略
   - 合理控制请求频率

### Cookie有效性

**Cookie可能失效的情况：**
- 账号在其他设备登录
- 修改了账号密码
- 平台安全检测到异常
- Cookie自然过期

**失效表现：**
- API返回登录失败
- 爬取任务一直处于pending状态
- 返回"需要登录"的错误

**解决方法：**
- 重新获取Cookie
- 更新配置文件
- 重启API服务

---

## 📊 配置文件结构

```
MediaCrawler/
├── config/
│   ├── base_config.py       # 基础配置（自动使用test_platform_cookies.py中的Cookie）
│   ├── xhs_config.py        # 小红书平台特定配置
│   └── zhihu_config.py      # 知乎平台特定配置
├── test_platform_cookies.py # Cookie配置中心（您需要编辑此文件）
└── api_server.py           # API服务器（自动加载Cookie）
```

---

## 🎯 下一步

配置完成后：

1. ✅ 验证所有平台Cookie已配置
2. ✅ 启动API服务
3. ✅ 通过Swagger UI测试各平台
4. ✅ 集成到您的应用中

---

## 📞 常见问题

### Q1: 获取Cookie时找不到Console

**解决**：
- 按F12打开开发者工具
- 在顶部标签中找到"Console"或"控制台"
- 如果找不到，尝试点击">>"按钮查看更多标签

### Q2: Cookie太长，复制不完整

**解决**：
- 点击输出的Cookie字符串
- 按 Ctrl+A (全选) → Ctrl+C (复制)
- 或右键点击输出 → Copy string contents

### Q3: 配置后测试失败

**解决**：
1. 检查Cookie是否完整复制（没有遗漏开头或结尾）
2. 确保Cookie没有多余的引号或空格
3. 验证是否在登录状态下获取的Cookie
4. 尝试重新获取Cookie

### Q4: 如何判断Cookie是否有效

**方法1 - 运行验证脚本**：
```bash
python test_platform_cookies.py
```

**方法2 - 测试API**：
启动API服务后，通过Swagger UI创建测试任务

**方法3 - 查看日志**：
API服务启动后，日志会显示Cookie加载状态

---

## 💡 最佳实践

1. **使用独立测试账号**
   - 避免使用主账号
   - 降低账号风险

2. **定期更新Cookie**
   - 建议每月检查一次
   - 遇到问题时首先更新Cookie

3. **备份Cookie**
   - 在配置文件中保留旧Cookie的注释
   - 方便回滚

4. **监控爬取状态**
   - 注意API返回的错误信息
   - 及时处理Cookie失效问题

---

## 📚 相关文档

- `API使用文档.md` - API接口详细说明
- `API服务完成总结.md` - 功能总结和快速开始
- `最终使用指南.md` - MediaCrawler完整使用指南

---

**配置完成后，您的API服务将支持：**
- ✅ 抖音（已测试）
- ✅ 小红书（需配置Cookie）
- ✅ 知乎（需配置Cookie）

立即开始配置，让您的API服务支持更多平台！
