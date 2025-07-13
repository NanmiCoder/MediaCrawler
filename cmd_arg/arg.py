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
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks | bili | wb | tieba | zhihu)',
                        choices=["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"], default=config.PLATFORM)
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"], default=config.LOGIN_TYPE)
    parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                        choices=["search", "detail", "creator"], default=config.CRAWLER_TYPE)
    parser.add_argument('--start', type=int,
                        help='number of start page', default=config.START_PAGE)
    parser.add_argument('--keywords', type=str,
                        help='please input keywords', default=config.KEYWORDS)
    parser.add_argument('--get_comment', type=str2bool,
                        help='''whether to crawl level one comment, supported values case insensitive ('yes', 'true', 't', 'y', '1', 'no', 'false', 'f', 'n', '0')''', default=config.ENABLE_GET_COMMENTS)
    parser.add_argument('--get_sub_comment', type=str2bool,
                        help=''''whether to crawl level two comment, supported values case insensitive ('yes', 'true', 't', 'y', '1', 'no', 'false', 'f', 'n', '0')''', default=config.ENABLE_GET_SUB_COMMENTS)
    parser.add_argument('--save_data_option', type=str,
                        help='where to save the data (csv or db or json)', choices=['csv', 'db', 'json'], default=config.SAVE_DATA_OPTION)
    parser.add_argument('--cookies', type=str,
                        help='cookies used for cookie login type', default=config.COOKIES)
    parser.add_argument('--creator_urls', type=str, nargs='*',
                        help='creator urls or sec_user_ids for dy platform creator crawling (support multiple URLs separated by space)')
    parser.add_argument('--video_urls', type=str, nargs='*',
                        help='video urls or video_ids for dy platform detail crawling (support multiple URLs separated by space)')
    parser.add_argument('--xhs_note_urls', type=str, nargs='*',
                        help='note urls or note_ids for xhs platform detail crawling (support multiple URLs separated by space)')
    parser.add_argument('--xhs_creator_urls', type=str, nargs='*',
                        help='creator urls or creator_ids for xhs platform creator crawling (support multiple URLs separated by space)')
    parser.add_argument('--ks_video_urls', type=str, nargs='*',
                        help='video urls or video_ids for ks platform detail crawling (support multiple URLs separated by space)')
    parser.add_argument('--ks_creator_urls', type=str, nargs='*',
                        help='creator urls or creator_ids for ks platform creator crawling (support multiple URLs separated by space)')

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
    
    # 处理创作者URL参数（仅对抖音平台的creator类型有效）
    if args.creator_urls and config.PLATFORM == "dy" and config.CRAWLER_TYPE == "creator":
        config.DY_CREATOR_URL_LIST = args.creator_urls
        print(f"[CMD] 已设置抖音创作者URL列表: {args.creator_urls}")
        
    # 处理视频URL参数（仅对抖音平台的detail类型有效）
    if args.video_urls and config.PLATFORM == "dy" and config.CRAWLER_TYPE == "detail":
        config.DY_SPECIFIED_ID_LIST = args.video_urls
        print(f"[CMD] 已设置抖音视频URL列表: {args.video_urls}")
        
    # 处理小红书笔记URL参数（仅对小红书平台的detail类型有效）
    if args.xhs_note_urls and config.PLATFORM == "xhs" and config.CRAWLER_TYPE == "detail":
        config.XHS_SPECIFIED_NOTE_URL_LIST = args.xhs_note_urls
        print(f"[CMD] 已设置小红书笔记URL列表: {args.xhs_note_urls}")
        
    # 处理小红书创作者URL参数（仅对小红书平台的creator类型有效）
    if args.xhs_creator_urls and config.PLATFORM == "xhs" and config.CRAWLER_TYPE == "creator":
        config.XHS_CREATOR_ID_LIST = args.xhs_creator_urls
        print(f"[CMD] 已设置小红书创作者URL列表: {args.xhs_creator_urls}")
        
    # 处理快手视频URL参数（仅对快手平台的detail类型有效）
    if args.ks_video_urls and config.PLATFORM == "ks" and config.CRAWLER_TYPE == "detail":
        config.KS_SPECIFIED_ID_LIST = args.ks_video_urls
        print(f"[CMD] 已设置快手视频URL列表: {args.ks_video_urls}")
        
    # 处理快手创作者URL参数（仅对快手平台的creator类型有效）
    if args.ks_creator_urls and config.PLATFORM == "ks" and config.CRAWLER_TYPE == "creator":
        config.KS_CREATOR_ID_LIST = args.ks_creator_urls
        print(f"[CMD] 已设置快手创作者URL列表: {args.ks_creator_urls}")
