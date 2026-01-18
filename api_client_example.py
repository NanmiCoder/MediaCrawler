"""
MediaCrawler API 客户端示例
演示如何通过 API 采集抖音、小红书、知乎数据
"""
import requests
import time
import json
from typing import Dict, List, Optional

class MediaCrawlerClient:
    """MediaCrawler API 客户端"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url

    def get_platforms(self) -> Dict:
        """获取支持的平台列表"""
        response = requests.get(f"{self.base_url}/api/platforms")
        return response.json()

    def search(
        self,
        platform: str,
        keyword: str,
        max_count: int = 10,
        enable_comments: bool = True,
        enable_media: bool = False
    ) -> str:
        """
        创建搜索任务

        Args:
            platform: 平台代码 (dy/xhs/zhihu)
            keyword: 搜索关键词
            max_count: 最大采集数量
            enable_comments: 是否采集评论
            enable_media: 是否下载媒体文件

        Returns:
            task_id: 任务ID
        """
        response = requests.post(
            f"{self.base_url}/api/search",
            json={
                "platform": platform,
                "keyword": keyword,
                "max_count": max_count,
                "enable_comments": enable_comments,
                "enable_media": enable_media
            }
        )
        response.raise_for_status()
        return response.json()["task_id"]

    def get_task_status(self, task_id: str) -> Dict:
        """查询任务状态"""
        response = requests.get(f"{self.base_url}/api/task/{task_id}")
        response.raise_for_status()
        return response.json()

    def get_task_result(self, task_id: str) -> Dict:
        """获取任务结果"""
        response = requests.get(f"{self.base_url}/api/task/{task_id}/result")
        response.raise_for_status()
        return response.json()

    def wait_for_task(
        self,
        task_id: str,
        check_interval: int = 5,
        timeout: int = 600,
        callback=None
    ) -> Dict:
        """
        等待任务完成

        Args:
            task_id: 任务ID
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
            callback: 状态回调函数

        Returns:
            任务结果
        """
        start_time = time.time()

        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                raise TimeoutError(f"任务 {task_id} 超时")

            # 查询状态
            status = self.get_task_status(task_id)

            # 回调
            if callback:
                callback(status)

            # 检查状态
            if status["status"] == "completed":
                return self.get_task_result(task_id)
            elif status["status"] == "failed":
                raise Exception(f"任务失败: {status.get('error')}")

            # 等待
            time.sleep(check_interval)

    def search_and_wait(
        self,
        platform: str,
        keyword: str,
        max_count: int = 10,
        enable_comments: bool = True,
        enable_media: bool = False,
        verbose: bool = True
    ) -> Dict:
        """
        搜索并等待结果（便捷方法）

        Args:
            platform: 平台代码
            keyword: 搜索关键词
            max_count: 最大采集数量
            enable_comments: 是否采集评论
            enable_media: 是否下载媒体文件
            verbose: 是否显示进度

        Returns:
            采集结果
        """
        if verbose:
            print(f"📡 创建任务: {platform} - {keyword}")

        # 创建任务
        task_id = self.search(
            platform=platform,
            keyword=keyword,
            max_count=max_count,
            enable_comments=enable_comments,
            enable_media=enable_media
        )

        if verbose:
            print(f"✅ 任务ID: {task_id}")
            print(f"⏳ 等待任务完成...")

        # 等待完成
        def status_callback(status):
            if verbose and status.get("progress"):
                print(f"   {status['progress']}")

        result = self.wait_for_task(task_id, callback=status_callback)

        if verbose:
            print(f"🎉 任务完成！")
            if result.get("data"):
                print(f"📊 采集到 {result['data'].get('total', 0)} 条数据")

        return result

    def list_tasks(self) -> List[Dict]:
        """获取所有任务列表"""
        response = requests.get(f"{self.base_url}/api/tasks")
        response.raise_for_status()
        return response.json()["tasks"]


# ==================== 使用示例 ====================

def example_douyin():
    """示例：采集抖音数据"""
    print("=" * 80)
    print("示例 1: 采集抖音数据")
    print("=" * 80)

    client = MediaCrawlerClient()

    # 搜索并等待结果
    result = client.search_and_wait(
        platform="dy",
        keyword="美食教程",
        max_count=5,
        enable_comments=True,
        enable_media=False
    )

    # 显示结果
    print("\n📝 结果预览:")
    for i, item in enumerate(result["data"]["items"][:3], 1):
        print(f"\n{i}. {item.get('title', item.get('desc', 'N/A'))}")
        print(f"   作者: {item.get('nickname', 'N/A')}")
        print(f"   点赞: {item.get('liked_count', 'N/A')}")
        print(f"   链接: {item.get('aweme_url', item.get('video_url', 'N/A'))}")


def example_xiaohongshu():
    """示例：采集小红书数据"""
    print("\n" + "=" * 80)
    print("示例 2: 采集小红书数据")
    print("=" * 80)

    client = MediaCrawlerClient()

    result = client.search_and_wait(
        platform="xhs",
        keyword="美妆教程",
        max_count=5,
        enable_comments=True,
        enable_media=False
    )

    print("\n📝 结果预览:")
    for i, item in enumerate(result["data"]["items"][:3], 1):
        print(f"\n{i}. {item.get('title', 'N/A')}")
        print(f"   作者: {item.get('nickname', 'N/A')}")
        print(f"   点赞: {item.get('liked_count', 'N/A')}")


def example_zhihu():
    """示例：采集知乎数据"""
    print("\n" + "=" * 80)
    print("示例 3: 采集知乎数据")
    print("=" * 80)

    client = MediaCrawlerClient()

    result = client.search_and_wait(
        platform="zhihu",
        keyword="Python教程",
        max_count=5,
        enable_comments=False,
        enable_media=False
    )

    print("\n📝 结果预览:")
    for i, item in enumerate(result["data"]["items"][:3], 1):
        print(f"\n{i}. {item.get('title', 'N/A')}")
        print(f"   作者: {item.get('author_name', 'N/A')}")
        print(f"   赞同: {item.get('voteup_count', 'N/A')}")


def example_batch():
    """示例：批量采集多个平台"""
    print("\n" + "=" * 80)
    print("示例 4: 批量采集多个平台")
    print("=" * 80)

    client = MediaCrawlerClient()

    tasks = [
        {"platform": "dy", "keyword": "健身教程"},
        {"platform": "xhs", "keyword": "穿搭分享"},
        {"platform": "zhihu", "keyword": "职场经验"}
    ]

    print(f"📋 共 {len(tasks)} 个任务")

    # 创建所有任务
    task_ids = []
    for task in tasks:
        task_id = client.search(
            platform=task["platform"],
            keyword=task["keyword"],
            max_count=5
        )
        task_ids.append((task_id, task))
        print(f"✅ 创建任务: {task['platform']} - {task['keyword']} ({task_id})")

    print(f"\n⏳ 等待所有任务完成...")

    # 等待所有任务完成
    results = []
    for task_id, task in task_ids:
        try:
            result = client.wait_for_task(task_id)
            results.append({
                "platform": task["platform"],
                "keyword": task["keyword"],
                "result": result
            })
            print(f"✅ {task['platform']} - {task['keyword']} 完成")
        except Exception as e:
            print(f"❌ {task['platform']} - {task['keyword']} 失败: {e}")

    print(f"\n🎉 批量采集完成！成功 {len(results)} 个")


def example_custom():
    """示例：自定义采集"""
    print("\n" + "=" * 80)
    print("示例 5: 自定义采集参数")
    print("=" * 80)

    client = MediaCrawlerClient()

    # 不采集评论，加快速度
    result = client.search_and_wait(
        platform="dy",
        keyword="旅行vlog",
        max_count=3,
        enable_comments=False,  # 不采集评论
        enable_media=False,     # 不下载媒体
        verbose=True
    )

    # 保存到文件
    output_file = "custom_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n💾 结果已保存到: {output_file}")


def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║              MediaCrawler API 客户端示例                       ║
║                                                                ║
║  请确保 API 服务已启动: python api_server.py                  ║
║  或使用: ./start_api.sh                                        ║
╚════════════════════════════════════════════════════════════════╝
    """)

    # 检查 API 是否可用
    try:
        client = MediaCrawlerClient()
        platforms = client.get_platforms()
        print(f"✅ API 服务连接成功！")
        print(f"📊 支持的平台: {', '.join([p['name'] for p in platforms['platforms']])}\n")
    except Exception as e:
        print(f"❌ API 服务未启动或连接失败: {e}")
        print(f"请先启动 API 服务: python api_server.py")
        return

    # 运行示例
    try:
        # 示例1：采集抖音
        example_douyin()

        # 示例2：采集小红书（需要配置Cookie）
        # example_xiaohongshu()

        # 示例3：采集知乎（需要配置Cookie）
        # example_zhihu()

        # 示例4：批量采集
        # example_batch()

        # 示例5：自定义采集
        # example_custom()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ 所有示例运行完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
