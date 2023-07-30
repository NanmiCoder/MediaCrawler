# -*- coding: utf-8 -*-
# account_config.py
import os

PHONE_LIST = [
    "13012345671",
    "13012345672",
    "13012345673",
    "13012345674",
    "13012345675",
    "13012345676",
    # ...
]

IP_PROXY_LIST = [
    "111.122.xx.xx1:8888",
    "111.122.xx.xx2:8888",
    "111.122.xx.xx3:8888",
    "111.122.xx.xx4:8888",
    "111.122.xx.xx5:8888",
    "111.122.xx.xx6:8888",
    # ...
]

IP_PROXY_PROTOCOL = "http://"
IP_PROXY_USER = os.getenv("IP_PROXY_USER", "test")
IP_PROXY_PASSWORD = os.getenv("IP_PROXY_PASSWORD", "123456")
