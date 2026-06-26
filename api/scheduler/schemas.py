# -*- coding: utf-8 -*-

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from api.schemas.crawler import (
    CrawlerTypeEnum,
    LoginTypeEnum,
    PlatformEnum,
    SaveDataOptionEnum,
)


class InstanceStatusEnum(str, Enum):
    """Scheduler instance status."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    DISABLED = "disabled"


class TaskStatusEnum(str, Enum):
    """Scheduler task status."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class InstanceCreateRequest(BaseModel):
    """Create a crawler instance."""

    name: str = Field(..., min_length=1, max_length=80)
    platform: PlatformEnum
    login_type: LoginTypeEnum = LoginTypeEnum.QRCODE
    headless: bool = False
    save_option: SaveDataOptionEnum = SaveDataOptionEnum.JSONL
    browser_profile_dir: str = ""
    cdp_debug_port: Optional[int] = Field(default=None, ge=1000, le=65535)
    default_params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("instance name cannot be empty")
        return value


class InstanceUpdateRequest(BaseModel):
    """Update mutable crawler instance settings."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    login_type: Optional[LoginTypeEnum] = None
    headless: Optional[bool] = None
    save_option: Optional[SaveDataOptionEnum] = None
    browser_profile_dir: Optional[str] = None
    cdp_debug_port: Optional[int] = Field(default=None, ge=1000, le=65535)
    default_params: Optional[Dict[str, Any]] = None
    status: Optional[InstanceStatusEnum] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("instance name cannot be empty")
        return value


class InstanceResponse(BaseModel):
    id: str
    name: str
    platform: str
    login_type: str
    headless: bool
    save_option: str
    browser_profile_dir: str
    cdp_debug_port: int
    default_params: Dict[str, Any]
    status: str
    current_task_id: Optional[str] = None
    pid: Optional[int] = None
    last_error: str = ""
    created_at: str
    updated_at: str


class TaskCreateRequest(BaseModel):
    """Create a crawler task bound to one instance."""

    instance_id: str
    crawler_type: CrawlerTypeEnum = CrawlerTypeEnum.SEARCH
    target_text: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: str
    instance_id: str
    crawler_type: str
    target_text: str
    params: Dict[str, Any]
    status: str
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    artifact_dir: str = ""
    error_message: str = ""
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class TaskLogResponse(BaseModel):
    id: int
    task_id: str
    timestamp: str
    level: str
    message: str


class ArtifactResponse(BaseModel):
    id: str
    task_id: str
    path: str
    type: str
    size: int
    modified_at: float
    record_count: Optional[int] = None


class SchedulerStatusResponse(BaseModel):
    instances_total: int
    running_instances: int
    queued_tasks: int
    running_tasks: int
