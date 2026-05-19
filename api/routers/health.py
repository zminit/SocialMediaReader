"""健康检查路由。"""

from fastapi import APIRouter, Depends

from api.dependencies import get_app_state, AppState

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(state: AppState = Depends(get_app_state)):
    """系统健康检查。"""
    checks = {
        "storage": state.db is not None,
        "orchestrator": state.orchestrator is not None,
        "scheduler_running": (
            state.scheduler is not None and state.scheduler.running
        ),
        "collector_available": (
            state.orchestrator is not None
            and state.orchestrator.collector is not None
        ),
        "dify_available": (
            state.orchestrator is not None
            and state.orchestrator.dify_client is not None
        ),
    }

    all_critical = checks["storage"]
    status = "healthy" if all_critical else "degraded"

    return {
        "status": status,
        "checks": checks,
    }
