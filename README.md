> **！！免责声明：！！**

> 本仓库的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。

# 仓库描述
这个代码仓库是一个利用[playwright](https://playwright.dev/)的爬虫程序，可以准确地爬取小红书、抖音的笔记、评论等信息。  
原理：利用playwright登录成功后，保留登录成功后的上下文浏览器环境，通过上下文浏览器环境执行JS表达式获取一些加密参数，
再使用[httpx](https://github.com/encode/httpx)发起异步请求，相当于使用Playwright搭桥，免去了复现核心加密JS代码，逆向难度大大降低。  



## 主要功能
- [x] 小红书 笔记、评论
- [x] 小红书 二维码扫描登录 | 手机号+验证码自动登录 | cookies登录
- [x] 爬取抖音视频、评论
- [ ] To do 抖音滑块

## 技术栈

- playwright
- httpx
- Web逆向

## 使用方法

1. 安装依赖库
   `pip install -r requirements.txt`
2. 安装playwright浏览器驱动
   `playwright install`
3. 运行爬虫程序
   `python main.py --platform xhs --keywords 健身 --lt qrcode`
4. 打开小红书扫二维码登录

## 小红书运行截图
![小红书运行截图](https://s2.loli.net/2023/06/09/PVBe3X5vf4yncrd.gif)

## 抖音运行截图
- ![抖音运行截图](https://s2.loli.net/2023/06/25/GXfkeLhpTyNiAqH.gif)

## 关于手机号+验证码登录的说明
当在小红书等平台上使用手机登录时，发送验证码后，使用短信转发器完成验证码转发。  

准备工作：
- 安卓机1台（IOS没去研究，理论上监控短信也是可行的）
- 安装短信转发软件 [参考仓库](https://github.com/pppscn/SmsForwarder)
- 转发软件中配置WEBHOOK相关的信息，主要分为 消息模板（请查看本项目中的recv_sms_notification.py）、一个能push短信通知的API地址
- push的API地址一般是需要绑定一个域名的（当然也可以是内网的IP地址），我用的是内网穿透方式，会有一个免费的域名绑定到内网的web server，内网穿透工具 [ngrok](https://ngrok.com/docs/)
- 安装redis并设置一个密码 [redis安装](https://www.cnblogs.com/hunanzp/p/12304622.html)
- 执行 `python recv_sms_notification.py` 等待短信转发器发送HTTP通知
- 执行手机号登录的爬虫程序 `python main.py --platform xhs --keywords 健身 --lt phone --phone 13812345678`

备注：
- 小红书这边一个手机号一天只能发10条短信（悠着点），目前在发验证码时还未触发滑块验证，估计多了之后也会有~
- 短信转发软件会不会监控自己手机上其他短信内容？（理论上应该不会，因为[短信转发仓库](https://github.com/pppscn/SmsForwarder)star还是蛮多的）

## 支持一下
- 如果该项目对你有帮助，star一下  ❤️❤️❤️



[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)



## 参考
- xhs客户端 [ReaJason的xhs仓库](https://github.com/ReaJason/xhs)
- 短信转发 [参考仓库](https://github.com/pppscn/SmsForwarder)
- 内网穿透工具 [ngrok](https://ngrok.com/docs/) 

