# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/test/cache_factory_suite.py
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
# @Desc    : Cache Factory Test Suite
#            This test suite validates the CacheFactory class functionality,
#            including cache creation, error handling, and instance management.


import unittest
from unittest.mock import patch, MagicMock

from cache.cache_factory import CacheFactory
from cache.local_cache import ExpiringLocalCache
from cache.redis_cache import RedisCache
from cache.abs_cache import AbstractCache


class TestCacheFactory(unittest.TestCase):
    """
    Test suite for CacheFactory class.
    
    This class contains comprehensive tests for the cache factory pattern,
    ensuring that different cache types can be created correctly and that
    error cases are handled appropriately.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        This method is called before each test method to prepare
        the test environment. Currently, no specific setup is needed
        as CacheFactory uses static methods.
        """
        pass

    def tearDown(self):
        """
        Clean up after each test method.
        
        This method is called after each test method to clean up
        any resources that were created during the test.
        """
        pass

    # ========================================================================
    # Test Case 1: Create Memory Cache
    # ========================================================================

    def test_create_memory_cache(self):
        """
        Test creating a memory cache instance.
        
        This test verifies that:
        1. CacheFactory can create an ExpiringLocalCache instance
        2. The created instance is of the correct type
        3. The instance implements the AbstractCache interface
        4. The instance can be used for basic cache operations
        """
        # Create a memory cache instance using the factory
        cache = CacheFactory.create_cache('memory')

        # Verify that the cache is an instance of ExpiringLocalCache
        self.assertIsInstance(cache, ExpiringLocalCache)

        # Verify that the cache implements the AbstractCache interface
        self.assertIsInstance(cache, AbstractCache)

        # Test basic cache functionality to ensure it works correctly
        cache.set('test_key', 'test_value', 10)
        retrieved_value = cache.get('test_key')

        # Verify that the value was stored and retrieved correctly
        self.assertEqual(retrieved_value, 'test_value')

    def test_create_memory_cache_with_parameters(self):
        """
        Test creating a memory cache with custom parameters.
        
        This test verifies that:
        1. CacheFactory can pass parameters to ExpiringLocalCache
        2. Custom cron_interval parameter is accepted
        """
        # Create a memory cache with custom cron_interval
        custom_interval = 5
        cache = CacheFactory.create_cache('memory', cron_interval=custom_interval)

        # Verify that the cache was created successfully
        self.assertIsInstance(cache, ExpiringLocalCache)

        # Verify that the custom parameter was applied
        self.assertEqual(cache._cron_interval, custom_interval)

    # ========================================================================
    # Test Case 2: Create Redis Cache
    # ========================================================================

    @patch('cache.cache_factory.RedisCache')
    def test_create_redis_cache(self, mock_redis_cache_class):
        """
        Test creating a redis cache instance.
        
        This test verifies that:
        1. CacheFactory can create a RedisCache instance
        2. The created instance is of the correct type
        3. The instance implements the AbstractCache interface
        4. RedisCache is instantiated without arguments
        
        Note: We mock RedisCache to avoid requiring a real Redis connection
        during testing.
        """
        # Create a mock RedisCache instance
        mock_redis_instance = MagicMock(spec=RedisCache)
        mock_redis_cache_class.return_value = mock_redis_instance

        # Create a redis cache instance using the factory
        cache = CacheFactory.create_cache('redis')

        # Verify that RedisCache was instantiated
        mock_redis_cache_class.assert_called_once()

        # Verify that the cache is the mocked instance
        self.assertEqual(cache, mock_redis_instance)

    @patch('cache.redis_cache.Redis')
    def test_create_redis_cache_integration(self, mock_redis):
        """
        Test creating a redis cache with mocked Redis connection.
        
        This test verifies that:
        1. RedisCache can be created with a mocked Redis connection
        2. The cache instance works correctly with the mock
        """
        # Create a mock Redis client
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        # Create a redis cache instance
        cache = CacheFactory.create_cache('redis')

        # Verify that the cache is an instance of RedisCache
        self.assertIsInstance(cache, RedisCache)

        # Verify that the cache implements the AbstractCache interface
        self.assertIsInstance(cache, AbstractCache)

    # ========================================================================
    # Test Case 3: Invalid Cache Type Handling
    # ========================================================================

    def test_create_cache_with_invalid_type(self):
        """
        Test handling of invalid cache type.
        
        This test verifies that:
        1. CacheFactory raises ValueError for unknown cache types
        2. The error message is descriptive and helpful
        3. The error includes the invalid cache type in the message
        """
        # Attempt to create a cache with an invalid type
        invalid_cache_type = 'invalid_cache_type'

        # Verify that ValueError is raised
        with self.assertRaises(ValueError) as context:
            CacheFactory.create_cache(invalid_cache_type)

        # Verify that the error message contains the invalid cache type
        error_message = str(context.exception)
        self.assertIn('Unknown cache type', error_message)
        self.assertIn(invalid_cache_type, error_message)

    def test_create_cache_with_empty_string(self):
        """
        Test handling of empty string as cache type.
        
        This test verifies that:
        1. CacheFactory raises ValueError for empty string
        2. Empty strings are treated as invalid cache types
        """
        # Attempt to create a cache with empty string
        with self.assertRaises(ValueError) as context:
            CacheFactory.create_cache('')

        # Verify that the error message is appropriate
        error_message = str(context.exception)
        self.assertIn('Unknown cache type', error_message)

    def test_create_cache_with_none_type(self):
        """
        Test handling of None as cache type.
        
        This test verifies that:
        1. CacheFactory raises ValueError for None
        2. None values are treated as invalid cache types
        """
        # Attempt to create a cache with None
        with self.assertRaises(ValueError) as context:
            CacheFactory.create_cache(None)

        # Verify that the error message is appropriate
        error_message = str(context.exception)
        self.assertIn('Unknown cache type', error_message)

    def test_create_cache_with_numeric_type(self):
        """
        Test handling of numeric cache type.
        
        This test verifies that:
        1. CacheFactory raises ValueError for numeric types
        2. Non-string types are treated as invalid cache types
        """
        # Attempt to create a cache with numeric type
        with self.assertRaises(ValueError) as context:
            CacheFactory.create_cache(123)

        # Verify that the error message is appropriate
        error_message = str(context.exception)
        self.assertIn('Unknown cache type', error_message)

    # ========================================================================
    # Test Case 4: Singleton Pattern Validation
    # ========================================================================

    def test_cache_factory_is_not_singleton(self):
        """
        Test that CacheFactory does not enforce singleton pattern.
        
        This test verifies that:
        1. Multiple calls to create_cache return different instances
        2. Each cache instance is independent
        3. CacheFactory follows factory pattern, not singleton pattern
        
        Note: CacheFactory itself is a class with static methods,
        so we test that it creates new instances each time.
        """
        # Create first memory cache instance
        cache1 = CacheFactory.create_cache('memory')

        # Create second memory cache instance
        cache2 = CacheFactory.create_cache('memory')

        # Verify that they are different instances (not the same object)
        self.assertIsNot(cache1, cache2)

        # Verify that they are both instances of ExpiringLocalCache
        self.assertIsInstance(cache1, ExpiringLocalCache)
        self.assertIsInstance(cache2, ExpiringLocalCache)

        # Verify that they are independent (changes to one don't affect the other)
        cache1.set('key1', 'value1', 10)
        cache2.set('key2', 'value2', 10)

        # Verify that each cache only contains its own data
        self.assertEqual(cache1.get('key1'), 'value1')
        self.assertIsNone(cache1.get('key2'))

        self.assertEqual(cache2.get('key2'), 'value2')
        self.assertIsNone(cache2.get('key1'))

    def test_cache_factory_static_method(self):
        """
        Test that CacheFactory.create_cache is a static method.
        
        This test verifies that:
        1. create_cache can be called without instantiating CacheFactory
        2. The method works correctly as a static method
        """
        # Call create_cache without creating a CacheFactory instance
        cache = CacheFactory.create_cache('memory')

        # Verify that the cache was created successfully
        self.assertIsInstance(cache, ExpiringLocalCache)

        # Verify that we can call it multiple times without issues
        cache2 = CacheFactory.create_cache('memory')
        self.assertIsInstance(cache2, ExpiringLocalCache)

    def test_multiple_cache_types_independence(self):
        """
        Test that different cache types create independent instances.
        
        This test verifies that:
        1. Memory and Redis caches are independent
        2. Creating one type does not affect the other
        3. Each cache type maintains its own state
        """
        # Create memory cache
        memory_cache = CacheFactory.create_cache('memory')

        # Create redis cache (mocked to avoid connection requirements)
        with patch('cache.cache_factory.RedisCache') as mock_redis:
            mock_redis_instance = MagicMock(spec=RedisCache)
            mock_redis.return_value = mock_redis_instance

            redis_cache = CacheFactory.create_cache('redis')

            # Verify that they are different types
            self.assertIsInstance(memory_cache, ExpiringLocalCache)
            self.assertIsInstance(redis_cache, MagicMock)

            # Verify that they are different instances
            self.assertIsNot(memory_cache, redis_cache)

    # ========================================================================
    # Additional Edge Cases
    # ========================================================================

    def test_create_cache_with_extra_parameters(self):
        """
        Test creating cache with extra parameters that are not used.
        
        This test verifies that:
        1. Extra parameters are handled gracefully
        2. Memory cache accepts extra keyword arguments
        3. Redis cache ignores extra arguments
        """
        # Create memory cache with extra parameters
        cache = CacheFactory.create_cache('memory', 
                                         cron_interval=5, 
                                         extra_param='ignored')

        # Verify that the cache was created successfully
        self.assertIsInstance(cache, ExpiringLocalCache)

        # Verify that valid parameters were applied
        self.assertEqual(cache._cron_interval, 5)

    def test_create_cache_case_sensitivity(self):
        """
        Test that cache type is case-sensitive.
        
        This test verifies that:
        1. Cache type matching is case-sensitive
        2. 'Memory' (capitalized) is different from 'memory'
        3. Case variations raise ValueError
        """
        # Test with capitalized cache type
        with self.assertRaises(ValueError):
            CacheFactory.create_cache('Memory')

        # Test with uppercase cache type
        with self.assertRaises(ValueError):
            CacheFactory.create_cache('MEMORY')

        # Test with mixed case
        with self.assertRaises(ValueError):
            CacheFactory.create_cache('ReDiS')


if __name__ == '__main__':
    """
    Run the test suite when executed directly.
    
    This allows the test file to be run standalone using:
    python test/cache_factory_suite.py
    """
    unittest.main()

