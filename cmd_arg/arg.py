import argparse
import config

async def parse_cmd():
    # 读取command arg
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks | bili | wb)',
                        choices=["xhs", "dy", "ks", "bili", "wb"])
    parser.add_argument('--lt', type=str, help='Login type (qrcode | phone | cookie)',
                        choices=["qrcode", "phone", "cookie"])
    parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                        choices=["search", "detail", "creator"])
    parser.add_argument('--start', type=int,
                        help='number of start page')
    parser.add_argument('--keywords', type=str,
                        help='please input keywords')

    args = parser.parse_args()

    # override config
    config.PLATFORM = args.platform
    config.LOGIN_TYPE = args.lt
    config.CRAWLER_TYPE = args.type
    config.START_PAGE = args.start
    config.KEYWORDS = args.keywords
