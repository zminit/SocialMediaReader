"""主题管理路由。"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from storage.topic_repository import SQLiteTopicRepository

from api.dependencies import get_topic_repo

router = APIRouter(prefix="/api/topics", tags=["topics"])


# ------------------------------------------------------------------ #
#  请求 / 响应模型
# ------------------------------------------------------------------ #


class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="主题名称")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    keywords: Optional[List[str]] = None


class TopicResponse(BaseModel):
    id: int
    name: str
    keywords: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ------------------------------------------------------------------ #
#  路由
# ------------------------------------------------------------------ #


@router.get("", response_model=List[TopicResponse])
def list_topics(
    repo: SQLiteTopicRepository = Depends(get_topic_repo),
):
    """获取所有主题列表。"""
    return repo.list_topics()


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(
    topic_id: int,
    repo: SQLiteTopicRepository = Depends(get_topic_repo),
):
    """获取单个主题详情。"""
    topic = repo.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    return topic


@router.post("", response_model=TopicResponse, status_code=201)
def create_topic(
    body: TopicCreate,
    repo: SQLiteTopicRepository = Depends(get_topic_repo),
):
    """创建新主题。"""
    topic_id = repo.create_topic(name=body.name, keywords=body.keywords)
    topic = repo.get_topic(topic_id)
    return topic


@router.put("/{topic_id}", response_model=TopicResponse)
def update_topic(
    topic_id: int,
    body: TopicUpdate,
    repo: SQLiteTopicRepository = Depends(get_topic_repo),
):
    """更新主题。"""
    existing = repo.get_topic(topic_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    updated = repo.update_topic(
        topic_id,
        name=body.name,
        keywords=body.keywords,
    )
    if not updated:
        raise HTTPException(status_code=400, detail="No fields to update")

    return repo.get_topic(topic_id)
