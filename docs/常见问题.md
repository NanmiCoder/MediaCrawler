# 常见程序运行出错问题

## 缺少node环境导致的问题
Q: 爬取抖音和知乎报错: `execjs._exceptions.ProgramError: SyntaxError: 缺少 ';'` <br>
A: 该错误为缺少 nodejs 环境，这个错误可以通过安装 nodejs 环境来解决，版本大于等：`v16` <br>

Q: 使用Cookie爬取抖音报错: execjs._exceptions.ProgramError: TypeError: Cannot read property 'JS_MD5_NO_COMMON_JS' of null
A: windows电脑去网站下载`https://nodejs.org/en/blog/release/v16.8.0` Windows 64-bit Installer 版本，一直下一步即可。

## xhs登录出现滑块一直验证不通过问题

Q: 小红书扫码登录成功后，浏览器一直在验证滑块，无法登录？<br>
A: 这种情况一般是因为使用playwright浏览器驱动被识别出来的问题，可以尝试删除项目目录下的`brower_data`文件夹，重新走登录流程。<br>

## 如何指定关键词
Q: 可以指定关键词爬取吗？<br>
A: 在config/base_config.py 中 KEYWORDS 参数用于控制需要爬取的关键词 <br>

## 如何指定帖子
Q: 可以指定帖子爬取吗？<br>
A：在config/base_config.py 中 XHS_SPECIFIED_ID_LIST 参数用于控制需要指定爬取的帖子ID列表 <br>

## 爬取失效
Q: 刚开始能爬取数据，过一段时间就是失效了？<br>
A：出现这种情况多半是由于你的账号触发了平台风控机制了，❗️❗️请勿大规模对平台进行爬虫，影响平台。<br>

## 如何更换另一个账号
Q: 如何更换登录账号？<br>
A：删除项目根目录下的 brower_data/ 文件夹即可 <br>

## playwright超时问题
Q: 报错 `playwright._impl._api_types.TimeoutError: Timeout 30000ms exceeded.`<br>
A: 出现这种情况检查下开梯子没有<br>

## 如果配置playwright浏览器驱动过滑块验证
Q: 小红书扫码登录成功后如何手动验证?
A: 打开 config/base_config.py 文件, 找到 HEADLESS 配置项, 将其设置为 False, 此时重启项目, 在浏览器中手动通过验证码<br>

## 词云图生成
Q: 如何配置词云图的生成?
A: 打开 config/base_config.py 文件, 找到`ENABLE_GET_WORDCLOUD` 以及`ENABLE_GET_COMMENTS` 两个配置项，将其都设为True即可使用该功能。<br>

## 词云图添加禁用词和自定义词组
Q: 如何给词云图添加禁用词和自定义词组？
A: 打开 `docs/hit_stopwords.txt` 输入禁用词(注意一个词语一行)。打开 config/base_config.py 文件找到 `CUSTOM_WORDS `按格式添加自定义词组即可。<br>
