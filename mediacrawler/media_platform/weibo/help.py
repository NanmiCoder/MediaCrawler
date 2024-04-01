# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/24 17:37
# @Desc    :

from typing import Dict, List


def filter_search_result_card(card_list: List[Dict]) -> List[Dict]:
    """
    过滤微博搜索的结果，只保留card_type为9类型的数据
    :param card_list:
    :return:
    """
    note_list: List[Dict] = []
    for card_item in card_list:
        if card_item.get("card_type") == 9:
            note_list.append(card_item)
        if len(card_item.get("card_group", [])) > 0:
            card_group = card_item.get("card_group")
            for card_group_item in card_group:
                if card_group_item.get("card_type") == 9:
                    note_list.append(card_group_item)

    return note_list
