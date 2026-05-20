"""日志查看 API。"""

from typing import Optional

from fastapi import APIRouter, Query

from logging_config.db_handler import LogQueryService

router = APIRouter(prefix="/api/logs", tags=["logs"])

_log_service: Optional[LogQueryService] = None


def _get_service() -> LogQueryService:
    global _log_service
    if _log_service is None:
        from logging_config.config import LogConfig
        config = LogConfig.from_env()
        _log_service = LogQueryService(db_path=config.db_path)
    return _log_service


@router.get("")
def query_logs(
    level: Optional[str] = Query(None, description="按级别过滤: DEBUG/INFO/WARNING/ERROR"),
    logger: Optional[str] = Query(None, description="按模块名过滤（模糊匹配）"),
    search: Optional[str] = Query(None, description="搜索消息内容"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO 格式)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 格式)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """查询日志记录（分页、可过滤）。"""
    service = _get_service()
    return service.query_logs(
        level=level,
        logger_name=logger,
        search=search,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def log_stats():
    """获取日志统计信息。"""
    service = _get_service()
    return service.get_stats()


@router.delete("")
def clear_logs(
    before: Optional[str] = Query(None, description="清理此时间之前的日志 (ISO 格式)"),
):
    """清理日志记录。"""
    service = _get_service()
    deleted = service.clear_logs(before=before)
    return {"deleted": deleted}
