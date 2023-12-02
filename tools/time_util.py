# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 12:52
# @Desc    : 时间相关的工具函数

import time


def get_current_timestamp() -> int:
    """
    获取当前的时间戳(13 位)：1701493264496
    :return:
    """
    return int(time.time() * 1000)


def get_current_time() -> str:
    """
    获取当前的时间：'2023-12-02 13:01:23'
    :return:
    """
    return time.strftime('%Y-%m-%d %X', time.localtime())


def get_current_date() -> str:
    """
    获取当前的日期：'2023-12-02'
    :return:
    """
    return time.strftime('%Y-%m-%d', time.localtime())


def get_time_str_from_unix_time(unixtime):
    """
    unix 整数类型时间戳  ==> 字符串日期时间
    :param unixtime:
    :return:
    """
    if int(unixtime) > 1000000000000:
        unixtime = int(unixtime) / 1000
    return time.strftime('%Y-%m-%d %X', time.localtime(unixtime))


def get_date_str_from_unix_time(unixtime):
    """
    unix 整数类型时间戳  ==> 字符串日期
    :param unixtime:
    :return:
    """
    if int(unixtime) > 1000000000000:
        unixtime = int(unixtime) / 1000
    return time.strftime('%Y-%m-%d', time.localtime(unixtime))


def get_unix_time_from_time_str(time_str):
    """
    字符串时间 ==> unix 整数类型时间戳，精确到秒
    :param time_str:
    :return:
    """
    try:
        format_str = "%Y-%m-%d %H:%M:%S"
        tm_object = time.strptime(str(time_str), format_str)
        return int(time.mktime(tm_object))
    except Exception as e:
        return 0
    pass


def get_unix_timestamp():
    return int(time.time())