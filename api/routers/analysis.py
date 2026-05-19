"""分析结果查询路由。"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from storage.analysis_repository import SQLiteAnalysisResultRepository

from api.dependencies import get_analysis_repo

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("")
def list_analysis_results(
    topic_id: int = Query(..., description="主题 ID"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0, description="最低相关性分数"),
    limit: int = Query(50, ge=1, le=500, description="返回数量上限"),
    repo: SQLiteAnalysisResultRepository = Depends(get_analysis_repo),
) -> List[Dict[str, Any]]:
    """查询指定主题的分析结果，按相关性排序。"""
    return repo.list_by_topic(
        topic_id=topic_id,
        min_relevance=min_relevance,
        limit=limit,
    )


@router.get("/source/{source_id}")
def get_analysis_by_source(
    source_id: int,
    repo: SQLiteAnalysisResultRepository = Depends(get_analysis_repo),
) -> Dict[str, Any]:
    """获取指定 source 的分析结果。"""
    result = repo.get_by_source_id(source_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No analysis result for source {source_id}",
        )
    return result
