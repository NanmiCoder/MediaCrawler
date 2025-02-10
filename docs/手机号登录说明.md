# 关于手机号+验证码登录的说明
> 配置过程相当复杂，不建议采用该种方式

当在浏览器模拟人为发起手机号登录请求时，使用短信转发软件将验证码发送至爬虫端回填，完成自动登录

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

- 短信转发软件会不会监控自己手机上其他短信内容？（理论上应该不会，因为[短信转发仓库](https://github.com/pppscn/SmsForwarder)
star还是蛮多的）