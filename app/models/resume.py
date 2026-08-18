"""简历模型：原始文件 + 解析中间产物 + LLM 结构化结果。"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True, index=True)
    file_name = Column(String(255), nullable=False)          # 用户上传时的原始文件名
    file_path = Column(String(512), nullable=False)          # 相对 STORAGE_PATH 的存储路径
    file_type = Column(String(16), nullable=False)           # docx
    source = Column(String(32), default="h5_form", nullable=False)
    raw_text = Column(Text, nullable=True)                   # 文档解析出的纯文本
    parsed_json = Column(JSON, nullable=True)                # LLM 结构化提取结果
    parse_status = Column(String(16), default="pending", nullable=False, index=True)
    # pending -> parsing -> done | failed
    parse_error = Column(String(512), nullable=True)
    # 解析管线步骤日志：[{name, status, detail, at}, ...]（前端过程可视化）
    parse_steps = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", back_populates="resumes")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resume id={self.id} file={self.file_name!r} status={self.parse_status}>"
