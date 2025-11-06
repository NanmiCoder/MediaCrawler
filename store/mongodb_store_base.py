# -*- coding: utf-8 -*-
"""
MongoDB存储基类
提供MongoDB连接管理和通用存储方法
"""
import asyncio
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from config import db_config
from tools import utils


class MongoDBConnection:
    """MongoDB连接管理单例类"""
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance

    async def get_client(self) -> AsyncIOMotorClient:
        """获取MongoDB客户端"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    await self._connect()
        return self._client

    async def get_db(self) -> AsyncIOMotorDatabase:
        """获取MongoDB数据库"""
        if self._db is None:
            async with self._lock:
                if self._db is None:
                    await self._connect()
        return self._db

    async def _connect(self):
        """建立MongoDB连接"""
        try:
            mongo_config = db_config.mongodb_config
            host = mongo_config.get("host", "localhost")
            port = mongo_config.get("port", 27017)
            user = mongo_config.get("user", "")
            password = mongo_config.get("password", "")
            db_name = mongo_config.get("db_name", "media_crawler")

            # 构建连接URL
            if user and password:
                connection_url = f"mongodb://{user}:{password}@{host}:{port}/"
            else:
                connection_url = f"mongodb://{host}:{port}/"

            self._client = AsyncIOMotorClient(connection_url, serverSelectionTimeoutMS=5000)
            # 测试连接
            await self._client.server_info()
            self._db = self._client[db_name]
            utils.logger.info(f"[MongoDBConnection] Successfully connected to MongoDB at {host}:{port}, database: {db_name}")
        except Exception as e:
            utils.logger.error(f"[MongoDBConnection] Failed to connect to MongoDB: {e}")
            raise

    async def close(self):
        """关闭MongoDB连接"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            utils.logger.info("[MongoDBConnection] MongoDB connection closed")


class MongoDBStoreBase:
    """MongoDB存储基类"""

    def __init__(self, collection_prefix: str):
        """
        初始化MongoDB存储基类
        Args:
            collection_prefix: 集合名称前缀（如：xhs, douyin, bilibili等）
        """
        self.collection_prefix = collection_prefix
        self._connection = MongoDBConnection()

    async def get_collection(self, collection_suffix: str) -> AsyncIOMotorCollection:
        """
        获取MongoDB集合
        Args:
            collection_suffix: 集合名称后缀（如：contents, comments, creators）
        Returns:
            MongoDB集合对象
        """
        db = await self._connection.get_db()
        collection_name = f"{self.collection_prefix}_{collection_suffix}"
        return db[collection_name]

    async def save_or_update(self, collection_suffix: str, query: Dict, data: Dict) -> bool:
        """
        保存或更新数据（upsert操作）
        Args:
            collection_suffix: 集合名称后缀
            query: 查询条件
            data: 要保存的数据
        Returns:
            是否成功
        """
        try:
            collection = await self.get_collection(collection_suffix)
            result = await collection.update_one(
                query,
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase.save_or_update] Failed to save data to {self.collection_prefix}_{collection_suffix}: {e}")
            return False

    async def find_one(self, collection_suffix: str, query: Dict) -> Optional[Dict]:
        """
        查询单条数据
        Args:
            collection_suffix: 集合名称后缀
            query: 查询条件
        Returns:
            查询结果
        """
        try:
            collection = await self.get_collection(collection_suffix)
            result = await collection.find_one(query)
            return result
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase.find_one] Failed to query from {self.collection_prefix}_{collection_suffix}: {e}")
            return None

    async def find_many(self, collection_suffix: str, query: Dict, limit: int = 0) -> List[Dict]:
        """
        查询多条数据
        Args:
            collection_suffix: 集合名称后缀
            query: 查询条件
            limit: 限制返回数量，0表示不限制
        Returns:
            查询结果列表
        """
        try:
            collection = await self.get_collection(collection_suffix)
            cursor = collection.find(query)
            if limit > 0:
                cursor = cursor.limit(limit)
            results = await cursor.to_list(length=None)
            return results
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase.find_many] Failed to query from {self.collection_prefix}_{collection_suffix}: {e}")
            return []

    async def create_index(self, collection_suffix: str, keys: List[tuple], unique: bool = False):
        """
        创建索引
        Args:
            collection_suffix: 集合名称后缀
            keys: 索引键列表，例如：[("note_id", 1)]
            unique: 是否创建唯一索引
        """
        try:
            collection = await self.get_collection(collection_suffix)
            await collection.create_index(keys, unique=unique)
            utils.logger.info(f"[MongoDBStoreBase.create_index] Created index on {self.collection_prefix}_{collection_suffix}")
        except Exception as e:
            utils.logger.error(f"[MongoDBStoreBase.create_index] Failed to create index: {e}")

