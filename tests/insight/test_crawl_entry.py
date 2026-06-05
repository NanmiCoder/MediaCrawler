# -*- coding: utf-8 -*-
import config  # 上游配置
from insight.crawl_entry import apply_overrides


def test_apply_overrides_sets_max_notes(monkeypatch):
    original = config.CRAWLER_MAX_NOTES_COUNT
    try:
        monkeypatch.setenv("INSIGHT_MAX_NOTES", "33")
        apply_overrides()
        assert config.CRAWLER_MAX_NOTES_COUNT == 33
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = original


def test_apply_overrides_noop_without_env(monkeypatch):
    original = config.CRAWLER_MAX_NOTES_COUNT
    try:
        monkeypatch.delenv("INSIGHT_MAX_NOTES", raising=False)
        apply_overrides()
        assert config.CRAWLER_MAX_NOTES_COUNT == original
    finally:
        config.CRAWLER_MAX_NOTES_COUNT = original
