# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import os
import platform
import subprocess
import time
import socket
from typing import Optional, List, Tuple
import asyncio
from pathlib import Path

from tools import utils


class BrowserLauncher:
    """
    浏览器启动器，用于检测和启动用户的Chrome/Edge浏览器
    支持Windows和macOS系统
    """
    
    def __init__(self):
        self.system = platform.system()
        self.browser_process = None
        self.debug_port = None
        
    def detect_browser_paths(self) -> List[str]:
        """
        检测系统中可用的浏览器路径
        返回按优先级排序的浏览器路径列表
        """
        paths = []
        
        if self.system == "Windows":
            # Windows下的常见Chrome/Edge安装路径
            possible_paths = [
                # Chrome路径
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                # Edge路径
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                # Chrome Beta/Dev/Canary
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Beta\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Dev\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome SxS\Application\chrome.exe"),
            ]
        elif self.system == "Darwin":  # macOS
            # macOS下的常见Chrome/Edge安装路径
            possible_paths = [
                # Chrome路径
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta",
                "/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev",
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
                # Edge路径
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Microsoft Edge Beta.app/Contents/MacOS/Microsoft Edge Beta",
                "/Applications/Microsoft Edge Dev.app/Contents/MacOS/Microsoft Edge Dev",
                "/Applications/Microsoft Edge Canary.app/Contents/MacOS/Microsoft Edge Canary",
            ]
        else:
            # Linux等其他系统
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome-beta",
                "/usr/bin/google-chrome-unstable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/snap/bin/chromium",
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge-beta",
                "/usr/bin/microsoft-edge-dev",
            ]
        
        # 检查路径是否存在且可执行
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                paths.append(path)
                
        return paths
    
    def find_available_port(self, start_port: int = 9222) -> int:
        """
        查找可用的端口
        """
        port = start_port
        while port < start_port + 100:  # 最多尝试100个端口
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
        
        raise RuntimeError(f"无法找到可用的端口，已尝试 {start_port} 到 {port-1}")
    
    def launch_browser(self, browser_path: str, debug_port: int, headless: bool = False, 
                      user_data_dir: Optional[str] = None) -> subprocess.Popen:
        """
        启动浏览器进程
        """
        # 基本启动参数
        args = [
            browser_path,
            f"--remote-debugging-port={debug_port}",
            "--remote-debugging-address=0.0.0.0",  # 允许远程访问
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-hang-monitor",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-web-security",  # 可能有助于某些网站的访问
            "--disable-features=VizDisplayCompositor",
            "--disable-dev-shm-usage",  # 避免共享内存问题
            "--no-sandbox",  # 在CDP模式下关闭沙箱
        ]
        
        # 无头模式
        if headless:
            args.extend([
                "--headless",
                "--disable-gpu",
            ])
        else:
            # 非无头模式下也保持一些稳定性参数
            args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ])
        
        # 用户数据目录
        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")
        
        utils.logger.info(f"[BrowserLauncher] 启动浏览器: {browser_path}")
        utils.logger.info(f"[BrowserLauncher] 调试端口: {debug_port}")
        utils.logger.info(f"[BrowserLauncher] 无头模式: {headless}")
        
        try:
            # 在Windows上，使用CREATE_NEW_PROCESS_GROUP避免Ctrl+C影响子进程
            if self.system == "Windows":
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    preexec_fn=os.setsid  # 创建新的进程组
                )
            
            return process
            
        except Exception as e:
            utils.logger.error(f"[BrowserLauncher] 启动浏览器失败: {e}")
            raise
    
    def wait_for_browser_ready(self, debug_port: int, timeout: int = 30) -> bool:
        """
        等待浏览器准备就绪
        """
        utils.logger.info(f"[BrowserLauncher] 等待浏览器在端口 {debug_port} 上准备就绪...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', debug_port))
                    if result == 0:
                        utils.logger.info(f"[BrowserLauncher] 浏览器已在端口 {debug_port} 上准备就绪")
                        return True
            except Exception:
                pass
            
            time.sleep(0.5)
        
        utils.logger.error(f"[BrowserLauncher] 浏览器在 {timeout} 秒内未能准备就绪")
        return False
    
    def get_browser_info(self, browser_path: str) -> Tuple[str, str]:
        """
        获取浏览器信息（名称和版本）
        """
        try:
            if "chrome" in browser_path.lower():
                name = "Google Chrome"
            elif "edge" in browser_path.lower() or "msedge" in browser_path.lower():
                name = "Microsoft Edge"
            elif "chromium" in browser_path.lower():
                name = "Chromium"
            else:
                name = "Unknown Browser"
            
            # 尝试获取版本信息
            try:
                result = subprocess.run([browser_path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                version = result.stdout.strip() if result.stdout else "Unknown Version"
            except:
                version = "Unknown Version"
            
            return name, version
            
        except Exception:
            return "Unknown Browser", "Unknown Version"
    
    def cleanup(self):
        """
        清理资源，关闭浏览器进程
        """
        if self.browser_process:
            try:
                utils.logger.info("[BrowserLauncher] 正在关闭浏览器进程...")
                
                if self.system == "Windows":
                    # Windows下使用taskkill强制终止进程树
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.browser_process.pid)], 
                                 capture_output=True)
                else:
                    # Unix系统下终止进程组
                    os.killpg(os.getpgid(self.browser_process.pid), 9)
                
                self.browser_process = None
                utils.logger.info("[BrowserLauncher] 浏览器进程已关闭")
                
            except Exception as e:
                utils.logger.warning(f"[BrowserLauncher] 关闭浏览器进程时出错: {e}")
