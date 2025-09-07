# 项目代码结构

```
MediaCrawler
├── base
│   └── base_crawler.py         # 项目的抽象基类
├── cache
│   ├── abs_cache.py            # 缓存抽象基类
│   ├── cache_factory.py        # 缓存工厂
│   ├── local_cache.py          # 本地缓存实现
│   └── redis_cache.py          # Redis缓存实现
├── cmd_arg
│   └── arg.py                  # 命令行参数定义
├── config
│   ├── base_config.py          # 基础配置
│   ├── db_config.py            # 数据库配置
│   └── ...                     # 各平台配置文件
├── constant
│   └── ...                     # 各平台常量定义
├── database
│   ├── db.py                   # 数据库ORM，封装增删改查
│   ├── db_session.py           # 数据库会话管理
│   └── models.py               # 数据库模型定义
├── docs
│   └── ...                     # 项目文档
├── libs
│   ├── douyin.js               # 抖音Sign函数
│   ├── stealth.min.js          # 去除浏览器自动化特征的JS
│   └── zhihu.js                # 知乎Sign函数
├── media_platform
│   ├── bilibili                # B站采集实现
│   ├── douyin                  # 抖音采集实现
│   ├── kuaishou                # 快手采集实现
│   ├── tieba                   # 百度贴吧采集实现
│   ├── weibo                   # 微博采集实现
│   ├── xhs                     # 小红书采集实现
│   └── zhihu                   # 知乎采集实现
├── model
│   ├── m_baidu_tieba.py        # 百度贴吧数据模型
│   ├── m_douyin.py             # 抖音数据模型
│   ├── m_kuaishou.py           # 快手数据模型
│   ├── m_weibo.py              # 微博数据模型
│   ├── m_xiaohongshu.py        # 小红书数据模型
│   └── m_zhihu.py              # 知乎数据模型
├── proxy
│   ├── base_proxy.py           # 代理基类
│   ├── providers               # 代理提供商实现
│   ├── proxy_ip_pool.py        # 代理IP池
│   └── types.py                # 代理类型定义
├── store
│   ├── bilibili                # B站数据存储实现
│   ├── douyin                  # 抖音数据存储实现
│   ├── kuaishou                # 快手数据存储实现
│   ├── tieba                   # 贴吧数据存储实现
│   ├── weibo                   # 微博数据存储实现
│   ├── xhs                     # 小红书数据存储实现
│   └── zhihu                   # 知乎数据存储实现
├── test
│   ├── test_db_sync.py         # 数据库同步测试
│   ├── test_proxy_ip_pool.py   # 代理IP池测试
│   └── ...                     # 其他测试用例
├── tools
│   ├── browser_launcher.py     # 浏览器启动器
│   ├── cdp_browser.py          # CDP浏览器控制
│   ├── crawler_util.py         # 爬虫工具函数
│   ├── utils.py                # 通用工具函数
│   └── ...
├── main.py                     # 程序入口, 支持 --init_db 参数来初始化数据库
├── recv_sms.py                 # 短信转发HTTP SERVER接口
└── var.py                      # 全局上下文变量定义
```