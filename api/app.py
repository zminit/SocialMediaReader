"""FastAPI 应用入口。

Usage:
    uvicorn api.app:app --reload
    # 或
    python -m api.app
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import APIConfig
from .dependencies import get_app_state
from .routers import health, topics, sources, analysis, jobs, stats

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化，关闭时清理。"""
    state = get_app_state()

    # 启动：初始化各模块
    logger.info("Starting SocialMediaReader API...")
    state.init_storage()
    state.init_orchestrator()
    state.init_scheduler()
    state.start_scheduler()
    logger.info("API ready")

    yield

    # 关闭：清理资源
    logger.info("Shutting down SocialMediaReader API...")
    state.shutdown()
    logger.info("API shut down")


def create_app(config: APIConfig = None) -> FastAPI:
    """创建 FastAPI 应用实例。"""
    if config is None:
        config = APIConfig.from_env()

    app = FastAPI(
        title=config.title,
        version=config.version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(health.router)
    app.include_router(topics.router)
    app.include_router(sources.router)
    app.include_router(analysis.router)
    app.include_router(jobs.router)
    app.include_router(stats.router)

    return app


# 默认实例（uvicorn api.app:app）
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = APIConfig.from_env()
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "api.app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
