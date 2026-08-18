"""集中配置：所有可配置项从环境变量读取（开发用 .env，生产注入真实环境变量）。

核心安全要求：
- LLM_API_KEY 等密钥一律通过环境变量注入，禁止硬编码、禁止提交仓库。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录（app/core/config.py -> 上溯三级）
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 基础 ----
    PROJECT_NAME: str = "Recruit AI"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]  # MVP 开发期放开；生产收敛为具体域名

    # ---- 数据库（默认 MySQL，需求指定）----
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "recruit"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "recruit_ai"
    DATABASE_URL: str = ""  # 非空时优先（测试用 sqlite:///:memory:）

    # ---- DeepSeek LLM（OpenAI 兼容协议）----
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT: float = 60.0
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1

    # ---- 文件存储（本地磁盘，MVP）----
    STORAGE_PATH: str = str(BASE_DIR / "data" / "files")

    @property
    def resolved_database_url(self) -> str:
        """完整连接串：显式 DATABASE_URL 优先，否则拼 MySQL 连接串。"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )


settings = Settings()  # 全局单例：业务代码统一 `from app.core.config import settings`
