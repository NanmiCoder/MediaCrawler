"""Repository-wide pytest layer and external-service policy."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _relative_test_path(config: pytest.Config, item: pytest.Item) -> str:
    root = Path(str(config.rootpath)).resolve()
    path = Path(str(item.path)).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Assign repository layers and skip opt-in external tests by default."""
    run_external = (
        os.getenv("MEDIACRAWLER_RUN_EXTERNAL_TESTS", "").lower() in _TRUE_VALUES
    )
    external_skip = pytest.mark.skip(
        reason=(
            "external integration test; set "
            "MEDIACRAWLER_RUN_EXTERNAL_TESTS=1 to run"
        )
    )

    for item in items:
        relative_path = _relative_test_path(config, item)
        if relative_path == "api/tests.py" or relative_path.startswith(
            "douyin_scraper/tests/"
        ):
            item.add_marker(pytest.mark.core)
        elif relative_path.startswith(("tests/", "test/")):
            item.add_marker(pytest.mark.legacy)

        if "external" in item.keywords and not run_external:
            item.add_marker(external_skip)
