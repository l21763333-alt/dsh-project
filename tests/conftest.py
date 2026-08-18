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

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    """FastAPI TestClient：with 块触发 startup 钩子（建表）。"""
    with TestClient(app) as c:
        yield c
