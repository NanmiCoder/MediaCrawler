# Desc: base config
PLATFORM = "xhs"
KEYWORDS = "python,golang"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""  # login by cookie, if login_type is cookie, you must set this value
CRAWLER_TYPE = "search"

# enable ip proxy
ENABLE_IP_PROXY = False

# retry_interval
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True

# save login state
SAVE_LOGIN_STATE = True

# save user data dir
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# crawler max notes count
CRAWLER_MAX_NOTES_COUNT = 20

# max concurrency num
MAX_CONCURRENCY_NUM = 10


# xhs specified note id list
XHS_SPECIFIED_ID_LIST = [
"6422c2750000000027000d88",
"64ca1b73000000000b028dd2",
"630d5b85000000001203ab41",
]
