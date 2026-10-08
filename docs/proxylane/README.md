# ProxyLane 中国住宅 IP 接入指南

[ProxyLane](https://proxylane.dev/?utm_source=mediacrawler&utm_medium=partnership&utm_campaign=mediacrawler_sponsor_202610&utm_content=docs_zh) 提供中国住宅 IP（电信、联通、移动），出口可固定到上海、北京、广州、深圳等城市。适合在海外服务器或海外网络运行 MediaCrawler：扫码登录和后续抓取走同一个中国住宅 IP。

MediaCrawler 自带 `static` 代理模式，接入只需 3 步，不用改代码。

## 1. 获取代理账号

MediaCrawler 用户使用优惠码 `MEDIACRAWLER3GB` 在 ProxyLane 注册，即可免费领取 3GB 流量（[一键领取](https://proxylane.dev/redeem?code=MEDIACRAWLER3GB&utm_source=mediacrawler&utm_medium=partnership&utm_campaign=mediacrawler_sponsor_202610&utm_content=docs_zh)）。注册后在控制台复制代理用户名和密码。

## 2. 修改 `config/base_config.py`

```python
ENABLE_IP_PROXY = True
IP_PROXY_PROVIDER_NAME = "static"
STATIC_PROXY_URL = "http://USER_c_CN_city_Shanghai_s_xhs01:PASS@asia.gw.proxylane.dev:10000"

# CDP 模式下浏览器不走代理，扫码登录会使用本机 IP
ENABLE_CDP_MODE = False
```

把 `USER` 和 `PASS` 换成控制台里的用户名和密码。

## 3. 运行

```shell
uv run main.py --platform xhs --lt qrcode --type search
```

也可以不改配置文件，直接用命令行参数（`ENABLE_CDP_MODE` 仍需在配置文件中关闭）：

```shell
uv run main.py --platform xhs --lt qrcode --type search \
  --enable_ip_proxy yes --ip_proxy_provider_name static \
  --static_proxy_url "http://USER_c_CN_city_Shanghai_s_xhs01:PASS@asia.gw.proxylane.dev:10000"
```

## 用户名参数

地区和会话写在用户名后面：

| 参数 | 示例 | 作用 |
| --- | --- | --- |
| `_c_` | `_c_CN` | 国家（ISO 代码），中国为 `CN` |
| `_city_` | `_city_Shanghai` | 城市，例如 `Beijing`、`Guangzhou`、`Shenzhen` |
| `_s_` | `_s_xhs01` | 粘性会话名（字母和数字），同一个会话保持同一个 IP |
| `_ttl_` | `_ttl_3600s`、`_ttl_72h` | 会话时长，最长 72 小时 |

建议每个登录账号使用不同的会话名，例如 `_s_xhs01`、`_s_dy01`。不写 `_s_` 时每次请求都会更换 IP，适合不登录的公开数据抓取。ISP 和 ASN 定向可以在控制台生成。

## 检查出口 IP

```shell
curl -x "http://USER_c_CN_city_Shanghai_s_test1:PASS@asia.gw.proxylane.dev:10000" "http://ip-api.com/json/?lang=zh-CN"
```

返回的 `country` 应为“中国”，`city` 为“上海”。

## 说明

- `static` 模式只支持 `http://` 和 `https://` 代理地址，不支持 SOCKS5。
- 中国 IP 推荐使用 `asia.gw.proxylane.dev`，也可以使用 `us.gw.proxylane.dev` 和 `eu.gw.proxylane.dev`。
- 新会话的第一次连接可能需要多等几秒。

请遵守各平台规则和相关法律法规，仅以学习和研究为目的使用。
