# -*- coding: utf-8 -*-
"""
Unit tests for Excel export functionality
"""

import pytest
import asyncio
import os
from pathlib import Path
import tempfile
import shutil

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from store.excel_store_base import ExcelStoreBase


@pytest.mark.skipif(not EXCEL_AVAILABLE, reason="openpyxl not installed")
class TestExcelStoreBase:
    """Test cases for ExcelStoreBase"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # Cleanup
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def excel_store(self, temp_dir, monkeypatch):
        """Create ExcelStoreBase instance for testing"""
        # Monkey patch data directory
        monkeypatch.chdir(temp_dir)
        store = ExcelStoreBase(platform="test", crawler_type="search")
        yield store
        # Cleanup is handled by temp_dir fixture
    
    def test_initialization(self, excel_store):
        """Test Excel store initialization"""
        assert excel_store.platform == "test"
        assert excel_store.crawler_type == "search"
        assert excel_store.workbook is not None
        assert excel_store.contents_sheet is not None
        assert excel_store.comments_sheet is not None
        assert excel_store.creators_sheet is not None
    
    @pytest.mark.asyncio
    async def test_store_content(self, excel_store):
        """Test storing content data"""
        content_item = {
            "note_id": "test123",
            "title": "Test Title",
            "desc": "Test Description",
            "user_id": "user456",
            "nickname": "TestUser",
            "liked_count": 100,
            "comment_count": 50
        }
        
        await excel_store.store_content(content_item)
        
        # Verify data was written
        assert excel_store.contents_sheet.max_row == 2  # Header + 1 data row
        assert excel_store.contents_headers_written is True
    
    @pytest.mark.asyncio
    async def test_store_comment(self, excel_store):
        """Test storing comment data"""
        comment_item = {
            "comment_id": "comment123",
            "note_id": "note456",
            "content": "Great post!",
            "user_id": "user789",
            "nickname": "Commenter",
            "like_count": 10
        }
        
        await excel_store.store_comment(comment_item)
        
        # Verify data was written
        assert excel_store.comments_sheet.max_row == 2  # Header + 1 data row
        assert excel_store.comments_headers_written is True
    
    @pytest.mark.asyncio
    async def test_store_creator(self, excel_store):
        """Test storing creator data"""
        creator_item = {
            "user_id": "creator123",
            "nickname": "Creator Name",
            "fans": 10000,
            "follows": 500,
            "interaction": 50000
        }
        
        await excel_store.store_creator(creator_item)
        
        # Verify data was written
        assert excel_store.creators_sheet.max_row == 2  # Header + 1 data row
        assert excel_store.creators_headers_written is True
    
    @pytest.mark.asyncio
    async def test_multiple_items(self, excel_store):
        """Test storing multiple items"""
        # Store multiple content items
        for i in range(5):
            await excel_store.store_content({
                "note_id": f"note{i}",
                "title": f"Title {i}",
                "liked_count": i * 10
            })
        
        # Verify all items were stored
        assert excel_store.contents_sheet.max_row == 6  # Header + 5 data rows
    
    def test_flush(self, excel_store):
        """Test flushing data to file"""
        # Add some test data
        asyncio.run(excel_store.store_content({
            "note_id": "test",
            "title": "Test"
        }))
        
        # Flush to file
        excel_store.flush()
        
        # Verify file was created
        assert excel_store.filename.exists()
        
        # Verify file can be opened
        wb = openpyxl.load_workbook(excel_store.filename)
        assert "Contents" in wb.sheetnames
        wb.close()
    
    def test_header_formatting(self, excel_store):
        """Test header row formatting"""
        asyncio.run(excel_store.store_content({"note_id": "test", "title": "Test"}))
        
        # Check header formatting
        header_cell = excel_store.contents_sheet.cell(row=1, column=1)
        assert header_cell.font.bold is True
        assert header_cell.fill.start_color.rgb == "FF366092"
    
    def test_empty_sheets_removed(self, excel_store):
        """Test that empty sheets are removed on flush"""
        # Only add content, leave comments and creators empty
        asyncio.run(excel_store.store_content({"note_id": "test"}))
        
        excel_store.flush()
        
        # Reload workbook
        wb = openpyxl.load_workbook(excel_store.filename)
        
        # Only Contents sheet should exist
        assert "Contents" in wb.sheetnames
        assert "Comments" not in wb.sheetnames
        assert "Creators" not in wb.sheetnames
        wb.close()


@pytest.mark.skipif(not EXCEL_AVAILABLE, reason="openpyxl not installed")
def test_excel_import_availability():
    """Test that openpyxl is available"""
    assert EXCEL_AVAILABLE is True
    import openpyxl
    assert openpyxl is not None
