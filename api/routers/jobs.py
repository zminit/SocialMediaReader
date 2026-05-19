"""任务管理路由 — 手动触发 + 定时任务查询。"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scheduler.models import JobCommand
from scheduler.scheduler import Scheduler

from api.dependencies import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ------------------------------------------------------------------ #
#  请求模型
# ------------------------------------------------------------------ #


class TriggerRequest(BaseModel):
    """手动触发任务请求。"""

    job_type: str = Field(
        ..., description="任务类型: collect / analyze / report"
    )
    topic_id: int = Field(
        ..., description="主题 ID（analyze 传 0 表示所有主题）"
    )
    keywords_override: Optional[List[str]] = Field(
        None, description="覆盖关键词（仅 collect）"
    )
    max_items: int = Field(50, ge=1, le=200, description="最大采集数（仅 collect）")
    max_analyze: int = Field(20, ge=1, le=100, description="最大分析数（仅 analyze）")


# ------------------------------------------------------------------ #
#  路由
# ------------------------------------------------------------------ #


@router.post("/trigger")
def trigger_job(
    body: TriggerRequest,
    scheduler: Scheduler = Depends(get_scheduler),
) -> Dict[str, Any]:
    """手动触发一次任务，同步执行并返回结果。

    注意：collect 和 analyze 可能需要较长时间（10s~几分钟），
    客户端需设置较长的超时时间。
    """
    try:
        command = JobCommand(
            job_type=body.job_type,
            topic_id=body.topic_id,
            trigger="manual",
            keywords_override=body.keywords_override,
            max_items=body.max_items,
            max_analyze=body.max_analyze,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        "API trigger: type=%s, topic_id=%d",
        body.job_type,
        body.topic_id,
    )

    result = scheduler.trigger_manual(command)
    return result.to_dict()


@router.get("")
def list_scheduled_jobs(
    scheduler: Scheduler = Depends(get_scheduler),
) -> List[Dict[str, Any]]:
    """查看当前注册的定时任务。"""
    if scheduler._scheduler is None:
        return []

    jobs = scheduler._scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


@router.get("/status")
def scheduler_status(
    scheduler: Scheduler = Depends(get_scheduler),
) -> Dict[str, Any]:
    """查看调度器状态。"""
    return {
        "running": scheduler.running,
        "enabled": scheduler.config.enabled,
        "collect_hour_utc": scheduler.config.collect_hour,
        "analyze_hour_utc": scheduler.config.analyze_hour,
        "report_day": scheduler.config.report_day,
        "report_hour_utc": scheduler.config.report_hour,
    }
