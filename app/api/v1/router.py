"""路由聚合：所有 v1 子路由在此挂载。新增模块在 api/v1/ 下建文件并在此 include。"""
from fastapi import APIRouter

from app.api.v1 import collect, health, resumes

api_router = APIRouter()
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["简历"])
api_router.include_router(collect.router, prefix="/collect", tags=["简历收集"])
