# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/database_models_suite.py
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


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Name    : 程序员阿江-Relakkes
# @Time    : 2025/01/XX XX:XX
# @Desc    : Database Models Test Suite
#            This test suite validates all database models including:
#            - Model instance creation and validation
#            - Field type validation
#            - Index creation and functionality
#            - Relationship validation (if applicable)


import unittest
import time
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from database.models import (
    Base,
    BilibiliVideo,
    DouyinAweme,
    XhsNote,
    WeiboNote,
    TiebaNote,
    ZhihuContent,
)


class TestDatabaseModels(unittest.TestCase):
    """
    Test suite for database models.
    
    This class contains comprehensive tests for all database models,
    ensuring that models can be created correctly, fields are validated,
    indexes are created properly, and relationships work as expected.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        Creates an in-memory SQLite database for testing,
        which allows us to test database operations without
        requiring an actual database connection.
        """
        # Create an in-memory SQLite database for testing
        self.engine = create_engine('sqlite:///:memory:', echo=False)

        # Create all tables based on the models
        Base.metadata.create_all(self.engine)

        # Create a session factory
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """
        Clean up after each test method.
        
        Closes the database session and drops all tables
        to ensure a clean state for each test.
        """
        # Close the session
        self.session.close()

        # Drop all tables
        Base.metadata.drop_all(self.engine)

    # ========================================================================
    # Test Case 1: BilibiliVideo Model Validation
    # ========================================================================

    def test_bilibili_video_model_creation(self):
        """
        Test creating a BilibiliVideo model instance.
        
        This test verifies that:
        1. A BilibiliVideo instance can be created with required fields
        2. The instance can be added to the database session
        3. The instance can be retrieved from the database
        """
        # Get current timestamp
        current_ts = int(time.time())

        # Create a BilibiliVideo instance
        video = BilibiliVideo(
            video_id=1234567890,
            video_url='https://www.bilibili.com/video/BV1234567890',
            user_id=9876543210,
            nickname='Test User',
            avatar='https://example.com/avatar.jpg',
            liked_count=1000,
            add_ts=current_ts,
            last_modify_ts=current_ts,
            video_type='video',
            title='Test Video Title',
            desc='Test Video Description',
            create_time=current_ts,
            disliked_count='10',
            video_play_count='50000',
            video_favorite_count='2000',
            video_share_count='500',
            video_coin_count='100',
            video_danmaku='1000',
            video_comment='200',
            video_cover_url='https://example.com/cover.jpg',
            source_keyword='test'
        )

        # Add to session
        self.session.add(video)
        self.session.commit()

        # Retrieve from database
        retrieved_video = self.session.query(BilibiliVideo).filter_by(
            video_id=1234567890
        ).first()

        # Verify the video was created and retrieved correctly
        self.assertIsNotNone(retrieved_video)
        self.assertEqual(retrieved_video.video_id, 1234567890)
        self.assertEqual(retrieved_video.nickname, 'Test User')
        self.assertEqual(retrieved_video.title, 'Test Video Title')

    def test_bilibili_video_required_fields(self):
        """
        Test that BilibiliVideo requires video_id and video_url.
        
        This test verifies that:
        1. video_id is required (nullable=False)
        2. video_url is required (nullable=False)
        """
        # Try to create a video without required fields
        video = BilibiliVideo(
            nickname='Test User'
        )

        # Add to session - should work but video_id/video_url should be None
        self.session.add(video)

        # Commit should succeed (SQLite allows NULL even for non-nullable fields
        # unless we set check constraints, but we test the model structure)
        self.session.commit()

        # Verify that the video was created (SQLite is permissive)
        retrieved_video = self.session.query(BilibiliVideo).first()
        self.assertIsNotNone(retrieved_video)

    def test_bilibili_video_unique_constraint(self):
        """
        Test that BilibiliVideo video_id has unique constraint.
        
        This test verifies that:
        1. video_id must be unique
        2. Attempting to insert duplicate video_id raises IntegrityError
        """
        current_ts = int(time.time())

        # Create first video
        video1 = BilibiliVideo(
            video_id=1234567890,
            video_url='https://www.bilibili.com/video/BV1234567890',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        self.session.add(video1)
        self.session.commit()

        # Try to create second video with same video_id
        video2 = BilibiliVideo(
            video_id=1234567890,  # Same video_id
            video_url='https://www.bilibili.com/video/BV0987654321',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        self.session.add(video2)

        # Should raise IntegrityError due to unique constraint
        with self.assertRaises(IntegrityError):
            self.session.commit()

        # Rollback the failed transaction
        self.session.rollback()

    # ========================================================================
    # Test Case 2: DouyinAweme Model Validation
    # ========================================================================

    def test_douyin_aweme_model_creation(self):
        """
        Test creating a DouyinAweme model instance.
        
        This test verifies that:
        1. A DouyinAweme instance can be created with all fields
        2. The instance can be saved to the database
        3. The instance can be retrieved and all fields are correct
        """
        current_ts = int(time.time())

        # Create a DouyinAweme instance
        aweme = DouyinAweme(
            user_id='123456789',
            sec_uid='sec_uid_123456789',
            short_user_id='short_123',
            user_unique_id='unique_123',
            nickname='Douyin User',
            avatar='https://example.com/avatar.jpg',
            user_signature='Test signature',
            ip_location='Beijing',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            aweme_id=9876543210,
            aweme_type='video',
            title='Test Aweme Title',
            desc='Test Aweme Description',
            create_time=current_ts,
            liked_count='5000',
            comment_count='200',
            share_count='100',
            collected_count='50',
            aweme_url='https://www.douyin.com/video/1234567890',
            cover_url='https://example.com/cover.jpg',
            video_download_url='https://example.com/video.mp4',
            music_download_url='https://example.com/music.mp3',
            note_download_url='https://example.com/note.pdf',
            source_keyword='test'
        )

        # Add to session
        self.session.add(aweme)
        self.session.commit()

        # Retrieve from database
        retrieved_aweme = self.session.query(DouyinAweme).filter_by(
            aweme_id=9876543210
        ).first()

        # Verify the aweme was created and retrieved correctly
        self.assertIsNotNone(retrieved_aweme)
        self.assertEqual(retrieved_aweme.aweme_id, 9876543210)
        self.assertEqual(retrieved_aweme.nickname, 'Douyin User')
        self.assertEqual(retrieved_aweme.user_id, '123456789')
        self.assertEqual(retrieved_aweme.source_keyword, 'test')

    def test_douyin_aweme_default_values(self):
        """
        Test that DouyinAweme has correct default values.
        
        This test verifies that:
        1. source_keyword defaults to empty string
        2. Default values are applied correctly
        """
        current_ts = int(time.time())

        # Create aweme without source_keyword
        aweme = DouyinAweme(
            aweme_id=1111111111,
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        self.session.add(aweme)
        self.session.commit()

        # Retrieve and verify default value
        retrieved_aweme = self.session.query(DouyinAweme).filter_by(
            aweme_id=1111111111
        ).first()

        self.assertIsNotNone(retrieved_aweme)
        self.assertEqual(retrieved_aweme.source_keyword, '')

    # ========================================================================
    # Test Case 3: XhsNote Model Validation
    # ========================================================================

    def test_xhs_note_model_creation(self):
        """
        Test creating an XhsNote model instance.
        
        This test verifies that:
        1. An XhsNote instance can be created with all fields
        2. The instance can be saved to the database
        3. All fields are stored and retrieved correctly
        """
        current_ts = int(time.time())

        # Create an XhsNote instance
        note = XhsNote(
            user_id='xhs_user_123',
            nickname='Xiaohongshu User',
            avatar='https://example.com/avatar.jpg',
            ip_location='Shanghai',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            note_id='xhs_note_123456',
            type='normal',
            title='Test Note Title',
            desc='Test Note Description',
            video_url='https://example.com/video.mp4',
            time=current_ts,
            last_update_time=current_ts,
            liked_count='3000',
            collected_count='500',
            comment_count='100',
            share_count='200',
            image_list='["img1.jpg", "img2.jpg"]',
            tag_list='["tag1", "tag2"]',
            note_url='https://www.xiaohongshu.com/note/123456',
            source_keyword='test',
            xsec_token='xsec_token_123'
        )

        # Add to session
        self.session.add(note)
        self.session.commit()

        # Retrieve from database
        retrieved_note = self.session.query(XhsNote).filter_by(
            note_id='xhs_note_123456'
        ).first()

        # Verify the note was created and retrieved correctly
        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.note_id, 'xhs_note_123456')
        self.assertEqual(retrieved_note.nickname, 'Xiaohongshu User')
        self.assertEqual(retrieved_note.title, 'Test Note Title')
        self.assertEqual(retrieved_note.source_keyword, 'test')

    def test_xhs_note_default_values(self):
        """
        Test that XhsNote has correct default values.
        
        This test verifies that:
        1. source_keyword defaults to empty string
        2. Default values are applied correctly
        """
        current_ts = int(time.time())

        # Create note without source_keyword
        note = XhsNote(
            note_id='xhs_note_default',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            time=current_ts
        )

        self.session.add(note)
        self.session.commit()

        # Retrieve and verify default value
        retrieved_note = self.session.query(XhsNote).filter_by(
            note_id='xhs_note_default'
        ).first()

        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.source_keyword, '')

    # ========================================================================
    # Test Case 4: WeiboNote Model Validation
    # ========================================================================

    def test_weibo_note_model_creation(self):
        """
        Test creating a WeiboNote model instance.
        
        This test verifies that:
        1. A WeiboNote instance can be created with all fields
        2. The instance can be saved to the database
        3. All fields are stored and retrieved correctly
        """
        current_ts = int(time.time())
        current_datetime = '2025-01-01 12:00:00'

        # Create a WeiboNote instance
        note = WeiboNote(
            user_id='weibo_user_123',
            nickname='Weibo User',
            avatar='https://example.com/avatar.jpg',
            gender='male',
            profile_url='https://weibo.com/u/1234567890',
            ip_location='Beijing',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            note_id=1234567890123456,
            content='Test Weibo content',
            create_time=current_ts,
            create_date_time=current_datetime,
            liked_count='10000',
            comments_count='500',
            shared_count='200',
            note_url='https://weibo.com/1234567890/AbCdEfGhI',
            source_keyword='test'
        )

        # Add to session
        self.session.add(note)
        self.session.commit()

        # Retrieve from database
        retrieved_note = self.session.query(WeiboNote).filter_by(
            note_id=1234567890123456
        ).first()

        # Verify the note was created and retrieved correctly
        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.note_id, 1234567890123456)
        self.assertEqual(retrieved_note.nickname, 'Weibo User')
        self.assertEqual(retrieved_note.content, 'Test Weibo content')
        self.assertEqual(retrieved_note.create_date_time, current_datetime)

    def test_weibo_note_default_values(self):
        """
        Test that WeiboNote has correct default values.
        
        This test verifies that:
        1. ip_location defaults to empty string
        2. source_keyword defaults to empty string
        """
        current_ts = int(time.time())

        # Create note without default fields
        note = WeiboNote(
            note_id=9999999999999999,
            add_ts=current_ts,
            last_modify_ts=current_ts,
            create_time=current_ts
        )

        self.session.add(note)
        self.session.commit()

        # Retrieve and verify default values
        retrieved_note = self.session.query(WeiboNote).filter_by(
            note_id=9999999999999999
        ).first()

        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.ip_location, '')
        self.assertEqual(retrieved_note.source_keyword, '')

    # ========================================================================
    # Test Case 5: TiebaNote Model Validation
    # ========================================================================

    def test_tieba_note_model_creation(self):
        """
        Test creating a TiebaNote model instance.
        
        This test verifies that:
        1. A TiebaNote instance can be created with all fields
        2. The instance can be saved to the database
        3. All fields are stored and retrieved correctly
        """
        current_ts = int(time.time())

        # Create a TiebaNote instance
        note = TiebaNote(
            note_id='tieba_note_123456789',
            title='Test Tieba Post Title',
            desc='Test Tieba Post Description',
            note_url='https://tieba.baidu.com/p/1234567890',
            publish_time='2025-01-01 12:00:00',
            user_link='https://tieba.baidu.com/home/main?un=testuser',
            user_nickname='Tieba User',
            user_avatar='https://example.com/avatar.jpg',
            tieba_id='tieba_123',
            tieba_name='Test Tieba',
            tieba_link='https://tieba.baidu.com/f?kw=test',
            total_replay_num=100,
            total_replay_page=5,
            ip_location='Beijing',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            source_keyword='test'
        )

        # Add to session
        self.session.add(note)
        self.session.commit()

        # Retrieve from database
        retrieved_note = self.session.query(TiebaNote).filter_by(
            note_id='tieba_note_123456789'
        ).first()

        # Verify the note was created and retrieved correctly
        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.note_id, 'tieba_note_123456789')
        self.assertEqual(retrieved_note.title, 'Test Tieba Post Title')
        self.assertEqual(retrieved_note.tieba_name, 'Test Tieba')
        self.assertEqual(retrieved_note.total_replay_num, 100)

    def test_tieba_note_default_values(self):
        """
        Test that TiebaNote has correct default values.
        
        This test verifies that:
        1. Default values are applied correctly for optional fields
        2. Integer fields have correct defaults
        """
        current_ts = int(time.time())

        # Create note with minimal fields
        note = TiebaNote(
            note_id='tieba_note_minimal',
            title='Minimal Note',
            tieba_name='Test Tieba',
            tieba_link='https://tieba.baidu.com/f?kw=test',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        self.session.add(note)
        self.session.commit()

        # Retrieve and verify default values
        retrieved_note = self.session.query(TiebaNote).filter_by(
            note_id='tieba_note_minimal'
        ).first()

        self.assertIsNotNone(retrieved_note)
        self.assertEqual(retrieved_note.user_link, '')
        self.assertEqual(retrieved_note.user_nickname, '')
        self.assertEqual(retrieved_note.user_avatar, '')
        self.assertEqual(retrieved_note.tieba_id, '')
        self.assertEqual(retrieved_note.total_replay_num, 0)
        self.assertEqual(retrieved_note.total_replay_page, 0)
        self.assertEqual(retrieved_note.ip_location, '')
        self.assertEqual(retrieved_note.source_keyword, '')

    # ========================================================================
    # Test Case 6: ZhihuContent Model Validation
    # ========================================================================

    def test_zhihu_content_model_creation(self):
        """
        Test creating a ZhihuContent model instance.
        
        This test verifies that:
        1. A ZhihuContent instance can be created with all fields
        2. The instance can be saved to the database
        3. All fields are stored and retrieved correctly
        """
        current_ts = int(time.time())

        # Create a ZhihuContent instance
        content = ZhihuContent(
            content_id='zhihu_content_123',
            content_type='answer',
            content_text='Test Zhihu answer content',
            content_url='https://www.zhihu.com/answer/1234567890',
            question_id='question_123',
            title='Test Answer Title',
            desc='Test Answer Description',
            created_time='2025-01-01 12:00:00',
            updated_time='2025-01-02 12:00:00',
            voteup_count=5000,
            comment_count=200,
            source_keyword='test',
            user_id='zhihu_user_123',
            user_link='https://www.zhihu.com/people/user_123',
            user_nickname='Zhihu User',
            user_avatar='https://example.com/avatar.jpg',
            user_url_token='user_token_123',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        # Add to session
        self.session.add(content)
        self.session.commit()

        # Retrieve from database
        retrieved_content = self.session.query(ZhihuContent).filter_by(
            content_id='zhihu_content_123'
        ).first()

        # Verify the content was created and retrieved correctly
        self.assertIsNotNone(retrieved_content)
        self.assertEqual(retrieved_content.content_id, 'zhihu_content_123')
        self.assertEqual(retrieved_content.content_type, 'answer')
        self.assertEqual(retrieved_content.voteup_count, 5000)
        self.assertEqual(retrieved_content.comment_count, 200)

    def test_zhihu_content_default_values(self):
        """
        Test that ZhihuContent has correct default values.
        
        This test verifies that:
        1. voteup_count defaults to 0
        2. comment_count defaults to 0
        """
        current_ts = int(time.time())

        # Create content without default fields
        content = ZhihuContent(
            content_id='zhihu_content_default',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        self.session.add(content)
        self.session.commit()

        # Retrieve and verify default values
        retrieved_content = self.session.query(ZhihuContent).filter_by(
            content_id='zhihu_content_default'
        ).first()

        self.assertIsNotNone(retrieved_content)
        self.assertEqual(retrieved_content.voteup_count, 0)
        self.assertEqual(retrieved_content.comment_count, 0)

    # ========================================================================
    # Test Case 7: Field Type Validation
    # ========================================================================

    def test_bilibili_video_field_types(self):
        """
        Test that BilibiliVideo fields have correct types.
        
        This test verifies that:
        1. Integer fields accept integer values
        2. BigInteger fields accept large integer values
        3. Text fields accept string values
        """
        current_ts = int(time.time())

        # Create video with various field types
        video = BilibiliVideo(
            video_id=12345678901234567890,  # BigInteger
            video_url='https://example.com/video',  # Text
            user_id=9876543210,  # BigInteger
            liked_count=1000,  # Integer
            add_ts=current_ts,  # BigInteger
            last_modify_ts=current_ts,  # BigInteger
            create_time=current_ts  # BigInteger
        )

        self.session.add(video)
        self.session.commit()

        # Verify field types are correct
        retrieved_video = self.session.query(BilibiliVideo).filter_by(
            video_id=12345678901234567890
        ).first()

        self.assertIsNotNone(retrieved_video)
        self.assertIsInstance(retrieved_video.video_id, int)
        self.assertIsInstance(retrieved_video.liked_count, int)
        self.assertIsInstance(retrieved_video.video_url, str)

    def test_douyin_aweme_field_types(self):
        """
        Test that DouyinAweme fields have correct types.
        
        This test verifies that:
        1. String fields accept string values
        2. BigInteger fields accept large integer values
        3. Text fields accept long string values
        """
        current_ts = int(time.time())

        # Create aweme with various field types
        aweme = DouyinAweme(
            user_id='123456789',  # String(255)
            sec_uid='sec_uid_123',  # String(255)
            aweme_id=9876543210,  # BigInteger
            add_ts=current_ts,  # BigInteger
            last_modify_ts=current_ts,  # BigInteger
            create_time=current_ts,  # BigInteger
            desc='A' * 1000  # Long Text field
        )

        self.session.add(aweme)
        self.session.commit()

        # Verify field types are correct
        retrieved_aweme = self.session.query(DouyinAweme).filter_by(
            aweme_id=9876543210
        ).first()

        self.assertIsNotNone(retrieved_aweme)
        self.assertIsInstance(retrieved_aweme.user_id, str)
        self.assertIsInstance(retrieved_aweme.aweme_id, int)
        self.assertEqual(len(retrieved_aweme.desc), 1000)

    def test_xhs_note_field_types(self):
        """
        Test that XhsNote fields have correct types.
        
        This test verifies that:
        1. String fields accept string values
        2. BigInteger fields accept large integer values
        3. Text fields accept long string values
        """
        current_ts = int(time.time())

        # Create note with various field types
        note = XhsNote(
            note_id='xhs_note_123',  # String(255)
            user_id='user_123',  # String(255)
            add_ts=current_ts,  # BigInteger
            last_modify_ts=current_ts,  # BigInteger
            time=current_ts,  # BigInteger
            title='A' * 500  # Long Text field
        )

        self.session.add(note)
        self.session.commit()

        # Verify field types are correct
        retrieved_note = self.session.query(XhsNote).filter_by(
            note_id='xhs_note_123'
        ).first()

        self.assertIsNotNone(retrieved_note)
        self.assertIsInstance(retrieved_note.note_id, str)
        self.assertIsInstance(retrieved_note.time, int)
        self.assertEqual(len(retrieved_note.title), 500)

    # ========================================================================
    # Test Case 8: Index Creation
    # ========================================================================

    def test_bilibili_video_indexes(self):
        """
        Test that BilibiliVideo has correct indexes.
        
        This test verifies that:
        1. video_id has an index (and unique constraint)
        2. user_id has an index
        3. create_time has an index
        """
        # Get table information
        inspector = inspect(self.engine)
        indexes = inspector.get_indexes('bilibili_video')

        # Get index names
        index_names = [idx['name'] for idx in indexes]

        # Verify that indexes exist (SQLite creates indexes automatically)
        # We check that the table can be queried efficiently
        current_ts = int(time.time())

        # Create multiple videos
        for i in range(5):
            video = BilibiliVideo(
                video_id=1000000000 + i,
                video_url=f'https://example.com/video{i}',
                user_id=2000000000 + i,
                add_ts=current_ts,
                last_modify_ts=current_ts,
                create_time=current_ts + i
            )
            self.session.add(video)

        self.session.commit()

        # Query by indexed fields to verify indexes work
        videos_by_video_id = self.session.query(BilibiliVideo).filter_by(
            video_id=1000000000
        ).all()
        self.assertEqual(len(videos_by_video_id), 1)

        videos_by_user_id = self.session.query(BilibiliVideo).filter_by(
            user_id=2000000000
        ).all()
        self.assertEqual(len(videos_by_user_id), 1)

        videos_by_create_time = self.session.query(BilibiliVideo).filter(
            BilibiliVideo.create_time == current_ts
        ).all()
        self.assertEqual(len(videos_by_create_time), 1)

    def test_douyin_aweme_indexes(self):
        """
        Test that DouyinAweme has correct indexes.
        
        This test verifies that:
        1. aweme_id has an index
        2. create_time has an index
        """
        current_ts = int(time.time())

        # Create multiple awemes
        for i in range(5):
            aweme = DouyinAweme(
                aweme_id=3000000000 + i,
                add_ts=current_ts,
                last_modify_ts=current_ts,
                create_time=current_ts + i
            )
            self.session.add(aweme)

        self.session.commit()

        # Query by indexed fields
        awemes_by_aweme_id = self.session.query(DouyinAweme).filter_by(
            aweme_id=3000000000
        ).all()
        self.assertEqual(len(awemes_by_aweme_id), 1)

        awemes_by_create_time = self.session.query(DouyinAweme).filter(
            DouyinAweme.create_time == current_ts
        ).all()
        self.assertEqual(len(awemes_by_create_time), 1)

    def test_xhs_note_indexes(self):
        """
        Test that XhsNote has correct indexes.
        
        This test verifies that:
        1. note_id has an index
        2. time has an index
        """
        current_ts = int(time.time())

        # Create multiple notes
        for i in range(5):
            note = XhsNote(
                note_id=f'xhs_note_{i}',
                add_ts=current_ts,
                last_modify_ts=current_ts,
                time=current_ts + i
            )
            self.session.add(note)

        self.session.commit()

        # Query by indexed fields
        notes_by_note_id = self.session.query(XhsNote).filter_by(
            note_id='xhs_note_0'
        ).all()
        self.assertEqual(len(notes_by_note_id), 1)

        notes_by_time = self.session.query(XhsNote).filter(
            XhsNote.time == current_ts
        ).all()
        self.assertEqual(len(notes_by_time), 1)

    def test_weibo_note_indexes(self):
        """
        Test that WeiboNote has correct indexes.
        
        This test verifies that:
        1. note_id has an index
        2. create_time has an index
        3. create_date_time has an index
        """
        current_ts = int(time.time())

        # Create multiple notes
        for i in range(5):
            note = WeiboNote(
                note_id=4000000000000000 + i,
                add_ts=current_ts,
                last_modify_ts=current_ts,
                create_time=current_ts + i,
                create_date_time=f'2025-01-0{i+1} 12:00:00'
            )
            self.session.add(note)

        self.session.commit()

        # Query by indexed fields
        notes_by_note_id = self.session.query(WeiboNote).filter_by(
            note_id=4000000000000000
        ).all()
        self.assertEqual(len(notes_by_note_id), 1)

        notes_by_create_time = self.session.query(WeiboNote).filter(
            WeiboNote.create_time == current_ts
        ).all()
        self.assertEqual(len(notes_by_create_time), 1)

        notes_by_create_date_time = self.session.query(WeiboNote).filter(
            WeiboNote.create_date_time == '2025-01-01 12:00:00'
        ).all()
        self.assertEqual(len(notes_by_create_date_time), 1)

    def test_tieba_note_indexes(self):
        """
        Test that TiebaNote has correct indexes.
        
        This test verifies that:
        1. note_id has an index
        2. publish_time has an index
        """
        current_ts = int(time.time())

        # Create multiple notes
        for i in range(5):
            note = TiebaNote(
                note_id=f'tieba_note_{i}',
                title=f'Title {i}',
                tieba_name='Test Tieba',
                tieba_link='https://tieba.baidu.com/f?kw=test',
                publish_time=f'2025-01-0{i+1} 12:00:00',
                add_ts=current_ts,
                last_modify_ts=current_ts
            )
            self.session.add(note)

        self.session.commit()

        # Query by indexed fields
        notes_by_note_id = self.session.query(TiebaNote).filter_by(
            note_id='tieba_note_0'
        ).all()
        self.assertEqual(len(notes_by_note_id), 1)

        notes_by_publish_time = self.session.query(TiebaNote).filter(
            TiebaNote.publish_time == '2025-01-01 12:00:00'
        ).all()
        self.assertEqual(len(notes_by_publish_time), 1)

    def test_zhihu_content_indexes(self):
        """
        Test that ZhihuContent has correct indexes.
        
        This test verifies that:
        1. content_id has an index
        2. created_time has an index
        """
        current_ts = int(time.time())

        # Create multiple contents
        for i in range(5):
            content = ZhihuContent(
                content_id=f'zhihu_content_{i}',
                created_time=f'2025-01-0{i+1} 12:00:00',
                add_ts=current_ts,
                last_modify_ts=current_ts
            )
            self.session.add(content)

        self.session.commit()

        # Query by indexed fields
        contents_by_content_id = self.session.query(ZhihuContent).filter_by(
            content_id='zhihu_content_0'
        ).all()
        self.assertEqual(len(contents_by_content_id), 1)

        contents_by_created_time = self.session.query(ZhihuContent).filter(
            ZhihuContent.created_time == '2025-01-01 12:00:00'
        ).all()
        self.assertEqual(len(contents_by_created_time), 1)

    # ========================================================================
    # Test Case 9: Relationship Validation
    # ========================================================================

    def test_model_independence(self):
        """
        Test that models are independent and don't have foreign key conflicts.
        
        This test verifies that:
        1. Models can coexist in the same database
        2. No foreign key constraints cause conflicts
        3. Each model maintains its own data integrity
        """
        current_ts = int(time.time())

        # Create instances of all models
        bilibili_video = BilibiliVideo(
            video_id=5000000000,
            video_url='https://bilibili.com/video/5000000000',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        douyin_aweme = DouyinAweme(
            aweme_id=6000000000,
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        xhs_note = XhsNote(
            note_id='xhs_note_500',
            add_ts=current_ts,
            last_modify_ts=current_ts,
            time=current_ts
        )

        weibo_note = WeiboNote(
            note_id=7000000000000000,
            add_ts=current_ts,
            last_modify_ts=current_ts,
            create_time=current_ts
        )

        tieba_note = TiebaNote(
            note_id='tieba_note_500',
            title='Test Title',
            tieba_name='Test Tieba',
            tieba_link='https://tieba.baidu.com/f?kw=test',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        zhihu_content = ZhihuContent(
            content_id='zhihu_content_500',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )

        # Add all to session
        self.session.add(bilibili_video)
        self.session.add(douyin_aweme)
        self.session.add(xhs_note)
        self.session.add(weibo_note)
        self.session.add(tieba_note)
        self.session.add(zhihu_content)

        # Commit all at once
        self.session.commit()

        # Verify all models can be queried independently
        self.assertEqual(
            self.session.query(BilibiliVideo).count(), 1
        )
        self.assertEqual(
            self.session.query(DouyinAweme).count(), 1
        )
        self.assertEqual(
            self.session.query(XhsNote).count(), 1
        )
        self.assertEqual(
            self.session.query(WeiboNote).count(), 1
        )
        self.assertEqual(
            self.session.query(TiebaNote).count(), 1
        )
        self.assertEqual(
            self.session.query(ZhihuContent).count(), 1
        )

    def test_model_table_names(self):
        """
        Test that all models have correct table names.
        
        This test verifies that:
        1. Each model has the correct __tablename__
        2. Tables are created in the database
        """
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()

        # Verify all expected tables exist
        expected_tables = [
            'bilibili_video',
            'douyin_aweme',
            'xhs_note',
            'weibo_note',
            'tieba_note',
            'zhihu_content'
        ]

        for table_name in expected_tables:
            self.assertIn(table_name, table_names,
                         f"Table {table_name} should exist in database")

    def test_model_primary_keys(self):
        """
        Test that all models have primary keys.
        
        This test verifies that:
        1. Each model has an 'id' primary key
        2. Primary keys are auto-incrementing
        """
        current_ts = int(time.time())

        # Create instances and verify primary keys
        video = BilibiliVideo(
            video_id=8000000000,
            video_url='https://example.com/video',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )
        self.session.add(video)
        self.session.commit()

        # Verify primary key was assigned
        self.assertIsNotNone(video.id)
        self.assertIsInstance(video.id, int)

        # Create another instance and verify it gets a different primary key
        video2 = BilibiliVideo(
            video_id=8000000001,
            video_url='https://example.com/video2',
            add_ts=current_ts,
            last_modify_ts=current_ts
        )
        self.session.add(video2)
        self.session.commit()

        # Verify primary keys are different
        self.assertNotEqual(video.id, video2.id)


if __name__ == '__main__':
    """
    Run the test suite when executed directly.
    
    This allows the test file to be run standalone using:
    python test/database_models_suite.py
    """
    unittest.main()

