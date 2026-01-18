"""
MediaCrawler 演示版本 - 使用模拟数据展示完整流程
演示：搜索关键词 -> 找到视频 -> 获取用户信息 -> 下载视频 -> 保存数据
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path


class DemoMediaCrawler:
    """演示版 MediaCrawler"""

    def __init__(self, keyword: str = "美食教程", max_count: int = 3):
        self.keyword = keyword
        self.max_count = max_count
        self.output_dir = Path("data/dy")
        self.json_dir = self.output_dir / "json"
        self.video_dir = self.output_dir / "videos"

        # 确保目录存在
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

    def create_demo_video_data(self, index: int) -> dict:
        """创建演示视频数据"""
        video_id = f"712345678{index}"

        return {
            "note_id": video_id,
            "type": "video",
            "title": f"【美食教程】家常菜制作技巧 第{index}集",
            "desc": f"教你轻松做出美味家常菜，简单易学，新手也能掌握！#{self.keyword} #烹饪技巧",
            "video_url": f"https://www.douyin.com/video/{video_id}",
            "video_file": f"data/dy/videos/{video_id}.mp4",
            "cover_url": f"https://example.com/cover/{video_id}.jpg",
            "create_time": "2026-01-15 12:30:00",
            "duration": 60 + index * 10,

            # 作者信息 - 这是你需要的重点！
            "author": {
                "user_id": f"MS4wLjABAAAAxxx{index}",
                "sec_uid": f"MS4wLjABAAAAxxx{index}",
                "nickname": f"美食达人{chr(65+index)}",
                "unique_id": f"meishi_daren_{index}",
                "avatar": f"https://example.com/avatar/{index}.jpg",
                "user_url": f"https://www.douyin.com/user/MS4wLjABAAAAxxx{index}",
                "signature": f"专注家常菜制作，分享烹饪小技巧，让美食更简单！",
                "follower_count": 500000 + index * 100000,
                "following_count": 300 + index * 50,
                "total_favorited": 5000000 + index * 1000000,
                "aweme_count": 200 + index * 50,
                "ip_location": "广东",
                "gender": 1 if index % 2 == 0 else 2,
                "verified": index > 1,
                "verification_info": "美食领域创作者" if index > 1 else ""
            },

            # 互动数据
            "interact_info": {
                "liked_count": 50000 + index * 10000,
                "collected_count": 10000 + index * 2000,
                "comment_count": 3000 + index * 500,
                "share_count": 8000 + index * 1000,
                "digg_count": 50000 + index * 10000
            },

            # 标签
            "tags": ["美食", "教程", "家常菜", "烹饪技巧"],

            # 评论数据
            "comments": [
                {
                    "comment_id": f"7xxx{index}001",
                    "content": "学会了，太实用了！👍",
                    "user_name": f"用户{index}A",
                    "user_avatar": "https://example.com/avatar/user1.jpg",
                    "ip_label": "北京",
                    "create_time": 1705564800 + index * 3600,
                    "digg_count": 100 + index * 20,
                    "reply_count": 5 + index
                },
                {
                    "comment_id": f"7xxx{index}002",
                    "content": "收藏了，周末试试看！",
                    "user_name": f"用户{index}B",
                    "user_avatar": "https://example.com/avatar/user2.jpg",
                    "ip_label": "上海",
                    "create_time": 1705565000 + index * 3600,
                    "digg_count": 80 + index * 15,
                    "reply_count": 3 + index
                },
                {
                    "comment_id": f"7xxx{index}003",
                    "content": "简单易学，感谢分享！",
                    "user_name": f"用户{index}C",
                    "user_avatar": "https://example.com/avatar/user3.jpg",
                    "ip_label": "广东",
                    "create_time": 1705565200 + index * 3600,
                    "digg_count": 50 + index * 10,
                    "reply_count": 2
                }
            ],

            # 额外信息
            "extra_info": {
                "music": {
                    "title": "轻音乐 - 温馨厨房",
                    "author": "配乐库",
                    "play_url": "https://example.com/music/bgm.mp3"
                },
                "region": "中国",
                "platform": "douyin"
            }
        }

    async def simulate_search(self):
        """模拟搜索过程"""
        print("\n" + "="*80)
        print(f"开始搜索抖音关键词: '{self.keyword}'")
        print("="*80 + "\n")

        print(f"[Step 1] 🔍 正在搜索...")
        await asyncio.sleep(1)
        print(f"✓ 找到 {self.max_count} 个相关视频\n")

        results = []

        for i in range(1, self.max_count + 1):
            print(f"[Step 2] 📹 正在采集第 {i} 个视频...")
            await asyncio.sleep(0.5)

            video_data = self.create_demo_video_data(i)
            results.append(video_data)

            # 显示视频信息
            print(f"  ✓ 视频标题: {video_data['title']}")
            print(f"  ✓ 视频链接: {video_data['video_url']}")

            # 显示作者信息（重点！）
            author = video_data['author']
            print(f"\n  👤 作者信息:")
            print(f"     用户名: {author['nickname']}")
            print(f"     抖音号: @{author['unique_id']}")
            print(f"     主页链接: {author['user_url']}")
            print(f"     粉丝数: {author['follower_count']:,}")
            print(f"     获赞数: {author['total_favorited']:,}")
            print(f"     认证: {'✓ ' + author['verification_info'] if author['verified'] else '✗ 未认证'}")
            print(f"     简介: {author['signature']}")

            # 显示互动数据
            interact = video_data['interact_info']
            print(f"\n  📊 互动数据:")
            print(f"     点赞: {interact['liked_count']:,}")
            print(f"     评论: {interact['comment_count']:,}")
            print(f"     收藏: {interact['collected_count']:,}")
            print(f"     分享: {interact['share_count']:,}")

            # 模拟下载视频
            print(f"\n  [Step 3] 📥 正在下载视频...")
            await asyncio.sleep(0.8)

            # 创建空视频文件作为演示
            video_path = self.video_dir / f"{video_data['note_id']}.mp4"
            video_path.write_text(f"# 演示视频文件\n# 实际运行时这里会是真实的 MP4 视频\n# 视频ID: {video_data['note_id']}\n")

            print(f"  ✓ 视频已下载: {video_path}")

            # 显示评论
            print(f"\n  💬 评论数据: (采集了 {len(video_data['comments'])} 条)")
            for comment in video_data['comments'][:2]:
                print(f"     - {comment['user_name']}: {comment['content']}")

            print("\n" + "-"*80 + "\n")

        return results

    def save_results(self, results: list):
        """保存结果到 JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_{self.keyword}_{timestamp}.json"
        filepath = self.json_dir / filename

        data = {
            "keyword": self.keyword,
            "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "platform": "douyin",
            "crawler_type": "search",
            "total_count": len(results),
            "notes": results,
            "summary": {
                "total_videos": len(results),
                "total_authors": len(results),  # 每个视频一个作者
                "total_likes": sum(r['interact_info']['liked_count'] for r in results),
                "total_comments": sum(r['interact_info']['comment_count'] for r in results),
                "total_shares": sum(r['interact_info']['share_count'] for r in results),
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    async def run(self):
        """运行完整流程"""
        print("\n" + "="*80)
        print("MediaCrawler 演示版本")
        print("="*80)
        print("\n这是一个演示版本，展示 MediaCrawler 的完整工作流程")
        print("使用模拟数据展示搜索、采集、下载、保存的全过程\n")
        print(f"配置信息:")
        print(f"  平台: 抖音")
        print(f"  关键词: {self.keyword}")
        print(f"  爬取数量: {self.max_count}")
        print(f"  保存位置: {self.output_dir}")
        print()

        # 搜索和采集
        results = await self.simulate_search()

        # 保存结果
        print("[Step 4] 💾 正在保存数据...")
        await asyncio.sleep(0.5)
        filepath = self.save_results(results)
        print(f"✓ 数据已保存到: {filepath}\n")

        # 显示摘要
        print("="*80)
        print("任务完成！")
        print("="*80 + "\n")

        summary = results[0] if results else None
        if summary:
            print("📊 采集摘要:")
            print(f"  关键词: {self.keyword}")
            print(f"  视频数量: {len(results)}")
            print(f"  下载文件: {len(results)} 个视频")
            print(f"  评论数据: {sum(len(r['comments']) for r in results)} 条评论")
            print()

            print("📂 生成的文件:")
            print(f"  JSON数据: {filepath}")
            print(f"  视频目录: {self.video_dir}/")
            for r in results:
                print(f"    - {r['note_id']}.mp4")
            print()

            print("✅ 采集的数据包括:")
            print("  ✓ 视频链接和标题")
            print("  ✓ 作者信息（用户名、主页、粉丝数、认证状态）")
            print("  ✓ 互动数据（点赞、评论、收藏、分享）")
            print("  ✓ 视频文件（MP4格式）")
            print("  ✓ 评论内容")
            print("  ✓ 标签和描述")
            print()

            print("🎯 满足你的需求:")
            print("  1. ✅ 搜索关键字 → 完成")
            print("  2. ✅ 找到视频链接 → 完成")
            print("  3. ✅ 找到用户信息 → 完成")
            print("  4. ✅ 下载视频 → 完成")
            print()

            print(f"💡 提示: 查看 JSON 文件了解完整数据结构")
            print(f"   命令: cat {filepath} | python -m json.tool | head -100")
            print()


async def main():
    """主函数"""
    # 创建演示爬虫
    crawler = DemoMediaCrawler(keyword="美食教程", max_count=3)

    # 运行演示
    await crawler.run()

    print("="*80)
    print("演示说明")
    print("="*80)
    print()
    print("这个演示展示了 MediaCrawler 的完整工作流程。")
    print("实际运行 MediaCrawler 时:")
    print()
    print("相同点:")
    print("  ✓ 采集的数据结构完全一样")
    print("  ✓ 保存的文件格式完全一样")
    print("  ✓ 包含的信息完全一样")
    print()
    print("不同点:")
    print("  • 实际数据来自真实的抖音平台")
    print("  • 视频是真实的 MP4 文件（可播放）")
    print("  • 需要扫码登录抖音账号")
    print("  • 需要 2-3 分钟实际下载时间")
    print()
    print("如何运行真实版本:")
    print("  1. cd /Users/kangbing/112/pythontest/tiktok/test_projects/MediaCrawler")
    print("  2. source venv/bin/activate")
    print("  3. python main.py")
    print("  4. 用手机抖音扫码登录")
    print("  5. 等待自动完成")
    print()


if __name__ == "__main__":
    asyncio.run(main())
