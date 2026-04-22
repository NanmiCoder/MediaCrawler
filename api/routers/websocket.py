# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/websocket.py
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

import asyncio
from datetime import datetime
from typing import Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services import crawler_manager
from ..schemas import StatsUpdateMessage, DataUpdateMessage, SubscriptionUpdateMessage

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def broadcast_stats_update(platform: str = "xhs"):
    """
    Broadcast stats_update message to all connected WebSocket clients.
    Called by FileWatcherService when JSONL files change.
    Recalculates stats from files to ensure consistency.

    Args:
        platform: The platform identifier that triggered this update (e.g., "xhs", "dy", "bili", "zhihu")
    """
    from .notes import get_notes_stats

    try:
        stats = await get_notes_stats()
        message = StatsUpdateMessage(
            type="stats_update",
            total_notes=stats.get("total_notes", 0),
            total_images=stats.get("total_images", 0),
            timestamp=datetime.now().isoformat()
        )
        await manager.broadcast(message.model_dump())
        print(f"[WS] Broadcasted stats_update from platform '{platform}': {message.total_notes} notes, {message.total_images} images")
    except Exception as e:
        print(f"[WS] Error broadcasting stats_update from platform '{platform}': {e}")


async def broadcast_platform_update(platform: str):
    """
    Broadcast platform-specific data_update message to all connected WebSocket clients.
    This allows frontend to filter and route updates to specific viewer components.

    Args:
        platform: The platform identifier (e.g., "xhs", "dy", "bili", "zhihu")
    """
    try:
        message = DataUpdateMessage(
            type="data_update",
            platform=platform,
            timestamp=datetime.now().isoformat()
        )
        await manager.broadcast(message.model_dump())
        print(f"[WS] Broadcasted data_update for platform '{platform}'")
    except Exception as e:
        print(f"[WS] Error broadcasting data_update for platform '{platform}': {e}")


async def broadcast_subscription_update(
    subscription_id: str,
    keyword: str,
    platform: str,
    new_count: int = 0
):
    """
    Broadcast subscription_update message to all connected WebSocket clients.
    Called when a subscription-triggered crawl completes.

    Args:
        subscription_id: The subscription identifier
        keyword: The search keyword for this subscription
        platform: The platform identifier (e.g., "xhs", "zhihu")
        new_count: Number of new items crawled
    """
    try:
        message = SubscriptionUpdateMessage(
            type="subscription_update",
            subscription_id=subscription_id,
            keyword=keyword,
            platform=platform,
            new_count=new_count,
            timestamp=datetime.now().isoformat()
        )
        await manager.broadcast(message.model_dump())
        print(f"[WS] Broadcasted subscription_update for '{keyword}' on {platform}: {new_count} new items")
    except Exception as e:
        print(f"[WS] Error broadcasting subscription_update: {e}")


async def send_initial_stats(websocket: WebSocket):
    """Send current stats to a newly connected WebSocket client."""
    from .notes import get_notes_stats

    try:
        stats = await get_notes_stats()
        message = StatsUpdateMessage(
            type="stats_update",
            total_notes=stats.get("total_notes", 0),
            total_images=stats.get("total_images", 0),
            timestamp=datetime.now().isoformat()
        )
        await websocket.send_json(message.model_dump())
    except Exception as e:
        print(f"[WS] Error sending initial stats: {e}")


async def log_broadcaster():
    """Background task: read logs from queue and broadcast"""
    queue = crawler_manager.get_log_queue()
    while True:
        try:
            # Get log entry from queue
            entry = await queue.get()
            # Broadcast to all WebSocket connections
            await manager.broadcast(entry.model_dump())
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Log broadcaster error: {e}")
            await asyncio.sleep(0.1)


# Global broadcast task
_broadcaster_task: Optional[asyncio.Task] = None


def start_broadcaster():
    """Start broadcast task"""
    global _broadcaster_task
    if _broadcaster_task is None or _broadcaster_task.done():
        _broadcaster_task = asyncio.create_task(log_broadcaster())


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket log stream"""
    print("[WS] New connection attempt")

    try:
        # Ensure broadcast task is running
        start_broadcaster()

        await manager.connect(websocket)
        print(f"[WS] Connected, active connections: {len(manager.active_connections)}")

        # Send existing logs
        for log in crawler_manager.logs:
            try:
                await websocket.send_json(log.model_dump())
            except Exception as e:
                print(f"[WS] Error sending existing log: {e}")
                break

        print(f"[WS] Sent {len(crawler_manager.logs)} existing logs, entering main loop")

        while True:
            # Keep connection alive, receive heartbeat or any message
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text("ping")
                except Exception as e:
                    print(f"[WS] Error sending ping: {e}")
                    break

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {type(e).__name__}: {e}")
    finally:
        manager.disconnect(websocket)
        print(f"[WS] Cleanup done, active connections: {len(manager.active_connections)}")


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """
    WebSocket status stream - sends crawler status, stats updates, and data updates.

    This endpoint:
    1. Sends initial stats on connect
    2. Sends crawler status every second
    3. Receives broadcast messages (data_update, stats_update, subscription_update) from manager
    """
    await manager.connect(websocket)

    try:
        # Send initial stats on connect
        await send_initial_stats(websocket)

        while True:
            # Send status every second (with type field for frontend parsing)
            status = crawler_manager.get_status()
            status["type"] = "crawler_status"
            await websocket.send_json(status)

            # Wait for incoming messages (heartbeat) with timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # No message received, continue loop
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Status] Error: {e}")
    finally:
        manager.disconnect(websocket)
