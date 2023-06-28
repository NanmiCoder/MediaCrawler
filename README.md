> **免责声明：**

>本仓库的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。

# 仓库描述

**小红书爬虫**，**抖音爬虫** ...。  
目前能稳定抓取小红书的视频、图片、评论、点赞、转发等信息，抖音的视频、图片、评论、点赞等信息。

原理：利用[playwright](https://playwright.dev/)搭桥，保留登录成功后的上下文浏览器环境，通过执行JS表达式获取一些加密参数
通过使用此方式，免去了复现核心加密JS代码，逆向难度大大降低。

## 项目特点
- 类型注解，代码结构清晰，方便阅读
- 项目实现有点复杂，但是使用起来比较稳定
- 这种利用浏览器搭桥的方式可以应用到其他平台的爬虫，只需要修改一些参数即可


## 已实现

- [x] 小红书登录（二维码、手机号、cookies）
- [x] 小红书Sign请求签名
- [x] 抖音Sign请求签名
- [x] 代理池实现（手机号+IP）
- [x] 并发执行爬虫请求

## 待实现

- [ ] 抖音登录（滑块）
- [ ] 数据持久化到硬盘

## 使用方法

1. 安装依赖库
   `pip install -r requirements.txt`
2. 安装playwright浏览器驱动
   `playwright install`
3. 运行爬虫程序
   `python main.py --platform xhs --lt qrcode`
4. 打开小红书扫二维码登录

## 项目代码结构

```
MediaCrawler
├── base 
│   ├── base_crawler.py # 项目的抽象类
│   └── proxy_account_pool.py # 账号与IP代理池
├── config 
│   ├── account_config.py # 基础配置
│   └── base_config.py # 账号池配置
├── images 
│   ├── douyin.gif
│   └── xiaohongshu.git
├── libs 
│   ├── douyin.js # 抖音Sign函数
│   └── stealth.min.js # 去除浏览器自动化特征的JS
├── media_platform
│   ├── douyin # 抖音crawler实现
│   │   ├── client.py # 抖音API httpx 请求封装
│   │   ├── core.py # 抖音crawler的核心实现
│   │   ├── exception.py # 抖音crawler的异常处理
│   │   ├── field.py # 抖音crawler的字段定义
│   │   └── login.py # 抖音crawler的登录实现  
│   └── xiaohongshu # 小红书crawler实现
│       ├── client.py # 小红书API httpx 请求封装
│       ├── core.py # 小红书crawler的核心实现
│       ├── exception.py # 小红书crawler的异常处理
│       ├── field.py # 小红书crawler的字段定义
│       ├── help.py # 小红书crawler的辅助函数
│       └── login.py # 小红书crawler的登录实现
├── modles 
│   ├── douyin
│   │   └── m_douyin.py
│   └── xhs
│       └── m_xhs.py
├── tools
│   └── utils.py # 工具函数
├── main.py # 程序入口
└── recv_sms_notification.py # 短信转发器的HTTP SERVER接口
```

## 小红书运行截图

![小红书运行截图](https://s2.loli.net/2023/06/09/PVBe3X5vf4yncrd.gif)

## 抖音运行截图

- ![抖音运行截图](https://s2.loli.net/2023/06/25/GXfkeLhpTyNiAqH.gif)


## 支持一下

- 如果该项目对你有帮助，star一下 ❤️❤️❤️

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)

- 如果该项目对你有帮助，可以请作者喝杯咖啡😊😊😊
<img src="https://s2.loli.net/2023/06/16/luz5tyeHgFxhbfc.png" style="margin-top:10px">

## 关于手机号+验证码登录的说明

当在浏览器模拟人为发起手机号登录请求时,使用短信转发软件将验证码发送至爬虫端回填,完成自动登录

准备工作：

- 安卓机1台（IOS没去研究，理论上监控短信也是可行的）
- 安装短信转发软件 [参考仓库](https://github.com/pppscn/SmsForwarder)
- 转发软件中配置WEBHOOK相关的信息，主要分为 消息模板（请查看本项目中的recv_sms_notification.py）、一个能push短信通知的API地址
- push的API地址一般是需要绑定一个域名的（当然也可以是内网的IP地址），我用的是内网穿透方式，会有一个免费的域名绑定到内网的web
  server，内网穿透工具 [ngrok](https://ngrok.com/docs/)
- 安装redis并设置一个密码 [redis安装](https://www.cnblogs.com/hunanzp/p/12304622.html)
- 执行 `python recv_sms_notification.py` 等待短信转发器发送HTTP通知
- 执行手机号登录的爬虫程序 `python main.py --platform xhs --lt phone`

备注：

- 小红书这边一个手机号一天只能发10条短信（悠着点），目前在发验证码时还未触发滑块验证，估计多了之后也会有~
-
短信转发软件会不会监控自己手机上其他短信内容？（理论上应该不会，因为[短信转发仓库](https://github.com/pppscn/SmsForwarder)
star还是蛮多的）


## 参考

- xhs客户端 [ReaJason的xhs仓库](https://github.com/ReaJason/xhs)
- 短信转发 [参考仓库](https://github.com/pppscn/SmsForwarder)
- 内网穿透工具 [ngrok](https://ngrok.com/docs/)

