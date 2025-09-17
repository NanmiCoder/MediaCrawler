# XiaoHongShu (小红书) Data Structure Documentation

Detailed documentation of data structures that MediaCrawler can extract from XiaoHongShu

## 1. Note Data Structure (笔记数据结构)

### Storage Location Options

#### Traditional Storage (传统存储)
- Database: MySQL/SQLite tables or CSV/JSON files
- Media files: Separate storage for images and videos

#### New: Note Folder Storage (新增：笔记文件夹存储)
⚠️ **Available when using `SAVE_DATA_OPTION = "note_folder"`**
- Folder: `data/xhs/{publish_date_publish_time_note_id}/`
- File: `note_info.json`
- Similar to Bilibili's `video_folder` structure

### Data Fields

```json
{
  "note_id": "66fad51c000000001b0224b8",        // Note ID (笔记ID)
  "type": "normal",                            // Note type: "normal" or "video"
  "title": "分享一个超好用的编程技巧",              // Note title (笔记标题)
  "desc": "今天发现了一个很实用的Python技巧...", // Note description (笔记描述)
  "video_url": "http://sns-video-bd.xhscdn.com/video123", // Video URL (视频链接)
  "time": 1640995200,                          // Publish timestamp (发布时间戳)
  "last_update_time": 1640995300,              // Last update timestamp (最后更新时间)
  "user_id": "63e36c9a000000002703502b",       // Creator user ID (创作者ID)
  "nickname": "程序媛小美",                     // Creator nickname (创作者昵称)
  "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/...", // Creator avatar (创作者头像)
  "liked_count": 1234,                         // Like count (点赞数)
  "collected_count": 567,                      // Collection count (收藏数)
  "comment_count": 89,                         // Comment count (评论数)
  "share_count": 45,                           // Share count (分享数)
  "ip_location": "北京",                        // IP location (IP位置)
  "image_list": "https://sns-webpic-qc.xhscdn.com/202408/img1.jpg,https://sns-webpic-qc.xhscdn.com/202408/img2.jpg", // Image URLs (图片链接列表)
  "tag_list": "编程,Python,技术分享",            // Tags (标签列表)
  "last_modify_ts": 1692607200,                // Last modified timestamp (最后修改时间戳)
  "note_url": "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search", // Note URL (笔记链接)
  "source_keyword": "编程技巧,Python",          // Search keywords (搜索关键词)
  "xsec_token": "AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=" // Security token (安全令牌)
}
```

## 2. Comments Data Structure (评论数据结构)

### Data Fields

```json
{
  "comment_id": "64a1b2c3d4e5f6789012345",     // Comment ID (评论ID)
  "create_time": 1640995300,                   // Comment timestamp (评论时间戳)
  "ip_location": "上海",                        // IP location (IP位置)
  "note_id": "66fad51c000000001b0224b8",       // Associated note ID (关联笔记ID)
  "content": "这个技巧真的很实用，感谢分享！",     // Comment content (评论内容)
  "user_id": "789012345abcdef",                // Commenter user ID (评论者ID)
  "nickname": "技术爱好者小王",                  // Commenter nickname (评论者昵称)
  "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/...", // Commenter avatar (评论者头像)
  "sub_comment_count": 3,                      // Sub-comment count (子评论数)
  "pictures": "https://sns-webpic-qc.xhscdn.com/comment_pic1.jpg,https://sns-webpic-qc.xhscdn.com/comment_pic2.jpg", // Comment images (评论图片)
  "parent_comment_id": "0",                    // Parent comment ID, 0 means top-level (父评论ID，0表示顶级评论)
  "last_modify_ts": 1692607200,                // Last modified timestamp (最后修改时间戳)
  "like_count": 15                             // Comment like count (评论点赞数)
}
```

## 3. Creator Data Structure (创作者数据结构)

### Availability
⚠️ **Available when using `CRAWLER_TYPE = "creator"` mode**

### Data Fields

```json
{
  "user_id": "63e36c9a000000002703502b",       // Creator user ID (创作者ID)
  "nickname": "程序媛小美",                     // Nickname (昵称)
  "gender": "女",                              // Gender: "男"/"女"/null (性别)
  "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/...", // Avatar URL (头像链接)
  "desc": "分享编程技巧和职场经验的程序媛",        // Personal description (个人描述)
  "ip_location": "北京",                        // IP location (IP位置)
  "follows": 1250,                             // Following count (关注数)
  "fans": 8900,                               // Followers count (粉丝数)
  "interaction": 25000,                        // Total interactions (总互动数)
  "tag_list": "{\"职业标签\": \"程序员\", \"兴趣标签\": \"技术分享\"}", // Tags in JSON format (标签JSON格式)
  "last_modify_ts": 1692607200                 // Last modified timestamp (最后修改时间戳)
}
```

## 4. Media Files Data Structure (媒体文件数据结构)

### Image Files (图片文件)
```json
{
  "notice_id": "66fad51c000000001b0224b8",     // Associated note ID (关联笔记ID)
  "pic_content": "<binary_data>",              // Image binary content (图片二进制内容)
  "extension_file_name": "image_001.jpg"       // File name with extension (文件名)
}
```

### Video Files (视频文件)
```json
{
  "notice_id": "66fad51c000000001b0224b8",     // Associated note ID (关联笔记ID)
  "video_content": "<binary_data>",            // Video binary content (视频二进制内容)
  "extension_file_name": "video_001.mp4"       // File name with extension (文件名)
}
```

## 5. Storage Structure Comparison (存储结构对比)

### XiaoHongShu vs Bilibili
| Feature | XiaoHongShu | Bilibili |
|---------|-------------|----------|
| Folder Structure | ✅ Yes (`note_folder` option) | ✅ Yes (`video_folder` option) |
| Database Storage | ✅ Yes | ✅ Yes |
| CSV/JSON Storage | ✅ Yes | ✅ Yes |
| Media Download | ✅ Yes | ✅ Yes |
| Comments | ✅ Yes | ✅ Yes |
| Creator Info | ✅ Yes | ✅ Yes |

### Storage Options Available
- `SAVE_DATA_OPTION = "note_folder"` - **NEW**: Note folder storage (similar to Bilibili's video_folder)
- `SAVE_DATA_OPTION = "db"` - MySQL database storage
- `SAVE_DATA_OPTION = "sqlite"` - SQLite database storage
- `SAVE_DATA_OPTION = "csv"` - CSV files storage
- `SAVE_DATA_OPTION = "json"` - JSON files storage

### Note Folder Structure Example (笔记文件夹结构示例)

When using `SAVE_DATA_OPTION = "note_folder"`:

```
data/xhs/
├── 20240101_123000_66fad51c000000001b0224b8/    # Note publish_date_time_note_id
│   ├── note_info.json                          # Note basic information
│   ├── comments.json                           # Comments information
│   ├── images/                                 # Images folder
│   │   ├── image_001.jpg                       # Image files
│   │   ├── image_002.jpg
│   │   └── ...
│   └── videos/                                 # Videos folder
│       ├── video_001.mp4                       # Video files
│       └── ...
└── 20240102_150000_987654321abcdef012/
    ├── note_info.json
    ├── comments.json
    ├── images/
    └── videos/
```

## 6. Configuration Options (配置选项)

### Crawler Types
```python
CRAWLER_TYPE = "search"    # Search by keywords (关键词搜索)
CRAWLER_TYPE = "detail"    # Specific note details (指定笔记详情)
CRAWLER_TYPE = "creator"   # Creator profile data (创作者资料)
```

### XiaoHongShu Specific Settings
```python
PLATFORM = "xhs"                              # Set platform to XiaoHongShu
SORT_TYPE = "popularity_descending"            # Sort order for search results
XHS_SPECIFIED_NOTE_URL_LIST = [...]           # Specific note URLs (must include xsec_token)
XHS_CREATOR_ID_LIST = [...]                   # Creator IDs to crawl
```

### Data Collection Control
```python
ENABLE_GET_MEIDAS = True                       # Enable media download
ENABLE_GET_COMMENTS = True                     # Enable comment crawling
CRAWLER_MAX_NOTES_COUNT = 200                  # Max notes count
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10    # Max comments per note
```

## 6. Configuration Options (配置选项)

### Crawler Types
```python
CRAWLER_TYPE = "search"    # Search by keywords (关键词搜索)
CRAWLER_TYPE = "detail"    # Specific note details (指定笔记详情)
CRAWLER_TYPE = "creator"   # Creator profile data (创作者资料)
```

### Storage Options
- `SAVE_DATA_OPTION = "note_folder"` - **NEW**: Enable note folder storage mode (similar to Bilibili's video_folder)
- `SAVE_DATA_OPTION = "db"` - Database storage (for all data types)
- `SAVE_DATA_OPTION = "csv"` - CSV files storage
- `SAVE_DATA_OPTION = "json"` - JSON files storage
- `SAVE_DATA_OPTION = "sqlite"` - SQLite database storage

### XiaoHongShu Specific Settings
```python
PLATFORM = "xhs"                              # Set platform to XiaoHongShu
SORT_TYPE = "popularity_descending"            # Sort order for search results
XHS_SPECIFIED_NOTE_URL_LIST = [...]           # Specific note URLs (must include xsec_token)
XHS_CREATOR_ID_LIST = [...]                   # Creator IDs to crawl
```

### Data Collection Control
```python
ENABLE_GET_MEIDAS = True                       # Enable media download
ENABLE_GET_COMMENTS = True                     # Enable comment crawling
CRAWLER_MAX_NOTES_COUNT = 200                  # Max notes count
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10    # Max comments per note
```

## 7. Data Source APIs (数据来源API)

XiaoHongShu data is obtained from:
- Search API: Keyword-based note search
- Note Detail API: Individual note information
- Comment API: Note comments and replies
- User API: Creator profile information
- Media API: Image and video content

## 8. Special Features (特殊功能)

### 1. xsec_token Handling
- Required for accessing specific notes
- Automatically handled during crawling
- Stored for future reference

### 2. Content Types
- **Normal Notes**: Text + images content
- **Video Notes**: Video + text content
- Both types support comments and interactions

### 3. IP Location Tracking
- Records IP location for both notes and comments
- Useful for geographic analysis

### 4. Rich Media Support
- Multiple images per note
- High-quality video content
- Comment images support

## 9. Data Analysis Use Cases (数据分析用例)

### Content Analysis
- Popular topics and trends
- Content performance metrics
- User engagement patterns

### Creator Analysis
- Follower growth and demographics
- Content strategy effectiveness
- Interaction rates and engagement

### Market Research
- Brand mention tracking
- Product feedback analysis
- Consumer behavior insights

## 10. Timestamp Fields (时间戳字段)

- `time`: Note publish time (笔记发布时间)
- `last_update_time`: Note last update (笔记最后更新时间)
- `create_time`: Comment publish time (评论发布时间)
- `last_modify_ts`: Data last modified by crawler (爬虫最后修改时间)

All timestamps are Unix timestamps and can be converted using:
```python
from datetime import datetime
readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
```
