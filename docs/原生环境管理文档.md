## 使用python原生venv管理依赖（不推荐了）

## 创建并激活 python 虚拟环境
> 如果是爬取抖音和知乎，需要提前安装nodejs环境，版本大于等于：`16`即可 <br>
> 新增 [uv](https://github.com/astral-sh/uv) 来管理项目依赖，使用uv来替代python版本管理、pip进行依赖安装，更加方便快捷
   ```shell   
   # 进入项目根目录
   cd MediaCrawler
   
   # 创建虚拟环境
   # 我的python版本是：3.9.6，requirements.txt中的库是基于这个版本的，如果是其他python版本，可能requirements.txt中的库不兼容，自行解决一下。
   python -m venv venv
   
   # macos & linux 激活虚拟环境
   source venv/bin/activate

   # windows 激活虚拟环境
   venv\Scripts\activate

   ```

## 安装依赖库

   ```shell
   pip install -r requirements.txt
   ```

## 查看配置文件

## 安装 playwright浏览器驱动 (非必需)

   ```shell
   playwright install
   ```

## 运行爬虫程序

   ```shell
   ### 项目默认是没有开启评论爬取模式，如需评论请在config/base_config.py中的 ENABLE_GET_COMMENTS 变量修改
   ### 一些其他支持项，也可以在config/base_config.py查看功能，写的有中文注释
   
   # 从配置文件中读取关键词搜索相关的帖子并爬取帖子信息与评论
   python main.py --platform xhs --lt qrcode --type search
   
   # 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
   python main.py --platform xhs --lt qrcode --type detail
  
   # 打开对应APP扫二维码登录
     
   # 其他平台爬虫使用示例，执行下面的命令查看
   python main.py --help    
   ```