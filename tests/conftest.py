"""pytest 全局夹具。

关键点：
- 必须在导入 app 之前设置环境变量，config 单例在导入时读取。
- 测试使用 SQLite 内存库，避免依赖 MySQL；LLM Key 用假值（测试不真实调用）。
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_API_KEY"] = "test-key-not-real"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """会话级建表：服务层单测不经过 TestClient 启动钩子，需显式建表。"""
    from app import models  # noqa: F401 —— 注册全部模型

    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def _isolate_storage(tmp_path_factory):
    """测试期间把文件存储隔离到临时目录，避免污染 data/files（测试上传走真实 upload 路径）。"""
    from app.core.config import settings

    tmp_storage = tmp_path_factory.mktemp("test_storage")
    settings.STORAGE_PATH = str(tmp_storage)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """每个用例结束后清空数据（SQLite 内存库跨用例共享同一连接，防止数据串扰）。"""
    yield
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client():
    """FastAPI TestClient：with 块触发 startup 钩子（建表，幂等）。"""
    with TestClient(app) as c:
        yield c
