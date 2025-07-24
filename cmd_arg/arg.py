# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import argparse

import config
from tools.utils import str2bool


async def parse_cmd():
    # 读取command arg
    parser = argparse.ArgumentParser(description='Media crawler program. / 媒体爬虫程序')
    parser.add_argument('--platform', type=str, 
                        help='Media platform select / 选择媒体平台 (xhs=小红书 | dy=抖音 | ks=快手 | bili=哔哩哔哩 | wb=微博 | tieba=百度贴吧 | zhihu=知乎)',
                        choices=["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, 
                        help='Login type / 登录方式 (qrcode=二维码 | phone=手机号 | cookie=Cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, 
                        help='Crawler type / 爬取类型 (search=搜索 | detail=详情 | creator=创作者)',
                        choices=["search", "detail", "creator"], default=config.CRAWLER_TYPE)
    parser.add_argument('--start', type=int,
                        help='Number of start page / 起始页码', default=config.START_PAGE)
    parser.add_argument('--keywords', type=str,
                        help='Please input keywords / 请输入关键词', default=config.KEYWORDS)
    parser.add_argument('--get_comment', type=str2bool,
                        help='''Whether to crawl level one comment / 是否爬取一级评论, supported values case insensitive / 支持的值(不区分大小写) ('yes', 'true', 't', 'y', '1', 'no', 'false', 'f', 'n', '0')''', default=config.ENABLE_GET_COMMENTS)
    parser.add_argument('--get_sub_comment', type=str2bool,
                        help=''''Whether to crawl level two comment / 是否爬取二级评论, supported values case insensitive / 支持的值(不区分大小写) ('yes', 'true', 't', 'y', '1', 'no', 'false', 'f', 'n', '0')''', default=config.ENABLE_GET_SUB_COMMENTS)
    parser.add_argument('--save_data_option', type=str,
                        help='Where to save the data / 数据保存方式 (csv=CSV文件 | db=MySQL数据库 | json=JSON文件 | sqlite=SQLite数据库)', 
                        choices=['csv', 'db', 'json', 'sqlite'], default=config.SAVE_DATA_OPTION)
    parser.add_argument('--cookies', type=str,
                        help='Cookies used for cookie login type / Cookie登录方式使用的Cookie值', default=config.COOKIES)

    args = parser.parse_args()

    # override config
    config.PLATFORM = args.platform
    config.LOGIN_TYPE = args.lt
    config.CRAWLER_TYPE = args.type
    config.START_PAGE = args.start
    config.KEYWORDS = args.keywords
    config.ENABLE_GET_COMMENTS = args.get_comment
    config.ENABLE_GET_SUB_COMMENTS = args.get_sub_comment
    config.SAVE_DATA_OPTION = args.save_data_option
    config.COOKIES = args.cookies
