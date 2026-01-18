"""
监控模块 API 路由

功能：
1. 账号管理（添加、删除、列表）
2. 分类管理（按领域分类：出国留学、宠物视频等）
3. 爆款内容查询
4. 定时任务控制
"""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.mongodb_store_base import MongoDBStoreBase
from monitor import HotContentDetector, HotLevel, monitor_scheduler


router = APIRouter(prefix="/monitor", tags=["monitor"])

# MongoDB 存储
mongo_store = MongoDBStoreBase(collection_prefix="monitor")

# 爆款识别器
hot_detector = HotContentDetector()


# ==================== 请求/响应模型 ====================

class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., description="分类名称，如：出国留学、宠物视频")
    description: Optional[str] = Field(None, description="分类描述")
    hot_thresholds: Optional[dict] = Field(None, description="自定义爆款阈值")


class CategoryResponse(BaseModel):
    """分类响应"""
    name: str
    description: Optional[str]
    account_count: int = 0
    note_count: int = 0
    hot_note_count: int = 0
    created_at: Optional[str] = None


class AccountCreate(BaseModel):
    """添加监控账号请求"""
    url: str = Field(..., description="账号主页URL")
    category: str = Field(..., description="所属分类")
    nickname: Optional[str] = Field(None, description="账号昵称")
    remark: Optional[str] = Field(None, description="备注")


class AccountBatchCreate(BaseModel):
    """批量添加账号"""
    urls: List[str] = Field(..., description="账号URL列表")
    category: str = Field(..., description="所属分类")


class AccountResponse(BaseModel):
    """账号响应"""
    user_id: str
    url: str
    nickname: Optional[str]
    category: str
    is_active: bool = True
    last_crawl_time: Optional[str] = None
    created_at: Optional[str] = None


class HotNoteResponse(BaseModel):
    """爆款笔记响应"""
    note_id: str
    title: Optional[str]
    user_id: Optional[str]
    nickname: Optional[str]
    hot_level: str
    hot_score: float
    liked_count: int
    collected_count: int
    comment_count: int
    detected_at: Optional[str]


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应"""
    is_running: bool
    jobs: List[dict]


class TriggerResponse(BaseModel):
    """手动触发响应"""
    success: bool
    message: Optional[str]
    new_notes_count: int = 0
    hot_notes_count: int = 0


# ==================== 分类管理 API ====================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories():
    """获取所有分类列表"""
    categories = await mongo_store.find_many("categories", {})

    result = []
    for cat in categories:
        # 统计该分类下的账号和笔记数
        account_count = await mongo_store.count("accounts", {"category": cat["name"]})
        note_count = await mongo_store.count("notes", {"category": cat["name"]})
        hot_note_count = await mongo_store.count("hot_notes", {"category": cat["name"]})

        result.append(CategoryResponse(
            name=cat["name"],
            description=cat.get("description"),
            account_count=account_count,
            note_count=note_count,
            hot_note_count=hot_note_count,
            created_at=cat.get("created_at")
        ))

    return result


@router.post("/categories", response_model=CategoryResponse)
async def create_category(request: CategoryCreate):
    """创建新分类"""
    # 检查是否已存在
    existing = await mongo_store.find_one("categories", {"name": request.name})
    if existing:
        raise HTTPException(status_code=400, detail=f"分类 '{request.name}' 已存在")

    category_data = {
        "name": request.name,
        "description": request.description,
        "hot_thresholds": request.hot_thresholds,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    await mongo_store.save_or_update(
        "categories",
        {"name": request.name},
        category_data
    )

    return CategoryResponse(
        name=request.name,
        description=request.description,
        created_at=category_data["created_at"]
    )


@router.delete("/categories/{name}")
async def delete_category(name: str):
    """删除分类"""
    # 检查是否有账号在使用该分类
    account_count = await mongo_store.count("accounts", {"category": name})
    if account_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"分类 '{name}' 下有 {account_count} 个账号，请先移除账号"
        )

    collection = await mongo_store.get_collection("categories")
    result = await collection.delete_one({"name": name})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"分类 '{name}' 不存在")

    return {"status": "ok", "message": f"分类 '{name}' 已删除"}


# ==================== 账号管理 API ====================

@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    category: Optional[str] = Query(None, description="按分类筛选"),
    is_active: Optional[bool] = Query(None, description="按状态筛选")
):
    """获取监控账号列表"""
    query = {}
    if category:
        query["category"] = category
    if is_active is not None:
        query["is_active"] = is_active

    accounts = await mongo_store.find_many("accounts", query)

    return [
        AccountResponse(
            user_id=acc.get("user_id", ""),
            url=acc.get("url", ""),
            nickname=acc.get("nickname"),
            category=acc.get("category", ""),
            is_active=acc.get("is_active", True),
            last_crawl_time=acc.get("last_crawl_time"),
            created_at=acc.get("created_at")
        )
        for acc in accounts
    ]


@router.post("/accounts", response_model=AccountResponse)
async def add_account(request: AccountCreate):
    """添加监控账号"""
    from media_platform.xhs.help import parse_creator_info_from_url

    # 解析 URL 获取用户ID
    try:
        creator_info = parse_creator_info_from_url(request.url)
        user_id = creator_info.user_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无效的账号URL: {e}")

    # 检查分类是否存在
    category = await mongo_store.find_one("categories", {"name": request.category})
    if not category:
        # 自动创建分类
        await mongo_store.save_or_update(
            "categories",
            {"name": request.category},
            {
                "name": request.category,
                "created_at": datetime.now().isoformat()
            }
        )

    # 保存账号
    account_data = {
        "user_id": user_id,
        "url": request.url,
        "nickname": request.nickname,
        "category": request.category,
        "remark": request.remark,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    await mongo_store.save_or_update(
        "accounts",
        {"user_id": user_id},
        account_data
    )

    return AccountResponse(
        user_id=user_id,
        url=request.url,
        nickname=request.nickname,
        category=request.category,
        is_active=True,
        created_at=account_data["created_at"]
    )


@router.post("/accounts/batch")
async def add_accounts_batch(request: AccountBatchCreate):
    """批量添加监控账号"""
    from media_platform.xhs.help import parse_creator_info_from_url

    # 确保分类存在
    category = await mongo_store.find_one("categories", {"name": request.category})
    if not category:
        await mongo_store.save_or_update(
            "categories",
            {"name": request.category},
            {
                "name": request.category,
                "created_at": datetime.now().isoformat()
            }
        )

    added = []
    failed = []

    for url in request.urls:
        try:
            creator_info = parse_creator_info_from_url(url)
            user_id = creator_info.user_id

            account_data = {
                "user_id": user_id,
                "url": url,
                "category": request.category,
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            await mongo_store.save_or_update(
                "accounts",
                {"user_id": user_id},
                account_data
            )
            added.append({"user_id": user_id, "url": url})
        except Exception as e:
            failed.append({"url": url, "error": str(e)})

    return {
        "status": "ok",
        "added_count": len(added),
        "failed_count": len(failed),
        "added": added,
        "failed": failed
    }


@router.delete("/accounts/{user_id}")
async def delete_account(user_id: str):
    """删除监控账号"""
    collection = await mongo_store.get_collection("accounts")
    result = await collection.delete_one({"user_id": user_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"账号 '{user_id}' 不存在")

    return {"status": "ok", "message": f"账号 '{user_id}' 已删除"}


@router.patch("/accounts/{user_id}/toggle")
async def toggle_account(user_id: str):
    """切换账号监控状态"""
    account = await mongo_store.find_one("accounts", {"user_id": user_id})
    if not account:
        raise HTTPException(status_code=404, detail=f"账号 '{user_id}' 不存在")

    new_status = not account.get("is_active", True)
    await mongo_store.save_or_update(
        "accounts",
        {"user_id": user_id},
        {"is_active": new_status, "updated_at": datetime.now().isoformat()}
    )

    return {"status": "ok", "is_active": new_status}


# ==================== 爆款内容 API ====================

@router.get("/hot-notes", response_model=List[HotNoteResponse])
async def get_hot_notes(
    category: Optional[str] = Query(None, description="按分类筛选"),
    level: Optional[str] = Query(None, description="爆款等级: trending/hot/viral"),
    days: int = Query(7, description="最近几天"),
    limit: int = Query(50, description="返回数量限制")
):
    """获取爆款笔记列表"""
    query = {}

    if category:
        query["category"] = category

    if level:
        query["hot_level"] = level

    # 时间范围
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    query["detected_at"] = {"$gte": cutoff_date}

    collection = await mongo_store.get_collection("hot_notes")
    cursor = collection.find(query).sort("hot_score", -1).limit(limit)
    hot_notes = await cursor.to_list(length=limit)

    return [
        HotNoteResponse(
            note_id=note.get("note_id", ""),
            title=note.get("title"),
            user_id=note.get("user_id"),
            nickname=note.get("nickname"),
            hot_level=note.get("hot_level", "normal"),
            hot_score=note.get("hot_score", 0),
            liked_count=note.get("liked_count", 0),
            collected_count=note.get("collected_count", 0),
            comment_count=note.get("comment_count", 0),
            detected_at=note.get("detected_at")
        )
        for note in hot_notes
    ]


@router.get("/notes/latest")
async def get_latest_notes(
    category: Optional[str] = Query(None, description="按分类筛选"),
    hours: int = Query(24, description="最近几小时"),
    limit: int = Query(50, description="返回数量限制")
):
    """获取最新抓取的笔记"""
    query = {}

    if category:
        query["category"] = category

    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    query["crawled_at"] = {"$gte": cutoff_time}

    collection = await mongo_store.get_collection("notes")
    cursor = collection.find(query).sort("crawled_at", -1).limit(limit)
    notes = await cursor.to_list(length=limit)

    return {
        "total": len(notes),
        "notes": [
            {
                "note_id": note.get("note_id"),
                "title": note.get("title"),
                "desc": note.get("desc", "")[:200],  # 截取前200字
                "user_id": note.get("user_id"),
                "nickname": note.get("nickname"),
                "liked_count": note.get("liked_count", 0),
                "collected_count": note.get("collected_count", 0),
                "comment_count": note.get("comment_count", 0),
                "hot_analysis": note.get("hot_analysis"),
                "crawled_at": note.get("crawled_at")
            }
            for note in notes
        ]
    }


@router.get("/notes/{note_id}")
async def get_note_detail(note_id: str):
    """获取笔记详情"""
    note = await mongo_store.find_one("notes", {"note_id": note_id})

    if not note:
        raise HTTPException(status_code=404, detail=f"笔记 '{note_id}' 不存在")

    # 移除 MongoDB _id
    if "_id" in note:
        del note["_id"]

    return note


# ==================== 统计 API ====================

@router.get("/stats")
async def get_stats(category: Optional[str] = Query(None, description="按分类筛选")):
    """获取监控统计数据"""
    query = {}
    if category:
        query["category"] = category

    account_count = await mongo_store.count("accounts", {**query, "is_active": True})
    note_count = await mongo_store.count("notes", query)

    # 各等级爆款数量
    hot_notes_count = await mongo_store.count("hot_notes", {**query, "hot_level": "hot"})
    viral_notes_count = await mongo_store.count("hot_notes", {**query, "hot_level": "viral"})
    trending_notes_count = await mongo_store.count("hot_notes", {**query, "hot_level": "trending"})

    # 今日新增
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    today_notes = await mongo_store.count("notes", {**query, "crawled_at": {"$gte": today}})
    today_hot = await mongo_store.count("hot_notes", {**query, "detected_at": {"$gte": today}})

    return {
        "accounts": {
            "total": account_count
        },
        "notes": {
            "total": note_count,
            "today": today_notes
        },
        "hot_notes": {
            "trending": trending_notes_count,
            "hot": hot_notes_count,
            "viral": viral_notes_count,
            "today": today_hot
        }
    }


@router.get("/stats/category/{name}")
async def get_category_stats(name: str):
    """获取指定分类的详细统计"""
    # 检查分类是否存在
    category = await mongo_store.find_one("categories", {"name": name})
    if not category:
        raise HTTPException(status_code=404, detail=f"分类 '{name}' 不存在")

    # 基础统计
    account_count = await mongo_store.count("accounts", {"category": name, "is_active": True})
    note_count = await mongo_store.count("notes", {"category": name})

    # 获取热门创作者
    collection = await mongo_store.get_collection("hot_notes")
    pipeline = [
        {"$match": {"category": name}},
        {"$group": {
            "_id": "$user_id",
            "nickname": {"$first": "$nickname"},
            "hot_count": {"$sum": 1},
            "avg_score": {"$avg": "$hot_score"}
        }},
        {"$sort": {"hot_count": -1}},
        {"$limit": 10}
    ]
    top_creators = await collection.aggregate(pipeline).to_list(length=10)

    return {
        "category": name,
        "description": category.get("description"),
        "account_count": account_count,
        "note_count": note_count,
        "top_creators": [
            {
                "user_id": c["_id"],
                "nickname": c.get("nickname"),
                "hot_count": c["hot_count"],
                "avg_score": round(c["avg_score"], 2)
            }
            for c in top_creators
        ]
    }


# ==================== 调度器控制 API ====================

@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """获取调度器状态"""
    return SchedulerStatusResponse(
        is_running=monitor_scheduler.is_running,
        jobs=monitor_scheduler.get_jobs()
    )


@router.post("/scheduler/start")
async def start_scheduler():
    """启动调度器"""
    if monitor_scheduler.is_running:
        raise HTTPException(status_code=400, detail="调度器已在运行")

    # 添加默认任务
    monitor_scheduler.add_account_monitor_job()
    monitor_scheduler.add_trending_update_job()
    monitor_scheduler.add_cleanup_job()

    monitor_scheduler.start()

    return {"status": "ok", "message": "调度器已启动"}


@router.post("/scheduler/stop")
async def stop_scheduler():
    """停止调度器"""
    if not monitor_scheduler.is_running:
        raise HTTPException(status_code=400, detail="调度器未运行")

    monitor_scheduler.stop()

    return {"status": "ok", "message": "调度器已停止"}


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_monitor(category: Optional[str] = Query(None, description="指定分类")):
    """手动触发一次监控抓取"""
    try:
        # 如果指定了分类，只抓取该分类的账号
        if category:
            accounts = await mongo_store.find_many(
                "accounts",
                {"category": category, "is_active": True}
            )
        else:
            accounts = await mongo_store.find_many(
                "accounts",
                {"is_active": True}
            )

        if not accounts:
            return TriggerResponse(
                success=False,
                message="没有活跃的监控账号"
            )

        # 导入并初始化监控器
        from monitor.account_monitor import get_monitor
        monitor = await get_monitor()

        account_urls = [acc.get("url") for acc in accounts if acc.get("url")]

        # 执行监控
        new_notes = await monitor.monitor_accounts(
            account_urls=account_urls,
            only_new=True
        )

        # 为笔记添加分类标记
        for note in new_notes:
            # 找到对应的账号分类
            account = next(
                (acc for acc in accounts if acc.get("user_id") == note.get("source_user_id")),
                None
            )
            if account:
                note["category"] = account.get("category")
                # 更新数据库中的分类
                await mongo_store.save_or_update(
                    "notes",
                    {"note_id": note.get("note_id")},
                    {"category": account.get("category")}
                )

        # 识别爆款
        hot_notes = hot_detector.batch_detect(new_notes, min_level=HotLevel.TRENDING)

        # 为爆款笔记也添加分类
        for note in hot_notes:
            if note.get("category"):
                await mongo_store.save_or_update(
                    "hot_notes",
                    {"note_id": note.get("note_id")},
                    {"category": note.get("category")}
                )

        return TriggerResponse(
            success=True,
            message=f"抓取完成",
            new_notes_count=len(new_notes),
            hot_notes_count=len(hot_notes)
        )

    except Exception as e:
        return TriggerResponse(
            success=False,
            message=str(e)
        )
