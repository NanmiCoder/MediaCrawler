# -*- coding: utf-8 -*-
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import hashlib
import base64
import json
from typing import Any

def _build_c(e: Any, a: Any) -> str:
    c = str(e)
    if isinstance(a, (dict, list)):
        c += json.dumps(a, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(a, str):
        c += a
    # 其它类型不拼
    return c


# ---------------------------
# p.Pu = MD5(c) => hex 小写
# ---------------------------
def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()



# ============================================================
# Playwright 版本（异步）：传入 page（Page 对象）
#    内部用 page.evaluate('window.mnsv2(...)')
# ============================================================
async def seccore_signv2_playwright(
    page,  # Playwright Page
    e: Any,
    a: Any,
) -> str:
    """
    使用 Playwright 的 page.evaluate 调用 window.mnsv2(c, d) 来生成签名。
    需确保 page 上下文中已存在 window.mnsv2（比如已注入目标站点脚本）。

    用法：
      s = await page.evaluate("(c, d) => window.mnsv2(c, d)", c, d)
    """
    c = _build_c(e, a)
    d = _md5_hex(c)

    # 调用浏览器上下文里的 window.mnsv2
    s = await page.evaluate("(c, d) => window.mnsv2(c, d)", [c, d])
    f = {
        "x0": "4.2.6",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": s,
        "x4": a,
    }
    payload = json.dumps(f, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    token = "XYS_" + base64.b64encode(payload).decode("ascii")
    print(token)
    return token