from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import subprocess
import asyncio
from typing import Dict, Any, Optional
import json

app = FastAPI(title="MediaCrawler API", description="API for MediaCrawler configuration and execution")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request/response models
class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

class CommandRequest(BaseModel):
    platform: str
    login_type: str
    crawler_type: str
    keywords: Optional[str] = None
    start_page: Optional[int] = None
    get_comment: Optional[bool] = None
    get_sub_comment: Optional[bool] = None
    save_data_option: Optional[str] = None
    cookies: Optional[str] = None

class CommandResponse(BaseModel):
    success: bool
    message: str
    output: Optional[str] = None
    error: Optional[str] = None

# Helper function to read config file
def read_config_file():
    config_path = os.path.join("..", "config", "base_config.py")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config file: {str(e)}")

# Helper function to parse config values
def parse_config_content(content: str) -> Dict[str, Any]:
    config_values = {}
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            # Handle simple assignments like PLATFORM = "xhs"
            match = re.match(r'^([A-Z_]+)\s*=\s*(.+)$', line)
            if match:
                key = match.group(1)
                value_str = match.group(2).strip()
                
                # Parse different types of values
                try:
                    if value_str.startswith('"') and value_str.endswith('"'):
                        # String value
                        config_values[key] = value_str[1:-1]
                    elif value_str.startswith("'") and value_str.endswith("'"):
                        # String value with single quotes
                        config_values[key] = value_str[1:-1]
                    elif value_str.lower() in ['true', 'false']:
                        # Boolean value
                        config_values[key] = value_str.lower() == 'true'
                    elif value_str.isdigit() or (value_str.startswith('-') and value_str[1:].isdigit()):
                        # Integer value
                        config_values[key] = int(value_str)
                    elif re.match(r'^-?\d+\.\d+$', value_str):
                        # Float value
                        config_values[key] = float(value_str)
                    elif value_str.startswith('[') and value_str.endswith(']'):
                        # List value - simplified parsing
                        config_values[key] = value_str
                    else:
                        # Default to string
                        config_values[key] = value_str
                except:
                    config_values[key] = value_str
    
    return config_values

# Helper function to update config file
def update_config_file(config_values: Dict[str, Any]):
    config_path = os.path.join("..", "config", "base_config.py")
    
    try:
        content = read_config_file()
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            original_line = line
            stripped_line = line.strip()
            
            if stripped_line and not stripped_line.startswith('#') and '=' in stripped_line:
                match = re.match(r'^(\s*)([A-Z_]+)\s*=\s*(.+)$', line)
                if match:
                    indent = match.group(1)
                    key = match.group(2)
                    
                    if key in config_values:
                        new_value = config_values[key]
                        
                        # Format the new value appropriately
                        if isinstance(new_value, str):
                            if key in ['XHS_SPECIFIED_NOTE_URL_LIST', 'DY_SPECIFIED_ID_LIST', 'KS_SPECIFIED_ID_LIST', 
                                     'BILI_SPECIFIED_ID_LIST', 'WEIBO_SPECIFIED_ID_LIST', 'WEIBO_CREATOR_ID_LIST',
                                     'TIEBA_SPECIFIED_ID_LIST', 'TIEBA_NAME_LIST', 'TIEBA_CREATOR_URL_LIST',
                                     'XHS_CREATOR_ID_LIST', 'DY_CREATOR_ID_LIST', 'BILI_CREATOR_ID_LIST',
                                     'KS_CREATOR_ID_LIST', 'ZHIHU_CREATOR_URL_LIST', 'ZHIHU_SPECIFIED_ID_LIST']:
                                # Keep list format as-is
                                updated_lines.append(f'{indent}{key} = {new_value}')
                            else:
                                # Regular string
                                updated_lines.append(f'{indent}{key} = "{new_value}"')
                        elif isinstance(new_value, bool):
                            updated_lines.append(f'{indent}{key} = {str(new_value)}')
                        elif isinstance(new_value, (int, float)):
                            updated_lines.append(f'{indent}{key} = {new_value}')
                        else:
                            updated_lines.append(f'{indent}{key} = {new_value}')
                    else:
                        updated_lines.append(original_line)
                else:
                    updated_lines.append(original_line)
            else:
                updated_lines.append(original_line)
        
        # Write the updated content back to file
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config file: {str(e)}")

@app.get("/")
async def root():
    return {"message": "MediaCrawler API is running"}

@app.get("/config")
async def get_config():
    """Get current configuration values"""
    try:
        content = read_config_file()
        config_values = parse_config_content(content)
        return {"config": config_values}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration values"""
    try:
        update_config_file(request.config)
        return {"success": True, "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-crawler")
async def run_crawler(request: CommandRequest):
    """Execute crawler command"""
    try:
        # Build the command
        cmd = ["uv", "run", "main.py", "--platform", request.platform, "--lt", request.login_type, "--type", request.crawler_type]
        
        # Add optional parameters
        if request.keywords:
            cmd.extend(["--keywords", request.keywords])
        if request.start_page is not None:
            cmd.extend(["--start", str(request.start_page)])
        if request.get_comment is not None:
            cmd.extend(["--get_comment", str(request.get_comment).lower()])
        if request.get_sub_comment is not None:
            cmd.extend(["--get_sub_comment", str(request.get_sub_comment).lower()])
        if request.save_data_option:
            cmd.extend(["--save_data_option", request.save_data_option])
        if request.cookies:
            cmd.extend(["--cookies", request.cookies])
        
        # Change to the parent directory to run the command
        parent_dir = os.path.abspath("..")
        
        # Run the command asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=parent_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return CommandResponse(
                success=True,
                message="Crawler executed successfully",
                output=stdout.decode('utf-8') if stdout else None
            )
        else:
            return CommandResponse(
                success=False,
                message="Crawler execution failed",
                error=stderr.decode('utf-8') if stderr else None
            )
            
    except Exception as e:
        return CommandResponse(
            success=False,
            message="Failed to execute crawler",
            error=str(e)
        )

@app.get("/command-options")
async def get_command_options():
    """Get available command options"""
    return {
        "platforms": [
            {"value": "xhs", "label": "小红书 (Xiaohongshu)"},
            {"value": "dy", "label": "抖音 (Douyin)"},
            {"value": "ks", "label": "快手 (Kuaishou)"},
            {"value": "bili", "label": "B站 (Bilibili)"},
            {"value": "wb", "label": "微博 (Weibo)"},
            {"value": "tieba", "label": "贴吧 (Tieba)"},
            {"value": "zhihu", "label": "知乎 (Zhihu)"}
        ],
        "login_types": [
            {"value": "qrcode", "label": "二维码登录 (QR Code)"},
            {"value": "phone", "label": "手机号登录 (Phone)"},
            {"value": "cookie", "label": "Cookie登录 (Cookie)"}
        ],
        "crawler_types": [
            {"value": "search", "label": "关键词搜索 (Search)"},
            {"value": "detail", "label": "帖子详情 (Detail)"},
            {"value": "creator", "label": "创作者主页 (Creator)"}
        ],
        "save_data_options": [
            {"value": "csv", "label": "CSV 文件"},
            {"value": "db", "label": "数据库 (Database)"},
            {"value": "json", "label": "JSON 文件"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 