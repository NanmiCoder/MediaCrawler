# -*- coding: utf-8 -*-

from tools import utils


def test_convert_cookies():
    xhs_cookies = "a1=x000101360; webId=1190c4d3cxxxx125xxx; "
    cookie_dict = utils.convert_str_cookie_to_dict(xhs_cookies)
    assert cookie_dict.get("webId") == "1190c4d3cxxxx125xxx"
    assert cookie_dict.get("a1") == "x000101360"
