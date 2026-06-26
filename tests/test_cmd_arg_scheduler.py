# -*- coding: utf-8 -*-

import pytest

import config
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_cmd_arg_sets_scheduler_runtime_fields():
    original = {
        "CRAWLER_TYPE": config.CRAWLER_TYPE,
        "INSTANCE_ID": config.INSTANCE_ID,
        "BROWSER_PROFILE_DIR": config.BROWSER_PROFILE_DIR,
        "CDP_DEBUG_PORT": config.CDP_DEBUG_PORT,
        "CDP_CONNECT_EXISTING": config.CDP_CONNECT_EXISTING,
        "CONTENT_FILTERS": config.CONTENT_FILTERS,
    }

    try:
        result = await parse_cmd(
            [
                "--platform",
                "xhs",
                "--type",
                "login",
                "--instance_id",
                "inst-a",
                "--browser_profile_dir",
                "data/scheduler/profiles/inst-a",
                "--cdp_debug_port",
                "9233",
                "--cdp_connect_existing",
                "false",
                "--content_filters",
                '{"liked_count":{"min":1000}}',
            ]
        )

        assert result.type == "login"
        assert result.content_filters == {"liked_count": {"min": 1000.0}}
        assert config.INSTANCE_ID == "inst-a"
        assert config.BROWSER_PROFILE_DIR == "data/scheduler/profiles/inst-a"
        assert config.CDP_DEBUG_PORT == 9233
        assert config.CDP_CONNECT_EXISTING is False
        assert config.CONTENT_FILTERS == {"liked_count": {"min": 1000.0}}
    finally:
        for key, value in original.items():
            setattr(config, key, value)
