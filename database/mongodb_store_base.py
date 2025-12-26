# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/database/mongodb_store_base.py
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

"""MongoDB storage base class: Provides connection management and common storage methods"""
import asyncio
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from config import db_config
from tools import utils


class MongoDBConnection:
    """MongoDB connection management (singleton pattern)"""
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance

    async def get_client(self) -> AsyncIOMotorClient:
        """Get client"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    await self._connect()
        return self._client

    async def get_db(self) -> AsyncIOMotorDatabase:
        """Get database"""
        if self._db is None:
            async with self._lock:
                if self._db is None:
                    await self._connect()
        return self._db

    async def _connect(self):
        """Establish connection"""
        try:
            mongo_config = db_config.mongodb_config
            host = mongo_config["host"]
            port = mongo_config["port"]
            user = mongo_config["user"]
            password = mongo_config["password"]
            db_name = mongo_config["db_name"]

            # Build connection URL (with/without authentication)
            if user and password:
                connection_url = f"mongodb://{user}:{password}@{host}:{port}/"
            else:
                connection_url = f"mongodb://{host}:{port}/"

            self._client = AsyncIOMotorClient(connection_url, serverSelectionTimeoutMS=5000)
            await self._client.server_info()  # Test connection
            self._db = self._client[db_name]
            utils.logger.info(f"[MongoDBConnection] Connected to {host}:{port}/{db_name}")
        except Exception as e:
            utils.logger.error(f"[MongoDBConnection] Connection failed: {e}")
            raise

    async def close(self):
        """Close connection"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            utils.logger.info("[MongoDBConnection] Connection closed")


class MongoDBStoreBase:
    """MongoDB storage base class: Provides common CRUD operations"""

    def __init__(self, collection_prefix: str):
        """Initialize storage base class
        Args:
            collection_prefix: Platform prefix (xhs/douyin/bilibili, etc.)
        """
        self.collection_prefix = collection_prefix
        self._connection = MongoDBConnection()

    async def get_collection(self, collection_suffix: str) -> AsyncIOMotorCollection:
        """Get collection: {prefix}_{suffix}"""
        db = await self._connection.get_db()
        collection_name = f"{self.collection_prefix}_{collection_suffix}"
        return db[collection_name]

    async def save_or_update(self, collection_suffix: str, query: Dict, data: Dict) -> bool:
        """Save or update data (upsert)"""
        try:
            collection = await self.get_collection(collection_suffix)
            await collection.update_one(query, {"$set": data}, upsert=True)
            return True
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase] Save failed ({self.collection_prefix}_{collection_suffix}): {e}")
            return False

    async def find_one(self, collection_suffix: str, query: Dict) -> Optional[Dict]:
        """Query a single record"""
        try:
            collection = await self.get_collection(collection_suffix)
            return await collection.find_one(query)
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase] Find one failed ({self.collection_prefix}_{collection_suffix}): {e}")
            return None

    async def find_many(self, collection_suffix: str, query: Dict, limit: int = 0) -> List[Dict]:
        """Query multiple records (limit=0 means no limit)"""
        try:
            collection = await self.get_collection(collection_suffix)
            cursor = collection.find(query)
            if limit > 0:
                cursor = cursor.limit(limit)
            return await cursor.to_list(length=None)
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase] Find many failed ({self.collection_prefix}_{collection_suffix}): {e}")
            return []

    async def create_index(self, collection_suffix: str, keys: List[tuple], unique: bool = False):
        """Create index: keys=[("field", 1)]"""
        try:
            collection = await self.get_collection(collection_suffix)
            await collection.create_index(keys, unique=unique)
            utils.logger.info(f"[MongoDBStoreBase] Index created on {self.collection_prefix}_{collection_suffix}")
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase] Create index failed: {e}")
