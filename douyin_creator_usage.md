# 抖音创作者爬虫使用指南

## 🎯 功能介绍

现在支持通过抖音作者主页地址或sec_uid爬取该作者的所有视频详细信息，支持以下输入格式：

1. **完整URL**: `https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE`
2. **用户名URL**: `https://www.douyin.com/@username` (通过搜索API解析)
3. **短链接**: `https://v.douyin.com/iXXXXXX/` (通过浏览器重定向解析)
4. **sec_user_id**: `MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE`

## 📖 使用方法

### 方法一：命令行参数输入（推荐）

```bash
# 单个创作者
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE"

# 多个创作者（用空格分隔）
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE" "https://v.douyin.com/iXXXXXX/" "MS4wLjABAAAAYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"

# 支持短链接
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "https://v.douyin.com/iXXXXXX/"

# 直接使用sec_user_id
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE"
```

### 方法二：交互式输入

```bash
# 运行基础命令，程序会提示输入
uv run main.py --platform dy --lt qrcode --type creator
```

然后程序会显示提示界面：
```
============================================================
🎯 抖音创作者爬取模式
============================================================
请输入创作者信息，支持以下格式：
1. 完整URL: https://www.douyin.com/user/MS4wLjABAAAA...
2. 用户名URL: https://www.douyin.com/@username
3. 短链接: https://v.douyin.com/iXXXXXX/
4. sec_user_id: MS4wLjABAAAA...
5. 多个输入用空格分隔
------------------------------------------------------------
请输入创作者URL或sec_user_id (回车键结束): 
```

### 方法三：配置文件设置

编辑 `config/base_config.py`：

```python
# 设置平台和爬取类型
PLATFORM = "dy"
CRAWLER_TYPE = "creator"

# 设置创作者URL列表
DY_CREATOR_URL_LIST = [
    "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    "https://v.douyin.com/iXXXXXX/",  # 支持短链接
    "MS4wLjABAAAAYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",  # 直接使用sec_user_id
]
```

然后运行：
```bash
uv run main.py --platform dy --lt qrcode --type creator
```

## 🔧 如何获取抖音创作者链接

### 方法1：从浏览器复制
1. 在浏览器中打开抖音网页版
2. 搜索并进入目标创作者主页
3. 复制浏览器地址栏的URL

### 方法2：从抖音APP分享
1. 在抖音APP中进入创作者主页
2. 点击"分享"按钮
3. 选择"复制链接"
4. 粘贴得到的短链接

## 📊 爬取的数据内容

系统会爬取以下信息：

### 创作者信息
- 用户名、头像、简介
- 粉丝数、关注数、点赞数
- 认证信息等

### 视频详细信息（与单个视频爬取格式一致）
- 视频ID、标题、描述
- 播放量、点赞数、评论数、分享数
- 发布时间、视频时长
- 视频封面、下载链接
- 视频标签、话题
- 评论信息（如果开启评论爬取）

## ⚙️ 常用配置

在 `config/base_config.py` 中可以调整以下设置：

```python
# 是否爬取评论
ENABLE_GET_COMMENTS = True

# 是否爬取二级评论
ENABLE_GET_SUB_COMMENTS = False

# 每个视频最大评论数
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 数据保存格式 (csv/db/json)
SAVE_DATA_OPTION = "csv"

# 并发数量
MAX_CONCURRENCY_NUM = 1
```

## 📁 数据保存位置

- **CSV文件**: `data/douyin/` 目录下
- **JSON文件**: `data/douyin/json/` 目录下
- **数据库**: 需要先运行 `python db.py` 初始化数据库

## ⚠️ 注意事项

1. **登录要求**: 首次使用需要扫码登录抖音账号
2. **频率控制**: 建议设置合理的爬取间隔，避免被限制
3. **数据量**: 热门创作者可能有大量视频，爬取时间较长
4. **短链接**: 短链接需要网络访问来解析，请确保网络连接正常

## 🚀 示例命令

```bash
# 最简单的用法 - 会提示交互输入
uv run main.py --platform dy --lt qrcode --type creator

# 指定单个创作者URL
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "https://www.douyin.com/user/MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE"

# 批量爬取多个创作者
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "URL1" "URL2" "URL3"

# 关闭评论爬取以提高速度
uv run main.py --platform dy --lt qrcode --type creator --creator_urls "URL" --get_comment false
```

## 🔍 故障排除

### 1. URL解析失败
- 检查URL格式是否正确
- 确认是抖音创作者主页链接
- 尝试使用完整URL而不是短链接

### 2. 短链接解析失败
- 确保网络连接正常
- 短链接可能已过期，尝试重新获取

### 3. 爬取失败
- 检查账号是否正常登录
- 确认目标创作者主页是否公开
- 检查网络连接和代理设置

---

**提示**: 本工具仅供学习研究使用，请遵守相关法律法规和平台使用条款。