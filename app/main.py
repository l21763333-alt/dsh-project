"""应用主入口：FastAPI 应用工厂。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期：启动时初始化数据库表（幂等，lifespan 模式全版本兼容）。"""
    init_db()
    yield


def create_app() -> FastAPI:
    """应用工厂：测试可重复创建独立实例（隔离配置/中间件）。"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS：允许前端(web dev server) 与企业微信 H5 跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 业务路由：/api/v1/*
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # 单端口部署：前端构建产物存在时由 FastAPI 托管
    _mount_frontend(app)

    return app


def _mount_frontend(app: FastAPI) -> None:
    """web/dist 存在时挂载为静态资源（SPA 使用 hash 路由，无需服务端 fallback）。"""
    dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")


app = create_app()
