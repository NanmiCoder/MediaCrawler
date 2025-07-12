# MediaCrawler Frontend UI Setup Guide

This guide will help you set up the modern web interface for MediaCrawler, which provides a user-friendly way to configure settings and run crawler commands.

## Overview

The frontend system consists of:

1. **Next.js Frontend** (`frontend/`) - Modern React-based web interface
2. **FastAPI Backend** (`api/`) - API server for config management and command execution

## Quick Start

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Install Backend Dependencies

```bash
cd ../api
uv pip install -r requirements.txt
```

### 3. Start the Backend API

```bash
# From the api directory
python main.py
```

The API will start on http://localhost:8000

### 4. Start the Frontend

```bash
# From the frontend directory  
npm run dev
```

The web interface will be available at http://localhost:3000

## Features

### Config Tab
- **Visual Configuration**: Edit all `base_config.py` settings through a modern interface
- **Organized Sections**: Settings grouped into logical categories
  - Basic Configuration (Platform, Login Type, etc.)
  - Crawler Settings (Max notes, comments, etc.)
  - Proxy Settings (IP proxy configuration)
  - Advanced Settings (User Agent, CDP mode, etc.)
- **Auto-Save**: Changes are automatically saved to the config file
- **Type Safety**: Form validation ensures correct data types

### Crawler Tab  
- **Command Builder**: Visual interface to build crawler commands
- **Real-time Preview**: See the generated command before execution
- **Quick Templates**: Pre-configured commands for common scenarios
- **Execution Monitoring**: View command output and errors in real-time
- **Parameter Validation**: Ensures required parameters are provided

## Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐
│   Next.js UI    │ ──────────────► │   FastAPI       │
│   (Port 3000)   │                 │   (Port 8000)   │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │                                   │
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│   Browser       │                 │ File System     │
│   Interface     │                 │ (config files)  │
└─────────────────┘                 └─────────────────┘
```

## API Endpoints

The FastAPI backend provides these endpoints:

- `GET /config` - Retrieve current configuration
- `POST /config` - Update configuration file
- `POST /run-crawler` - Execute crawler with parameters
- `GET /command-options` - Get available platforms, types, etc.

## Usage Examples

### Configuring for Xiaohongshu (XHS)
1. Open the Config tab
2. Set Platform to "小红书 (Xiaohongshu)"
3. Set Login Type to "二维码登录 (QR Code)"
4. Configure keywords: "编程副业,编程兼职"
5. Enable comments if needed
6. Click "保存配置 (Save Configuration)"

### Running a Search Crawler
1. Switch to the Crawler tab
2. Select platform, login type, and crawler type
3. Enter keywords for search
4. Preview the generated command
5. Click "运行爬虫 (Run Crawler)"
6. Monitor the execution output

### Using Quick Templates
The Crawler tab includes pre-configured templates for common scenarios:
- XHS Search with Comments
- Douyin Search with Comments  
- Bilibili Search with Comments
- Weibo Search with Comments
- And more...

## Troubleshooting

### Frontend won't start
- Ensure Node.js 16+ is installed
- Run `npm install` in the frontend directory
- Check for port conflicts on 3000

### Backend API errors
- Ensure Python dependencies are installed with `uv pip install -r requirements.txt`
- Verify the config file path is correct
- Check for port conflicts on 8000

### Config changes not saving
- Ensure the API backend is running
- Check file permissions on config/base_config.py
- Verify CORS is properly configured

### Commands not executing
- Ensure you're in the correct directory structure
- Check that `uv` is installed and accessible
- Verify all required parameters are provided

## Development

### Adding New Configuration Options
1. Update the config parsing in `api/main.py`
2. Add form fields in `frontend/components/config-tab.tsx`
3. Update the backend's config update logic

### Adding New Command Options
1. Update the command builder in `api/main.py`
2. Add UI elements in `frontend/components/crawler-tab.tsx`
3. Test with the actual MediaCrawler commands

## Security Considerations

- The API runs locally and should not be exposed publicly
- Configuration changes directly modify system files
- Command execution has full system access
- Use only in trusted environments

## License

This frontend system follows the same license terms as the main MediaCrawler project. Use responsibly and in accordance with platform terms of service. 