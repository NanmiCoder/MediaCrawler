# Bilibili Data Structure Documentation

Detailed documentation of data structures that MediaCrawler can extract from Bilibili

## 1. Video Data Structure

### Storage Location
- Folder: `data/bilibili/{publish_date_publish_time_video_id}/`
- File: `video_info.json`

### Data Fields

```json
{
  "video_id": "123456789",              // Video AV ID (aid)
  "video_type": "video",                // Content type, fixed as "video"
  "title": "Video Title",               // Video title (max 500 characters)
  "desc": "Video description content",  // Video description (max 500 characters)
  "create_time": 1640995200,            // Publish timestamp (Unix timestamp)
  "user_id": "20813884",                // Creator user ID (mid)
  "nickname": "Creator Nickname",       // Creator nickname
  "avatar": "https://i0.hdslb.com/...", // Creator avatar URL
  "liked_count": "12345",               // Like count
  "disliked_count": "123",              // Dislike count
  "video_play_count": "567890",         // View count
  "video_favorite_count": "4567",       // Favorite count
  "video_share_count": "890",           // Share count
  "video_coin_count": "2345",           // Coin count
  "video_danmaku": "6789",              // Danmaku count
  "video_comment": "1234",              // Comment count
  "last_modify_ts": 1692607200,         // Last modified timestamp
  "video_url": "https://www.bilibili.com/video/av123456789", // Video URL
  "video_cover_url": "https://i0.hdslb.com/...", // Video cover URL
  "source_keyword": "programming,side project", // Search keywords
  "add_ts": 1692607200,                 // Added timestamp
  "save_time": "2024-08-11 15:30:00"    // Save time (readable format)
}
```

## 2. Comments Data Structure

### Storage Location
- Folder: `data/bilibili/{publish_date_publish_time_video_id}/`
- File: `comments.json` (array format)

### Data Fields

```json
[
  {
    "comment_id": "987654321",          // Comment ID (rpid)
    "parent_comment_id": "0",           // Parent comment ID, 0 means top-level comment
    "create_time": 1640995300,          // Comment timestamp
    "video_id": "123456789",            // Associated video ID
    "content": "This video is amazing!", // Comment content
    "user_id": "12345678",              // Commenter user ID
    "nickname": "User Nickname",        // Commenter nickname
    "sex": "Male",                      // User gender
    "sign": "User signature",           // User signature
    "avatar": "https://i0.hdslb.com/...", // User avatar URL
    "sub_comment_count": "5",           // Sub-comment count
    "like_count": 10,                   // Comment like count
    "last_modify_ts": 1692607200,       // Last modified timestamp
    "add_ts": 1692607200,               // Added timestamp
    "save_time": "2024-08-11 15:30:00"  // Save time (readable format)
  }
]
```

## 3. Creator Information Data Structure

### Availability
⚠️ **Only available when using `CRAWLER_TYPE = "creator"` mode**

### Data Fields

```json
{
  "user_id": "20813884",               // Creator user ID (mid)
  "nickname": "Creator Nickname",      // Creator nickname
  "sex": "Male",                       // Gender
  "sign": "Creator signature",         // Personal signature
  "avatar": "https://i0.hdslb.com/...", // Avatar URL
  "last_modify_ts": 1692607200,        // Last modified timestamp
  "total_fans": 100000,                // Total followers
  "total_liked": 500000,               // Total likes received
  "user_rank": 6,                      // User level
  "is_official": 0                     // Official verification (0=No, 1=Yes)
}
```

### Configuration Required
- Set `CRAWLER_TYPE = "creator"` in config
- Add creator IDs to `BILI_CREATOR_ID_LIST` in bilibili_config.py
- Set `CREATOR_MODE = True` in bilibili_config.py

## 4. Fans/Followings Data Structure

### Availability
⚠️ **Only available when using `CRAWLER_TYPE = "creator"` mode with `CREATOR_MODE = True`**

### Data Fields

```json
{
  "up_id": "20813884",                 // Creator ID
  "fan_id": "12345678",                // Fan/Follower ID
  "up_name": "Creator Nickname",       // Creator nickname
  "fan_name": "Fan Nickname",          // Fan nickname
  "up_sign": "Creator signature",      // Creator signature
  "fan_sign": "Fan signature",         // Fan signature
  "up_avatar": "https://i0.hdslb.com/...", // Creator avatar
  "fan_avatar": "https://i0.hdslb.com/...", // Fan avatar
  "last_modify_ts": 1692607200         // Last modified timestamp
}
```

### Configuration Required
- Set `CRAWLER_TYPE = "creator"` in config
- Set `CREATOR_MODE = True` in bilibili_config.py
- Configure `CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100` (max fans/followings per creator)

### Storage Location
These data are stored in the database or other storage options (csv, json, sqlite), **NOT** in the video folder structure.
```

## 5. Dynamics Data Structure

### Availability
⚠️ **Only available when using `CRAWLER_TYPE = "creator"` mode with `CREATOR_MODE = True`**

### Data Fields

```json
{
  "dynamic_id": "987654321",           // Dynamic ID
  "user_id": "20813884",              // Publisher user ID
  "user_name": "Creator Nickname",     // Publisher nickname
  "text": "Dynamic content text",       // Dynamic text content
  "type": "video",                     // Dynamic type (video/image/text etc.)
  "pub_ts": 1640995200,                // Publish timestamp
  "total_comments": 100,               // Total comments
  "total_forwards": 50,                // Total forwards
  "total_liked": 200,                  // Total likes
  "last_modify_ts": 1692607200         // Last modified timestamp
}
```

### Configuration Required
- Set `CRAWLER_TYPE = "creator"` in config
- Set `CREATOR_MODE = True` in bilibili_config.py
- Configure `CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50` (max dynamics per creator)

### Storage Location
This data is stored in the database or other storage options (csv, json, sqlite), **NOT** in the video folder structure.
```

## 6. Media Files Data Structure

### Video Files
- Location: `data/bilibili/{publish_date_publish_time_video_id}/video.mp4`
- Format: MP4 or other video formats
- Naming: Named according to original file extension

### Image Files
- Location: `data/bilibili/{publish_date_publish_time_video_id}/images/`
- Format: JPG, PNG and other image formats
- Includes: Cover images, dynamic images, etc.

## 7. Folder Structure Example

```
data/bilibili/
├── 20240101_123000_123456789/          # Video publish_date_time_video_id
│   ├── video_info.json                 # Video basic information
│   ├── comments.json                   # Comments information
│   ├── video.mp4                       # Video file (if media download enabled)
│   └── images/                         # Images folder
│       ├── cover.jpg                   # Cover image
│       └── ...                         # Other images
└── 20240102_150000_987654321/
    ├── video_info.json
    ├── comments.json
    └── video.mp4
```

## 8. Configuration Options

### Crawler Types
MediaCrawler supports 3 different crawler types:

#### 1. Search Mode (Default)
```python
CRAWLER_TYPE = "search"
```
- Crawls videos based on keywords
- Gets video info + comments + media files
- Uses `video_folder` storage structure

#### 2. Detail Mode
```python
CRAWLER_TYPE = "detail"
```
- Crawls specific video details
- Requires video IDs in `BILI_SPECIFIED_ID_LIST`

#### 3. Creator Mode
```python
CRAWLER_TYPE = "creator"
CREATOR_MODE = True
```
- Crawls creator profile data, fans, followings, and dynamics
- Requires creator IDs in `BILI_CREATOR_ID_LIST`
- **Note**: Creator data is stored in database/csv/json, NOT in video folders

### Storage Options
- `SAVE_DATA_OPTION = "video_folder"` - Enable video folder storage mode (for videos)
- `SAVE_DATA_OPTION = "db"` - Database storage (for all data types)
- `SAVE_DATA_OPTION = "csv"` - CSV files storage
- `SAVE_DATA_OPTION = "json"` - JSON files storage
- `SAVE_DATA_OPTION = "sqlite"` - SQLite database storage

### Data Collection Control
- `ENABLE_GET_MEIDAS = True` - Enable media file download
- `ENABLE_GET_COMMENTS = True` - Enable comment crawling
- `ENABLE_GET_SUB_COMMENTS = False` - Enable sub-comment crawling
- `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10` - Max comments per video
- `CRAWLER_MAX_NOTES_COUNT = 200` - Maximum video count
- `MAX_CONCURRENCY_NUM = 1` - Concurrency control
- `CRAWLER_MAX_SLEEP_SEC = 2` - Crawling interval time

### Creator Mode Specific Settings
- `CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100` - Max fans/followings per creator
- `CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50` - Max dynamics per creator

## 9. Data Source APIs

Data is mainly obtained from the following Bilibili APIs:
- Video Detail API: Get video basic information and statistics
- Comment API: Get video comment list
- User Info API: Get creator detailed information
- Search API: Search videos by keywords
- Dynamic API: Get creator dynamic information

## 10. Timestamp Explanation

- `create_time`: Video publish time (Unix timestamp)
- `ctime`: Comment publish time (Unix timestamp)
- `pub_ts`: Dynamic publish time (Unix timestamp)
- `add_ts`: Data added to local time (Unix timestamp)
- `last_modify_ts`: Last modified time (Unix timestamp)
- `save_time`: Readable format save time

All timestamps can be converted using Python's datetime module:
```python
from datetime import datetime
readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
```
