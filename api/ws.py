"""
douyin_scraper.api.ws — WebSocket 连接管理器
==============================================
Phase 2 新增：管理所有 /ws/tasks 客户端连接，支持广播消息。
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger("douyin_scraper.api")


class WSManager:
    """管理所有 WebSocket 连接，支持广播消息"""

    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket 连接建立, 当前连接数: %d", len(self._connections))

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)
        logger.info("WebSocket 连接断开, 当前连接数: %d", len(self._connections))

    async def broadcast(self, message: dict):
        """向所有连接广播消息（异步版本，在事件循环中调用）"""
        if not self._connections:
            return
        payload = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.add(ws)
        # 清理已断开的连接
        self._connections -= disconnected

    def broadcast_sync(self, message: dict):
        """向所有连接广播消息（同步版本，从工作线程中调用）"""
        if not self._connections:
            return
        payload = json.dumps(message, ensure_ascii=False)
        # 在工作线程中创建新事件循环发送消息
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.broadcast(message))
            finally:
                loop.close()
        except Exception as e:
            logger.warning("WebSocket 同步广播失败: %s", e)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# 全局单例
ws_manager = WSManager()
