"""
douyin_scraper.state — 状态管理
=================================
v5 重构：从 v4 的 common_utils 中拆出状态管理逻辑。
三态转换：pending → in_progress → completed / failed

我实际执行时踩过的坑：
  - 状态文件损坏导致全部步骤跳过 → 损坏时重置为空
  - 步骤开始前没有状态标记 → 崩溃后不知道是否已经开始
  - 步骤失败后状态不记录 → 重新运行时盲目重试
  - 重置步骤时忘了清除去重索引 → 数据被跳过
  - 全局变量存储状态路径 → 无法并行测试
  - 非原子写入导致状态文件损坏 → 原子写入（临时文件+os.replace）
  - 每次标记去重都读写文件导致 I/O 风暴 → 内存缓存+批量写入
"""

import hashlib
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

logger = logging.getLogger("douyin_scraper")

# 中国时区
_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def atomic_write_json(filepath: Path, data: dict) -> None:
    """
    原子写入 JSON 文件：先写临时文件，再 os.replace 替换原文件。
    防止写入过程中崩溃导致文件损坏。

    Args:
        filepath: 目标 JSON 文件路径
        data: 要写入的字典数据
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(filepath.parent),
        prefix=filepath.stem + ".tmp",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, str(filepath))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class StateManager:
    """
    状态管理器。

    管理三个状态文件：
    - task_state.json: 步骤完成状态
    - dedupe_index.json: 去重索引
    - execution_log.jsonl: 结构化日志

    v5 改进：不再使用模块级全局变量存储路径，
    通过实例属性管理，方便测试时注入临时目录。

    安全改进：
    - 原子写入：所有 JSON 文件通过 atomic_write_json 写入
    - 去重缓存：内存缓存 + 脏标记 + 批量写入，减少 I/O
    """

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._task_state_path = state_dir / "task_state.json"
        self._dedupe_path = state_dir / "dedupe_index.json"
        self._log_path = state_dir / "execution_log.jsonl"

        # 线程锁：保护所有 task_state 的 read-modify-write 操作
        self._state_lock = threading.Lock()

        # task_state 内存缓存：避免每次 get_step_status 都读磁盘
        self._task_state_cache: Optional[dict] = None

        # 去重索引内存缓存：index_name -> Set[item_id]
        self._dedupe_cache: Dict[str, Set[str]] = {}
        # 脏标记：记录哪些 index_name 被修改过但尚未写盘
        self._dedupe_dirty: Set[str] = set()
        # 是否已从文件加载过缓存
        self._dedupe_loaded: bool = False

    def __del__(self) -> None:
        """析构时确保脏去重索引写盘"""
        try:
            self.flush_dedupe()
        except Exception:
            pass

    def _ensure_dedupe_loaded(self) -> None:
        """懒加载去重索引到内存缓存"""
        if self._dedupe_loaded:
            return
        self._dedupe_loaded = True
        data = self._load_all_dedupe_from_disk()
        for index_name, ids in data.items():
            self._dedupe_cache[index_name] = set(ids)

    # ═══════════════════════════════════════════════════════════════
    # task_state.json 管理
    # ═══════════════════════════════════════════════════════════════

    def load_task_state(self) -> dict:
        """加载任务状态文件（从磁盘加载到缓存）"""
        with self._state_lock:
            if self._task_state_path.exists():
                try:
                    with open(self._task_state_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._task_state_cache = data
                    return data
                except (json.JSONDecodeError, OSError):
                    logger.warning("task_state.json 损坏，重置为空")
                    data = {"steps": {}, "metadata": {}}
                    self._task_state_cache = data
                    return data
            data = {"steps": {}, "metadata": {}}
            self._task_state_cache = data
            return data

    def _get_cached_state(self) -> dict:
        """获取缓存的状态，若缓存为空则从磁盘加载（调用方必须已持有 _state_lock）"""
        if self._task_state_cache is not None:
            return self._task_state_cache
        # 直接加载，不经过 load_task_state（避免嵌套获取 _state_lock 导致死锁）
        if self._task_state_path.exists():
            try:
                with open(self._task_state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._task_state_cache = data
                return data
            except (json.JSONDecodeError, OSError):
                logger.warning("task_state.json 损坏，重置为空")
                data = {"steps": {}, "metadata": {}}
                self._task_state_cache = data
                return data
        data = {"steps": {}, "metadata": {}}
        self._task_state_cache = data
        return data

    def save_task_state(self, state: dict) -> None:
        """保存任务状态文件（原子写入 + 更新缓存）"""
        with self._state_lock:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._task_state_path, state)
            self._task_state_cache = state

    def get_step_status(self, step_name: str) -> str:
        """获取步骤状态：从内存缓存读取，无磁盘 I/O"""
        with self._state_lock:
            state = self._get_cached_state()
            return state.get("steps", {}).get(step_name, {}).get("status", "pending")

    def get_step_info(self, step_name: str) -> dict:
        """获取步骤的详细信息（从缓存读取）"""
        with self._state_lock:
            state = self._get_cached_state()
            return state.get("steps", {}).get(step_name, {})

    def mark_step_started(self, step_name: str) -> None:
        """标记步骤开始（in_progress），线程安全"""
        with self._state_lock:
            state = self._get_cached_state()
            state.setdefault("steps", {})[step_name] = {
                "status": "in_progress",
                "started_at": _now_iso(),
            }
            self.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._task_state_path, state)
            self._task_state_cache = state
        logger.info("[%s] 步骤开始", step_name)

    def mark_step_completed(self, step_name: str, detail: str = "") -> None:
        """标记步骤完成，线程安全"""
        with self._state_lock:
            state = self._get_cached_state()
            entry: Dict[str, Any] = {
                "status": "completed",
                "completed_at": _now_iso(),
            }
            if detail:
                entry["detail"] = detail
            state.setdefault("steps", {})[step_name] = entry
            self.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._task_state_path, state)
            self._task_state_cache = state
        logger.info("[%s] 步骤完成: %s", step_name, detail)

    def mark_step_failed(
        self,
        step_name: str,
        error_summary: str = "",
        exit_code: int = 1,
    ) -> None:
        """
        标记步骤失败，线程安全。

        Args:
            step_name: 步骤名称
            error_summary: 错误摘要（前 200 字符）
            exit_code: 退出码（1=可重试, 2=不可重试, 3=致命）
        """
        with self._state_lock:
            state = self._get_cached_state()
            state.setdefault("steps", {})[step_name] = {
                "status": "failed",
                "failed_at": _now_iso(),
                "error_summary": error_summary[:200],
                "exit_code": exit_code,
            }
            self.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._task_state_path, state)
            self._task_state_cache = state
        logger.error(
            "[%s] 步骤失败 (exit_code=%d): %s",
            step_name, exit_code, error_summary[:200],
        )

    def is_step_completed(self, step_name: str) -> bool:
        return self.get_step_status(step_name) == "completed"

    def is_step_failed(self, step_name: str) -> bool:
        return self.get_step_status(step_name) == "failed"

    def check_step_ready(self, step_name: str) -> bool:
        """
        检查步骤是否可以执行。
        completed → 不执行，failed → 不执行（需手动修复）。
        """
        status = self.get_step_status(step_name)
        if status == "completed":
            logger.info("[%s] 步骤已完成，跳过", step_name)
            return False
        if status == "in_progress":
            logger.warning("[%s] 上次可能中断，继续执行", step_name)
            return True
        if status == "failed":
            logger.warning("[%s] 上次失败，需修复后 reset_step()", step_name)
            return False
        return True  # pending

    def reset_step(self, step_name: str, clear_dedupe: bool = False) -> None:
        """
        重置步骤状态为 pending，线程安全。
        """
        with self._state_lock:
            state = self._get_cached_state()
            if step_name in state.get("steps", {}):
                del state["steps"][step_name]
                self.state_dir.mkdir(parents=True, exist_ok=True)
                atomic_write_json(self._task_state_path, state)
                self._task_state_cache = state

        if clear_dedupe:
            self._ensure_dedupe_loaded()
            if step_name in self._dedupe_cache:
                del self._dedupe_cache[step_name]
                self._dedupe_dirty.discard(step_name)
            # 同步写盘
            data = {k: sorted(list(v)) for k, v in self._dedupe_cache.items()}
            self._save_all_dedupe_to_disk(data)

        logger.info("[%s] 步骤状态已重置 (clear_dedupe=%s)", step_name, clear_dedupe)

    def reset_all(self) -> None:
        """重置所有状态，线程安全"""
        with self._state_lock:
            for path in [self._task_state_path, self._dedupe_path]:
                if path.exists():
                    path.unlink()
            # 清空内存缓存
            self._task_state_cache = None
            self._dedupe_cache.clear()
            self._dedupe_dirty.clear()
            self._dedupe_loaded = False
        logger.info("所有状态文件已重置")

    # ═══════════════════════════════════════════════════════════════
    # dedupe_index.json 管理（内存缓存 + 批量写入）
    # ═══════════════════════════════════════════════════════════════

    def _load_all_dedupe_from_disk(self) -> dict:
        """从磁盘读取去重索引 JSON"""
        if self._dedupe_path.exists():
            try:
                with open(self._dedupe_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                if isinstance(e, OSError):
                    logger.error("去重索引加载失败: %s, 视为无已处理记录", e)
                return {}
        return {}

    def _save_all_dedupe_to_disk(self, data: dict) -> None:
        """将去重索引写入磁盘（原子写入）"""
        atomic_write_json(self._dedupe_path, data)

    def _load_all_dedupe(self) -> dict:
        """加载去重索引（兼容旧接口，从内存缓存返回）"""
        self._ensure_dedupe_loaded()
        return {k: sorted(list(v)) for k, v in self._dedupe_cache.items()}

    def _save_all_dedupe(self, data: dict) -> None:
        """保存去重索引（兼容旧接口，同步内存缓存并写盘）"""
        for index_name, ids in data.items():
            self._dedupe_cache[index_name] = set(ids)
        self._dedupe_dirty.clear()
        self._save_all_dedupe_to_disk(data)

    def is_duplicate(self, index_name: str, item_id: str) -> bool:
        """检查是否已写入（从内存缓存读取，无 I/O）"""
        self._ensure_dedupe_loaded()
        return str(item_id) in self._dedupe_cache.get(index_name, set())

    def is_written(self, index_name: str, item_id: str) -> bool:
        """is_duplicate 的别名，语义更清晰"""
        return self.is_duplicate(index_name, item_id)

    def mark_written(self, index_name: str, item_id: str) -> None:
        """
        标记已写入（只修改内存缓存，标记脏，不立即写盘）。
        调用 flush_dedupe() 批量写盘。
        """
        self._ensure_dedupe_loaded()
        item_id_str = str(item_id)
        if index_name not in self._dedupe_cache:
            self._dedupe_cache[index_name] = set()
        self._dedupe_cache[index_name].add(item_id_str)
        self._dedupe_dirty.add(index_name)

    def flush_dedupe(self) -> None:
        """
        将脏的去重索引批量写入磁盘（原子写入）。
        通常在步骤完成或对象析构时调用。
        """
        if not self._dedupe_dirty:
            return
        self._ensure_dedupe_loaded()
        data = {k: sorted(list(v)) for k, v in self._dedupe_cache.items()}
        try:
            self._save_all_dedupe_to_disk(data)
            self._dedupe_dirty.clear()
            logger.debug("去重索引已刷新到磁盘")
        except Exception as e:
            logger.error("去重索引刷新失败: %s", e)
            raise

    def load_completed_ids_from_jsonl(
        self, filepath: Path, id_field: str = "aweme_id"
    ) -> Set[str]:
        """
        从已有 JSONL 输出文件中读取已完成的 ID 集合。
        ★ 断点续传的核心 ★

        我实际执行时：脚本崩溃后，唯一的恢复方式就是读取输出文件。
        v5：空文件、损坏行的容错处理。
        """
        done: Set[str] = set()
        if not filepath.exists():
            return done
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        d = json.loads(line)
                        aid = str(d.get(id_field, ""))
                        if aid:
                            done.add(aid)
                    except json.JSONDecodeError:
                        logger.warning(
                            "JSONL 损坏行已跳过: %s 行号 %d",
                            filepath, line_num,
                        )
                        continue
        except OSError:
            pass
        return done

    @staticmethod
    def generate_pseudo_id(
        line_num: int, record: dict, prefix: str = "unknown"
    ) -> str:
        """
        当幂等键缺失时，生成确定性伪 ID。

        我实际执行时：有少数记录的 aweme_id 为空，导致去重失败和数据丢失。
        v5：空幂等键 → 生成 `unknown_<行号>_<内容哈希前8位>` 的确定性 ID。
        """
        content = json.dumps(record, sort_keys=True, ensure_ascii=False)
        hash_hex = hashlib.md5(content.encode("utf-8")).hexdigest()[:8]
        pseudo_id = f"{prefix}_{line_num}_{hash_hex}"
        logger.warning("幂等键缺失，生成伪 ID: %s", pseudo_id)
        return pseudo_id

    # ═══════════════════════════════════════════════════════════════
    # execution_log.jsonl
    # ═══════════════════════════════════════════════════════════════

    def write_log(
        self, level: str, step: str, action: str, msg: str, **kwargs: Any
    ) -> None:
        """写入结构化 JSON Lines 日志"""
        entry = {
            "ts": _now_iso(),
            "level": level,
            "step": step,
            "action": action,
            "msg": msg,
            **kwargs,
        }
        line = json.dumps(entry, ensure_ascii=False)
        # 使用 os.open 绕过 Windows asyncio 问题
        import os as _os
        flags = _os.O_WRONLY | _os.O_APPEND | _os.O_CREAT
        try:
            fd = _os.open(str(self._log_path), flags, 0o644)
            try:
                _os.write(fd, (line + "\n").encode("utf-8"))
            finally:
                _os.close(fd)
        except OSError as e:
            # JSONL 文件写入失败时，降级到 Python logging（写 stderr）
            _log = logging.getLogger(__name__)
            _log.warning("JSONL 日志写入失败: %s", e)

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有步骤状态摘要"""
        state = self.load_task_state()
        result: Dict[str, Any] = {}
        for step_name, info in state.get("steps", {}).items():
            result[step_name] = {
                "status": info.get("status", "pending"),
                "detail": info.get("detail", ""),
                "error_summary": info.get("error_summary", ""),
                "exit_code": info.get("exit_code", 0),
            }
        return result
