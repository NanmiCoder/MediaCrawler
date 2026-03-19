import json
import os
import aiofiles
from tools import utils

class CheckpointManager:
    def __init__(self, checkpoint_dir="data/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)
            
    def _get_file_path(self, platform: str) -> str:
        return os.path.join(self.checkpoint_dir, f"{platform}_search_checkpoint.json")

    async def get_max_page(self, platform: str, keyword: str) -> int:
        file_path = self._get_file_path(platform)
        if not os.path.exists(file_path):
            return 0
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                return data.get(keyword, 0)
        except Exception as e:
            utils.logger.error(f"[CheckpointManager.get_max_page] failed: {e}")
            return 0
            
    async def save_max_page(self, platform: str, keyword: str, page: int):
        file_path = self._get_file_path(platform)
        data = {}
        if os.path.exists(file_path):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = json.loads(content)
            except Exception:
                pass
        
        data[keyword] = page
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            utils.logger.error(f"[CheckpointManager.save_max_page] failed: {e}")

checkpoint_manager = CheckpointManager()
