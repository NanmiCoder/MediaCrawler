# -*- coding: utf-8 -*-
"""
Simple verification script for auto_retry decorator
Run this script to verify:
1. Network exceptions trigger retries
2. Exponential backoff timing (1s, 2s, 4s)
3. Business exceptions do NOT trigger retries
4. Config switch ENABLE_AUTO_RETRY=False disables retries
"""

import asyncio
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import httpx
import config

from tools.retry_decorator import (
    RetryExhaustedError,
    auto_retry,
    is_network_exception,
    NETWORK_RELATED_EXCEPTIONS,
)
from media_platform.xhs.exception import DataFetchError


async def test_1_network_exception_retries():
    """Test 1: Network exception triggers retries"""
    print("\n" + "=" * 60)
    print("Test 1: Network exception triggers retries")
    print("=" * 60)
    
    call_count = 0
    
    @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
    async def test_func():
        nonlocal call_count
        call_count += 1
        print(f"  [Attempt {call_count}] Called, about to raise ReadTimeout...")
        if call_count <= 2:
            raise httpx.ReadTimeout("Simulated timeout error")
        return "success"
    
    result = await test_func()
    print(f"  Result: {result}")
    print(f"  Total calls: {call_count}")
    
    assert call_count == 3, f"Expected 3 calls, got {call_count}"
    print("  ✓ PASSED: Retry mechanism works for network exceptions")


async def test_2_exponential_backoff():
    """Test 2: Exponential backoff timing (1s, 2s, 4s)"""
    print("\n" + "=" * 60)
    print("Test 2: Exponential backoff timing (1s, 2s, 4s)")
    print("=" * 60)
    
    sleep_times = []
    original_sleep = asyncio.sleep
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
        print(f"  [Mock sleep] Sleeping for {delay}s")
    
    asyncio.sleep = mock_sleep
    
    try:
        @auto_retry(max_retries=3, base_delay=1.0, enable_config=False)
        async def test_func():
            raise httpx.ConnectError("Simulated connection error")
        
        try:
            await test_func()
        except RetryExhaustedError as e:
            print(f"  Expected RetryExhaustedError: {e}")
        
        print(f"  Sleep intervals recorded: {sleep_times}")
        assert sleep_times == [1.0, 2.0, 4.0], f"Expected [1.0, 2.0, 4.0], got {sleep_times}"
        print("  ✓ PASSED: Exponential backoff timing is correct (1s, 2s, 4s)")
    finally:
        asyncio.sleep = original_sleep


async def test_3_business_exception_no_retry():
    """Test 3: Business exception does NOT trigger retry"""
    print("\n" + "=" * 60)
    print("Test 3: Business exception (DataFetchError) does NOT trigger retry")
    print("=" * 60)
    
    call_count = 0
    
    @auto_retry(max_retries=3, base_delay=0.1, enable_config=False)
    async def test_func():
        nonlocal call_count
        call_count += 1
        print(f"  [Attempt {call_count}] Called, about to raise DataFetchError...")
        raise DataFetchError("Business logic error: invalid data")
    
    try:
        await test_func()
    except DataFetchError as e:
        print(f"  Expected DataFetchError: {e}")
    
    print(f"  Total calls: {call_count}")
    assert call_count == 1, f"Expected 1 call, got {call_count}"
    print("  ✓ PASSED: Business exceptions do not trigger retries")


async def test_4_config_switch_disabled():
    """Test 4: ENABLE_AUTO_RETRY=False disables retries"""
    print("\n" + "=" * 60)
    print("Test 4: ENABLE_AUTO_RETRY=False disables retries")
    print("=" * 60)
    
    call_count = 0
    original_value = getattr(config, 'ENABLE_AUTO_RETRY', True)
    
    config.ENABLE_AUTO_RETRY = False
    
    try:
        @auto_retry(max_retries=3, base_delay=0.1, enable_config=True)
        async def test_func():
            nonlocal call_count
            call_count += 1
            print(f"  [Attempt {call_count}] Called, about to raise ReadTimeout...")
            raise httpx.ReadTimeout("Simulated timeout error")
        
        try:
            await test_func()
        except httpx.ReadTimeout as e:
            print(f"  Expected ReadTimeout (no retry): {e}")
        
        print(f"  Total calls: {call_count}")
        assert call_count == 1, f"Expected 1 call (no retry), got {call_count}"
        print("  ✓ PASSED: Config switch ENABLE_AUTO_RETRY=False disables retries")
    finally:
        config.ENABLE_AUTO_RETRY = original_value


async def test_5_config_switch_enabled():
    """Test 5: ENABLE_AUTO_RETRY=True enables retries"""
    print("\n" + "=" * 60)
    print("Test 5: ENABLE_AUTO_RETRY=True enables retries")
    print("=" * 60)
    
    call_count = 0
    original_value = getattr(config, 'ENABLE_AUTO_RETRY', True)
    
    config.ENABLE_AUTO_RETRY = True
    
    try:
        @auto_retry(max_retries=3, base_delay=0.1, enable_config=True)
        async def test_func():
            nonlocal call_count
            call_count += 1
            print(f"  [Attempt {call_count}] Called...")
            if call_count <= 2:
                raise httpx.ReadTimeout("Simulated timeout error")
            return "success"
        
        result = await test_func()
        print(f"  Result: {result}")
        print(f"  Total calls: {call_count}")
        assert call_count == 3, f"Expected 3 calls, got {call_count}"
        print("  ✓ PASSED: Config switch ENABLE_AUTO_RETRY=True enables retries")
    finally:
        config.ENABLE_AUTO_RETRY = original_value


def test_sync_function():
    """Test 6: Retry decorator works with sync functions"""
    print("\n" + "=" * 60)
    print("Test 6: Retry decorator works with sync functions")
    print("=" * 60)
    
    call_count = 0
    
    @auto_retry(max_retries=3, base_delay=0.01, enable_config=False)
    def test_func():
        nonlocal call_count
        call_count += 1
        print(f"  [Attempt {call_count}] Called...")
        if call_count <= 2:
            raise httpx.ReadTimeout("Simulated timeout error")
        return "sync success"
    
    result = test_func()
    print(f"  Result: {result}")
    print(f"  Total calls: {call_count}")
    assert call_count == 3, f"Expected 3 calls, got {call_count}"
    print("  ✓ PASSED: Retry decorator works with sync functions")


def test_exception_detection():
    """Test 7: Network exception detection"""
    print("\n" + "=" * 60)
    print("Test 7: Network exception detection")
    print("=" * 60)
    
    network_exceptions = [
        httpx.ConnectError("test"),
        httpx.ReadTimeout("test"),
        httpx.ConnectTimeout("test"),
        httpx.WriteTimeout("test"),
        httpx.PoolTimeout("test"),
        httpx.TimeoutException("test"),
        httpx.NetworkError("test"),
        httpx.TransportError("test"),
        httpx.ProtocolError("test"),
        ConnectionError("test"),
        TimeoutError("test"),
    ]
    
    non_network_exceptions = [
        DataFetchError("business error"),
        ValueError("test"),
        KeyError("test"),
        TypeError("test"),
    ]
    
    print("  Checking network exceptions:")
    for exc in network_exceptions:
        result = is_network_exception(exc)
        print(f"    {exc.__class__.__name__}: is_network_exception = {result}")
        assert result, f"Expected {exc.__class__.__name__} to be detected as network exception"
    
    print("  Checking non-network exceptions:")
    for exc in non_network_exceptions:
        result = is_network_exception(exc)
        print(f"    {exc.__class__.__name__}: is_network_exception = {result}")
        assert not result, f"Expected {exc.__class__.__name__} NOT to be detected as network exception"
    
    print("  ✓ PASSED: Network exception detection is correct")


async def main():
    print("=" * 60)
    print("Auto Retry Decorator Verification")
    print("=" * 60)
    
    test_exception_detection()
    test_sync_function()
    
    await test_1_network_exception_retries()
    await test_2_exponential_backoff()
    await test_3_business_exception_no_retry()
    await test_4_config_switch_disabled()
    await test_5_config_switch_enabled()
    
    print("\n" + "=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ Network exceptions trigger retries (3 times)")
    print("  ✓ Exponential backoff timing: 1s, 2s, 4s")
    print("  ✓ Business exceptions (DataFetchError) do NOT trigger retries")
    print("  ✓ Config switch ENABLE_AUTO_RETRY=False disables retries")
    print("  ✓ Config switch ENABLE_AUTO_RETRY=True enables retries")
    print("  ✓ Works with both sync and async functions")


if __name__ == "__main__":
    asyncio.run(main())
