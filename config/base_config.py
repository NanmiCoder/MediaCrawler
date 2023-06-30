PLATFORM = "xhs"
KEYWORDS = "健身,旅游"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookies
LOGIN_TYPE_COOKIE = "cookies"  # qrcode or phone or cookies
# If it's on the Xiaohongshu platform, only the web_session cookie will be kept.
# xhs cookie format -> web_session=040069b2acxxxxxxxxxxxxxxxxxxxx;
COOKIES = "web_session=030037a350f6d4575edfece41b234aa0adaf12;"

# redis config
REDIS_DB_HOST = "redis://127.0.0.1"  # your redis host
REDIS_DB_PWD = "123456"  # your redis password

# enable ip proxy
ENABLE_IP_PROXY = False

# retry_interval
RETRY_INTERVAL = 60 * 30  # 30 minutes

# playwright headless
HEADLESS = True
