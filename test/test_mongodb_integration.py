# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/test_mongodb_integration.py
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
import unittest
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mongodb_store_base import MongoDBConnection, MongoDBStoreBase
from store.xhs._store_impl import XhsMongoStoreImplement
from store.douyin._store_impl import DouyinMongoStoreImplement
from config import db_config


class TestMongoDBRealConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            conn = MongoDBConnection()
            asyncio.run(conn._connect())
            cls.mongodb_available = True
            print("\n✓ MongoDB connection successful")
        except Exception as e:
            cls.mongodb_available = False
            print(f"\n✗ MongoDB connection failed: {e}")

    def setUp(self):
        if not self.mongodb_available:
            self.skipTest("MongoDB not available")

        MongoDBConnection._instance = None
        MongoDBConnection._client = None
        MongoDBConnection._db = None

    def tearDown(self):
        if self.mongodb_available:
            conn = MongoDBConnection()
            asyncio.run(conn.close())

    @classmethod
    def tearDownClass(cls):
        if cls.mongodb_available:
            async def cleanup():
                conn = MongoDBConnection()
                db = await conn.get_db()

                test_collections = [
                    "test_xhs_contents",
                    "test_xhs_comments",
                    "test_xhs_creators",
                    "test_douyin_contents",
                    "test_douyin_comments",
                    "test_douyin_creators"
                ]

                for collection_name in test_collections:
                    try:
                        await db[collection_name].drop()
                    except:
                        pass

                await conn.close()

            try:
                asyncio.run(cleanup())
                print("\n✓ Test data cleanup completed")
            except Exception as e:
                print(f"\n✗ Error cleaning up test data: {e}")

    def test_real_connection(self):
        async def test():
            conn = MongoDBConnection()
            client = await conn.get_client()
            db = await conn.get_db()

            self.assertIsNotNone(client)
            self.assertIsNotNone(db)

            result = await db.command("ping")
            self.assertEqual(result.get("ok"), 1.0)

        asyncio.run(test())

    def test_real_save_and_query(self):
        async def test():
            store = MongoDBStoreBase(collection_prefix="test_xhs")

            test_data = {
                "note_id": "test_note_001",
                "title": "Test Note",
                "content": "This is a test content",
                "created_at": datetime.now().isoformat()
            }

            result = await store.save_or_update(
                "contents",
                {"note_id": "test_note_001"},
                test_data
            )
            self.assertTrue(result)

            found = await store.find_one(
                "contents",
                {"note_id": "test_note_001"}
            )

            self.assertIsNotNone(found)
            self.assertEqual(found["note_id"], "test_note_001")
            self.assertEqual(found["title"], "Test Note")

        asyncio.run(test())

    def test_real_update(self):
        async def test():
            store = MongoDBStoreBase(collection_prefix="test_xhs")

            initial_data = {
                "note_id": "test_note_002",
                "title": "Initial Title",
                "likes": 10
            }

            await store.save_or_update(
                "contents",
                {"note_id": "test_note_002"},
                initial_data
            )

            updated_data = {
                "note_id": "test_note_002",
                "title": "Updated Title",
                "likes": 100
            }

            await store.save_or_update(
                "contents",
                {"note_id": "test_note_002"},
                updated_data
            )

            found = await store.find_one(
                "contents",
                {"note_id": "test_note_002"}
            )

            self.assertEqual(found["title"], "Updated Title")
            self.assertEqual(found["likes"], 100)

        asyncio.run(test())

    def test_real_find_many(self):
        async def test():
            store = MongoDBStoreBase(collection_prefix="test_xhs")

            test_user_id = "test_user_123"
            for i in range(5):
                data = {
                    "note_id": f"test_note_{i:03d}",
                    "user_id": test_user_id,
                    "title": f"Test Note {i}",
                    "likes": i * 10
                }
                await store.save_or_update(
                    "contents",
                    {"note_id": data["note_id"]},
                    data
                )

            results = await store.find_many(
                "contents",
                {"user_id": test_user_id}
            )

            self.assertGreaterEqual(len(results), 5)

            limited_results = await store.find_many(
                "contents",
                {"user_id": test_user_id},
                limit=3
            )

            self.assertEqual(len(limited_results), 3)

        asyncio.run(test())

    def test_real_create_index(self):
        async def test():
            store = MongoDBStoreBase(collection_prefix="test_xhs")

            await store.create_index(
                "contents",
                [("note_id", 1)],
                unique=True
            )

            collection = await store.get_collection("contents")
            indexes = await collection.index_information()

            self.assertIn("note_id_1", indexes)

        asyncio.run(test())

    def test_xhs_store_implementation(self):
        async def test():
            store = XhsMongoStoreImplement()

            note_data = {
                "note_id": "xhs_test_001",
                "user_id": "user_001",
                "nickname": "Test User",
                "title": "Xiaohongshu Test Note",
                "desc": "This is a test note",
                "type": "normal",
                "liked_count": "100",
                "collected_count": "50",
                "comment_count": "20"
            }
            await store.store_content(note_data)

            comment_data = {
                "comment_id": "comment_001",
                "note_id": "xhs_test_001",
                "user_id": "user_002",
                "nickname": "Comment User",
                "content": "This is a test comment",
                "like_count": "10"
            }
            await store.store_comment(comment_data)

            creator_data = {
                "user_id": "user_001",
                "nickname": "Test Creator",
                "desc": "This is a test creator",
                "fans": "1000",
                "follows": "100"
            }
            await store.store_creator(creator_data)

            mongo_store = store.mongo_store

            note = await mongo_store.find_one("contents", {"note_id": "xhs_test_001"})
            self.assertIsNotNone(note)
            self.assertEqual(note["title"], "Xiaohongshu Test Note")

            comment = await mongo_store.find_one("comments", {"comment_id": "comment_001"})
            self.assertIsNotNone(comment)
            self.assertEqual(comment["content"], "This is a test comment")

            creator = await mongo_store.find_one("creators", {"user_id": "user_001"})
            self.assertIsNotNone(creator)
            self.assertEqual(creator["nickname"], "Test Creator")

        asyncio.run(test())

    def test_douyin_store_implementation(self):
        async def test():
            store = DouyinMongoStoreImplement()

            video_data = {
                "aweme_id": "dy_test_001",
                "user_id": "user_001",
                "nickname": "Test User",
                "title": "Douyin Test Video",
                "desc": "This is a test video",
                "liked_count": "1000",
                "comment_count": "100"
            }
            await store.store_content(video_data)

            comment_data = {
                "comment_id": "dy_comment_001",
                "aweme_id": "dy_test_001",
                "user_id": "user_002",
                "nickname": "Comment User",
                "content": "This is a test comment"
            }
            await store.store_comment(comment_data)

            creator_data = {
                "user_id": "user_001",
                "nickname": "Test Creator",
                "desc": "This is a test creator"
            }
            await store.store_creator(creator_data)

            mongo_store = store.mongo_store

            video = await mongo_store.find_one("contents", {"aweme_id": "dy_test_001"})
            self.assertIsNotNone(video)
            self.assertEqual(video["title"], "Douyin Test Video")

            comment = await mongo_store.find_one("comments", {"comment_id": "dy_comment_001"})
            self.assertIsNotNone(comment)

            creator = await mongo_store.find_one("creators", {"user_id": "user_001"})
            self.assertIsNotNone(creator)

        asyncio.run(test())

    def test_concurrent_operations(self):
        async def test():
            store = MongoDBStoreBase(collection_prefix="test_xhs")

            tasks = []
            for i in range(10):
                data = {
                    "note_id": f"concurrent_note_{i:03d}",
                    "title": f"Concurrent Test Note {i}",
                    "content": f"Content {i}"
                }
                task = store.save_or_update(
                    "contents",
                    {"note_id": data["note_id"]},
                    data
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            self.assertTrue(all(results))

            for i in range(10):
                found = await store.find_one(
                    "contents",
                    {"note_id": f"concurrent_note_{i:03d}"}
                )
                self.assertIsNotNone(found)

        asyncio.run(test())


def run_integration_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMongoDBRealConnection))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    print("="*70)
    print("MongoDB Storage Integration Test")
    print("="*70)
    print(f"MongoDB Configuration:")
    print(f"  Host: {db_config.MONGODB_HOST}")
    print(f"  Port: {db_config.MONGODB_PORT}")
    print(f"  Database: {db_config.MONGODB_DB_NAME}")
    print("="*70)

    result = run_integration_tests()

    print("\n" + "="*70)
    print("Test Statistics:")
    print(f"Total tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("="*70)

    sys.exit(0 if result.wasSuccessful() else 1)
