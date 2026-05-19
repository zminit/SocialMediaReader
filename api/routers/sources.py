"""采集内容查询路由。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from storage.source_repository import SQLiteSourceRepository

from api.dependencies import get_source_repo

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("")
def list_sources(
    topic_id: Optional[int] = Query(None, description="按主题过滤"),
    status: Optional[str] = Query(None, description="按状态过滤: pending_analysis, analyzed, analysis_failed"),
    limit: int = Query(50, ge=1, le=500, description="返回数量上限"),
    repo: SQLiteSourceRepository = Depends(get_source_repo),
) -> List[Dict[str, Any]]:
    """查询已采集的内容。

    - 不传参数：返回最新的 50 条
    - topic_id：按主题过滤
    - status：按状态过滤
    """
    if topic_id is not None:
        return repo.get_sources_by_topic(
            topic_id=topic_id, status=status, limit=limit
        )
    elif status is not None:
        return repo.get_sources_by_status(status=status, limit=limit)
    else:
        # 默认返回最新的
        return repo.get_sources_by_status(status="analyzed", limit=limit)


@router.get("/{source_id}")
def get_source(
    source_id: int,
    repo: SQLiteSourceRepository = Depends(get_source_repo),
) -> Dict[str, Any]:
    """获取单个 source 详情。"""
    source = repo.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source
