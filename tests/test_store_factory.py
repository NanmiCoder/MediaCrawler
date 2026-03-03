# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tests/test_store_factory.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
Unit tests for Store Factory functionality
"""

import pytest
from unittest.mock import patch, MagicMock

from store.xhs import XhsStoreFactory
from store.xhs._store_impl import (
    XhsCsvStoreImplement,
    XhsJsonStoreImplement,
    XhsJsonlStoreImplement,
    XhsDbStoreImplement,
    XhsSqliteStoreImplement,
    XhsMongoStoreImplement,
    XhsExcelStoreImplement
)


class TestXhsStoreFactory:
    """Test cases for XhsStoreFactory"""

    @patch('config.SAVE_DATA_OPTION', 'csv')
    def test_create_csv_store(self):
        """Test creating CSV store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsCsvStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'json')
    def test_create_json_store(self):
        """Test creating JSON store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsJsonStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'db')
    def test_create_db_store(self):
        """Test creating database store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsDbStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'sqlite')
    def test_create_sqlite_store(self):
        """Test creating SQLite store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsSqliteStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'mongodb')
    def test_create_mongodb_store(self):
        """Test creating MongoDB store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsMongoStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'excel')
    def test_create_excel_store(self):
        """Test creating Excel store"""
        # ContextVar cannot be mocked, so we test with actual value
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsExcelStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'jsonl')
    def test_create_jsonl_store(self):
        """Test creating JSONL store"""
        store = XhsStoreFactory.create_store()
        assert isinstance(store, XhsJsonlStoreImplement)

    @patch('config.SAVE_DATA_OPTION', 'invalid')
    def test_invalid_store_option(self):
        """Test that invalid store option raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            XhsStoreFactory.create_store()

        assert "Invalid save option" in str(exc_info.value)

    def test_all_stores_registered(self):
        """Test that all store types are registered"""
        expected_stores = ['csv', 'json', 'jsonl', 'db', 'postgres', 'sqlite', 'mongodb', 'excel']

        for store_type in expected_stores:
            assert store_type in XhsStoreFactory.STORES

        assert len(XhsStoreFactory.STORES) == len(expected_stores)
