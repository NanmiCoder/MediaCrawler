# Excel Export Guide

## Overview

MediaCrawler now supports exporting crawled data to formatted Excel files (.xlsx) with professional styling and multiple sheets for contents, comments, and creators.

## Features

- **Multi-sheet workbooks**: Separate sheets for Contents, Comments, and Creators
- **Professional formatting**: 
  - Styled headers with blue background and white text
  - Auto-adjusted column widths
  - Cell borders and text wrapping
  - Clean, readable layout
- **Smart export**: Empty sheets are automatically removed
- **Organized storage**: Files saved to `data/{platform}/` directory with timestamps

## Installation

Excel export requires the `openpyxl` library:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install openpyxl
```

## Usage

### Basic Usage

1. **Configure Excel export** in `config/base_config.py`:

```python
SAVE_DATA_OPTION = "excel"  # Change from json/csv/db to excel
```

2. **Run the crawler**:

```bash
# Xiaohongshu example
uv run main.py --platform xhs --lt qrcode --type search

# Douyin example
uv run main.py --platform dy --lt qrcode --type search

# Bilibili example
uv run main.py --platform bili --lt qrcode --type search
```

3. **Find your Excel file** in `data/{platform}/` directory:
   - Filename format: `{platform}_{crawler_type}_{timestamp}.xlsx`
   - Example: `xhs_search_20250128_143025.xlsx`

### Command Line Examples

```bash
# Search by keywords and export to Excel
uv run main.py --platform xhs --lt qrcode --type search --save_data_option excel

# Crawl specific posts and export to Excel
uv run main.py --platform xhs --lt qrcode --type detail --save_data_option excel

# Crawl creator profile and export to Excel
uv run main.py --platform xhs --lt qrcode --type creator --save_data_option excel
```

## Excel File Structure

### Contents Sheet
Contains post/video information:
- `note_id`: Unique post identifier
- `title`: Post title
- `desc`: Post description
- `user_id`: Author user ID
- `nickname`: Author nickname
- `liked_count`: Number of likes
- `comment_count`: Number of comments
- `share_count`: Number of shares
- `ip_location`: IP location
- `image_list`: Comma-separated image URLs
- `tag_list`: Comma-separated tags
- `note_url`: Direct link to post
- And more platform-specific fields...

### Comments Sheet
Contains comment information:
- `comment_id`: Unique comment identifier
- `note_id`: Associated post ID
- `content`: Comment text
- `user_id`: Commenter user ID
- `nickname`: Commenter nickname
- `like_count`: Comment likes
- `create_time`: Comment timestamp
- `ip_location`: Commenter location
- `sub_comment_count`: Number of replies
- And more...

### Creators Sheet
Contains creator/author information:
- `user_id`: Unique user identifier
- `nickname`: Display name
- `gender`: Gender
- `avatar`: Profile picture URL
- `desc`: Bio/description
- `fans`: Follower count
- `follows`: Following count
- `interaction`: Total interactions
- And more...

## Advantages Over Other Formats

### vs CSV
- ✅ Multiple sheets in one file
- ✅ Professional formatting
- ✅ Better handling of special characters
- ✅ Auto-adjusted column widths
- ✅ No encoding issues

### vs JSON
- ✅ Human-readable tabular format
- ✅ Easy to open in Excel/Google Sheets
- ✅ Better for data analysis
- ✅ Easier to share with non-technical users

### vs Database
- ✅ No database setup required
- ✅ Portable single-file format
- ✅ Easy to share and archive
- ✅ Works offline

## Tips & Best Practices

1. **Large datasets**: For very large crawls (>10,000 rows), consider using database storage instead for better performance

2. **Data analysis**: Excel files work great with:
   - Microsoft Excel
   - Google Sheets
   - LibreOffice Calc
   - Python pandas: `pd.read_excel('file.xlsx')`

3. **Combining data**: You can merge multiple Excel files using:
   ```python
   import pandas as pd
   df1 = pd.read_excel('file1.xlsx', sheet_name='Contents')
   df2 = pd.read_excel('file2.xlsx', sheet_name='Contents')
   combined = pd.concat([df1, df2])
   combined.to_excel('combined.xlsx', index=False)
   ```

4. **File size**: Excel files are typically 2-3x larger than CSV but smaller than JSON

## Troubleshooting

### "openpyxl not installed" error

```bash
# Install openpyxl
uv add openpyxl
# or
pip install openpyxl
```

### Excel file not created

Check that:
1. `SAVE_DATA_OPTION = "excel"` in config
2. Crawler successfully collected data
3. No errors in console output
4. `data/{platform}/` directory exists

### Empty Excel file

This happens when:
- No data was crawled (check keywords/IDs)
- Login failed (check login status)
- Platform blocked requests (check IP/rate limits)

## Example Output

After running a successful crawl, you'll see:

```
[ExcelStoreBase] Initialized Excel export to: data/xhs/xhs_search_20250128_143025.xlsx
[ExcelStoreBase] Stored content to Excel: 7123456789
[ExcelStoreBase] Stored comment to Excel: comment_123
...
[Main] Excel file saved successfully
```

Your Excel file will have:
- Professional blue headers
- Clean borders
- Wrapped text for long content
- Auto-sized columns
- Separate organized sheets

## Advanced Usage

### Programmatic Access

```python
from store.excel_store_base import ExcelStoreBase

# Create store
store = ExcelStoreBase(platform="xhs", crawler_type="search")

# Store data
await store.store_content({
    "note_id": "123",
    "title": "Test Post",
    "liked_count": 100
})

# Save to file
store.flush()
```

### Custom Formatting

You can extend `ExcelStoreBase` to customize formatting:

```python
from store.excel_store_base import ExcelStoreBase

class CustomExcelStore(ExcelStoreBase):
    def _apply_header_style(self, sheet, row_num=1):
        # Custom header styling
        super()._apply_header_style(sheet, row_num)
        # Add your customizations here
```

## Support

For issues or questions:
- Check [常见问题](常见问题.md)
- Open an issue on GitHub
- Join the WeChat discussion group

---

**Note**: Excel export is designed for learning and research purposes. Please respect platform terms of service and rate limits.
