"""应用主入口：FastAPI 应用工厂。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db


def create_app() -> FastAPI:
    """应用工厂：测试可重复创建独立实例（隔离配置/中间件）。"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # CORS：允许前端(web dev server) 与企业微信 H5 跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 启动钩子：初始化数据库表（幂等）
    app.add_event_handler("startup", init_db)

    # 业务路由：/api/v1/*
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
