"""候选人档案模型：一人一档（多份简历/多次投递归并于此）。"""
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, index=True)
    phone = Column(String(32), nullable=True, index=True)   # 去重指纹之一
    email = Column(String(128), nullable=True, index=True)  # 去重指纹之二
    gender = Column(String(16), nullable=True)
    birth_date = Column(String(32), nullable=True)          # MVP 用字符串，避免解析失败
    education = Column(String(32), nullable=True)           # 最高学历
    school = Column(String(128), nullable=True)
    major = Column(String(128), nullable=True)
    work_years = Column(Integer, nullable=True)
    skills = Column(JSON, nullable=True)                    # list[str]
    work_history = Column(JSON, nullable=True)              # list[dict]
    summary = Column(Text, nullable=True)                   # LLM 亮点摘要
    resume_text = Column(Text, nullable=True)               # 简历纯文本（搜索/详情展示）
    source = Column(String(32), default="h5_form", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Candidate id={self.id} name={self.name!r}>"
