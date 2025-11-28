# -*- coding: utf-8 -*-
"""
Unit tests for Store Factory functionality
"""

import pytest
from unittest.mock import patch, MagicMock

from store.xhs import XhsStoreFactory
from store.xhs._store_impl import (
    XhsCsvStoreImplement,
    XhsJsonStoreImplement,
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
    
    @patch('config.SAVE_DATA_OPTION', 'invalid')
    def test_invalid_store_option(self):
        """Test that invalid store option raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            XhsStoreFactory.create_store()
        
        assert "Invalid save option" in str(exc_info.value)
    
    def test_all_stores_registered(self):
        """Test that all store types are registered"""
        expected_stores = ['csv', 'json', 'db', 'sqlite', 'mongodb', 'excel']
        
        for store_type in expected_stores:
            assert store_type in XhsStoreFactory.STORES
        
        assert len(XhsStoreFactory.STORES) == len(expected_stores)
