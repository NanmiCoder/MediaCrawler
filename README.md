> **免责声明：**

>本仓库的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。

# 仓库描述

**小红书爬虫**，**抖音爬虫**， **快手爬虫**， **B站爬虫**...。  
目前能抓取小红书、抖音、快手、B站的视频、图片、评论、点赞、转发等信息。

原理：利用[playwright](https://playwright.dev/)搭桥，保留登录成功后的上下文浏览器环境，通过执行JS表达式获取一些加密参数
通过使用此方式，免去了复现核心加密JS代码，逆向难度大大降低。
爬虫技术交流群：[949715256](http://qm.qq.com/cgi-bin/qm/qr?_wv=1027&k=NFz-oY7Pek3gpG5zbLJFHARlB8lKL94f&authKey=FlxIQK99Uu90wddNV5W%2FBga6T6lXU5BRqyTTc26f2P2ZK5OW%2BDhHp7MwviX%2BbrPa&noverify=0&group_code=949715256),同时欢迎大家贡献代码提交PR


## SPONSORED BY
目前爬虫正在用的IP代理：<a href="https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang">极速HTTP代理</a>  新用户注册认证最高送12000IP，0元试用<br>
<a href="https://www.jisuhttp.com/?pl=mAKphQ&plan=ZY&kd=Yang" target="_blank"><img src="https://s2.loli.net/2023/11/30/RapQtL8A2w6TGfj.png" alt="极速HTTP代理-官网图"></a>


## 功能列表
| 平台  | Cookie 登录 | 二维码登录 | 手机号登录 | 关键词搜索 | 指定视频/帖子 ID 爬取 | 登录状态缓存 | 数据保存 | IP 代理池 | 滑块验证码 |
|:---:|:---------:|:-----:|:-----:|:-----:|:-------------:|:------:|:----:|:------:|:-----:|
| 小红书 |     ✅     |   ✅   | ✅     |   ✅   |       ✅       |   ✅    |  ✅   |   ✅    |   ✕   |
| 抖音  |     ✅     |   ✅   | ✅     |   ✅   |       ✅       |   ✅    |  ✅   |   ✅    |   ✅   |
| 快手  |     ✅     |   ✅   | ✕     |   ✅   |       ✅       |   ✅    |  ✅   |   ✅    |    ✕   |
| B 站 |     ✅      |   ✅    | ✕     |   ✅    |       ✅        |    ✅    |   ✅   |    ✅    |   ✕   |
| 微博  |     ✕     |   ✕   | ✕     |   ✕   |       ✕       |   ✕    |  ✕   |   ✕    |   ✕   |


## 使用方法

1. 创建 python 虚拟环境
   ```shell
   python3 -m venv venv
   ```

2. 安装依赖库

   ```shell
   pip install -r requirements.txt
   ```

3. 安装playwright浏览器驱动

   ```shell
   playwright install
   ```

4. 是否保存数据到DB中

   如果选择开启，则需要配置数据库连接信息，`config/db_config.py` 中的 `IS_SAVED_DATABASED`和`RELATION_DB_URL` 变量。然后执行以下命令初始化数据库信息，生成相关的数据库表结构：

   ```shell
   python db.py
   ```

5. 运行爬虫程序

   ```shell
   # 从配置文件中读取关键词搜索相关的帖子并爬去帖子信息与评论
   python main.py --platform xhs --lt qrcode --type search
   
   # 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
   python main.py --platform xhs --lt qrcode --type detail
   
   # 其他平台爬虫使用示例, 执行下面的命令查看
    python3 main.py --help
    
   ```

6. 打开对应APP扫二维码登录

7. 等待爬虫程序执行完毕，数据会保存到 `data/xhs` 目录下

## 如何使用 IP 代理
➡️➡️➡️ [IP代理使用方法](docs/代理使用.md)

## 运行报错常见问题Q&A
➡️➡️➡️ [常见问题](docs/常见问题.md)

## 项目代码结构
➡️➡️➡️ [项目代码结构说明](docs/项目代码结构.md)

## 手机号登录说明
➡️➡️➡️ [手机号登录说明](docs/手机号登录说明.md)

## 打赏

如果觉得项目不错的话可以打赏哦。您的支持就是我最大的动力！

打赏时您可以备注名称，我会将您添加至打赏列表中。
<p>
  <img alt="打赏-微信" src="static/images/wechat_pay.jpeg" style="width: 200px;margin-right: 140px;" />
  <img alt="打赏-支付宝" src="static/images/zfb_pay.jpeg" style="width: 200px" />
</p>

## 捐赠信息

PS：如果打赏时请备注捐赠者，如有遗漏请联系我添加（有时候消息多可能会漏掉，十分抱歉）

| 捐赠者    | 捐赠金额   | 捐赠日期       |
|--------|--------|------------|
| 坠落     | 50 元   | 2023-11-08 |
| 一呆     | 20 元   | 2023-12-01 |

## star 趋势图
- 如果该项目对你有帮助，star一下 ❤️❤️❤️

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)




## 参考

- xhs客户端 [ReaJason的xhs仓库](https://github.com/ReaJason/xhs)
- 短信转发 [参考仓库](https://github.com/pppscn/SmsForwarder)
- 内网穿透工具 [ngrok](https://ngrok.com/docs/)

