"""健康检查：确认服务与数据库可用。"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """GET /api/v1/health —— 探活接口（部署/监控用）。"""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001 —— 探活必须吞掉异常并如实上报
        db_ok = False
    return {"status": "ok", "database": "ok" if db_ok else "error"}
