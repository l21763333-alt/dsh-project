"""数据库会话与建表。

MVP 采用同步 SQLAlchemy + create_all（幂等建表），后续可平滑切换 Alembic 迁移。
测试环境通过 DATABASE_URL=sqlite:///:memory: 使用内存库，无需 MySQL。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

DATABASE_URL = settings.resolved_database_url
_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # SQLite 内存库必须共享同一连接，否则跨会话数据不可见
    poolclass=StaticPool if _is_sqlite and ":memory:" in DATABASE_URL else None,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def init_db() -> None:
    """应用启动钩子：创建所有表（幂等）。

    必须先导入 models 包以注册全部 ORM 模型到 Base.metadata。
    """
    from app import models  # noqa: F401  确保模型注册

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：请求级数据库会话，自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
