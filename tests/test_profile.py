# -*- coding: utf-8 -*-

import config
from tools.profile import get_browser_profile_dir


def test_get_browser_profile_dir_uses_explicit_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "BROWSER_PROFILE_DIR", "data/profiles/inst-a")

    assert get_browser_profile_dir() == str(tmp_path / "data" / "profiles" / "inst-a")


def test_get_browser_profile_dir_uses_platform_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "BROWSER_PROFILE_DIR", "")
    monkeypatch.setattr(config, "PLATFORM", "xhs")

    assert get_browser_profile_dir() == str(tmp_path / "browser_data" / "xhs_user_data_dir")
    assert get_browser_profile_dir(cdp=True) == str(tmp_path / "browser_data" / "cdp_xhs_user_data_dir")
