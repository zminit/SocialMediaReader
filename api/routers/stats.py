"""系统统计路由。"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from storage.source_repository import SQLiteSourceRepository
from storage.duplicate_repository import SQLiteDuplicateRecordRepository
from storage.filtered_repository import SQLiteFilteredRecordRepository

from api.dependencies import (
    get_source_repo,
    get_duplicate_repo,
    get_filtered_repo,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats(
    source_repo: SQLiteSourceRepository = Depends(get_source_repo),
    dup_repo: SQLiteDuplicateRecordRepository = Depends(get_duplicate_repo),
    filter_repo: SQLiteFilteredRecordRepository = Depends(get_filtered_repo),
) -> Dict[str, Any]:
    """获取系统统计信息。"""
    sources_by_status = source_repo.count_by_status()
    duplicates_by_type = dup_repo.count_by_type()
    filtered_by_reason = filter_repo.count_by_reason()

    total_sources = sum(sources_by_status.values())
    total_duplicates = sum(duplicates_by_type.values())
    total_filtered = sum(filtered_by_reason.values())

    return {
        "sources": {
            "total": total_sources,
            "by_status": sources_by_status,
        },
        "duplicates": {
            "total": total_duplicates,
            "by_type": duplicates_by_type,
        },
        "filtered": {
            "total": total_filtered,
            "by_reason": filtered_by_reason,
        },
        "pipeline_total": total_sources + total_duplicates + total_filtered,
    }
