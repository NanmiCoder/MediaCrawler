import pytest

from pathlib import Path

from api.tasks import TaskManager


def _selected_result(tmp_path: Path, task_type: str, files: tuple[str, ...]):
    manager = TaskManager(base_dir=str(tmp_path))
    task = manager.create_task(task_type)
    task.status = "completed"
    outputs = Path(task.workspace) / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    for name in files:
        (outputs / name).write_text("value\n", encoding="utf-8")
    return manager.get_result_path(task.task_id)


@pytest.mark.parametrize("task_type", ["search", "run_all"])
def test_search_selector_prefers_standard_csv(tmp_path: Path, task_type: str) -> None:
    result = _selected_result(tmp_path, task_type, ("search_result.jsonl", "search_result.csv"))
    assert result is not None
    assert result.name == "search_result.csv"


def test_fallback_selector_uses_supported_file(tmp_path: Path) -> None:
    result = _selected_result(tmp_path, "custom", ("fallback.csv",))
    assert result is not None
    assert result.name == "fallback.csv"
