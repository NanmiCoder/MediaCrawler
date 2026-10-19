# Using ProxyLane China residential IPs with MediaCrawler

[ProxyLane](https://proxylane.dev/?utm_source=mediacrawler&utm_medium=partnership&utm_campaign=mediacrawler_sponsor_202610&utm_content=docs_en) provides residential IPs inside mainland China (China Telecom, Unicom, Mobile). You can pin the exit to Shanghai, Beijing, Guangzhou, Shenzhen or another city. This helps when you run MediaCrawler from a server or network outside China: the QR login and the crawl share one Chinese residential IP.

MediaCrawler has a built-in `static` proxy mode, so setup takes 3 steps and no code changes.

## 1. Get proxy credentials

MediaCrawler users get 3 GB of free traffic: sign up at ProxyLane with code `MEDIACRAWLER3GB` ([claim it here](https://proxylane.dev/redeem?code=MEDIACRAWLER3GB&utm_source=mediacrawler&utm_medium=partnership&utm_campaign=mediacrawler_sponsor_202610&utm_content=docs_en)). Then copy your proxy username and password from the dashboard.

## 2. Edit `config/base_config.py`

```python
ENABLE_IP_PROXY = True
IP_PROXY_PROVIDER_NAME = "static"
STATIC_PROXY_URL = "http://USER_c_CN_city_Shanghai_s_xhs01:PASS@asia.gw.proxylane.dev:10000"

# In CDP mode the browser skips the proxy, so the QR login uses your own IP
ENABLE_CDP_MODE = False
```

Replace `USER` and `PASS` with the credentials from the dashboard.

## 3. Run

```shell
uv run main.py --platform xhs --lt qrcode --type search
```

You can also pass the proxy on the command line instead (`ENABLE_CDP_MODE` still has to be turned off in the config file):

```shell
uv run main.py --platform xhs --lt qrcode --type search \
  --enable_ip_proxy yes --ip_proxy_provider_name static \
  --static_proxy_url "http://USER_c_CN_city_Shanghai_s_xhs01:PASS@asia.gw.proxylane.dev:10000"
```

## Username parameters

Location and session go after the username:

| Parameter | Example | What it does |
| --- | --- | --- |
| `_c_` | `_c_CN` | Country (ISO code), `CN` for China |
| `_city_` | `_city_Shanghai` | City, for example `Beijing`, `Guangzhou`, `Shenzhen` |
| `_s_` | `_s_xhs01` | Sticky session name (letters and digits); the same name keeps the same IP |
| `_ttl_` | `_ttl_3600s`, `_ttl_72h` | Session length, up to 72 hours |

Use a different session name for each logged-in account, for example `_s_xhs01` and `_s_dy01`. Without `_s_` the IP changes on every request, which suits public data without a login. ISP and ASN targeting can be generated in the dashboard.

## Check the exit IP

```shell
curl -x "http://USER_c_CN_city_Shanghai_s_test1:PASS@asia.gw.proxylane.dev:10000" "http://ip-api.com/json/"
```

`country` should be `China` and `city` should be `Shanghai`.

## Notes

- The `static` mode accepts `http://` and `https://` proxy URLs only, not SOCKS5.
- For China IPs we recommend `asia.gw.proxylane.dev`; `us.gw.proxylane.dev` and `eu.gw.proxylane.dev` also work.
- The first connection of a new session can take a few extra seconds.

Please follow each platform's rules and applicable laws, and use this for learning and research only.
