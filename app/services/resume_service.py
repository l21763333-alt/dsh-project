"""简历收集与解析：上传存储 → 文档解析 → LLM 结构化提取 → 候选人落库。"""
import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.extractors.base import get_extractor
from app.ai.llm import LLMClient, get_llm
from app.ai.prompts import build_resume_extraction_messages
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.resume import Resume
from app.services.candidate_service import CandidateService

logger = logging.getLogger(__name__)

# MVP 仅支持 Word(.docx)
SUPPORTED_FILE_TYPES = {".docx"}


class ResumeParseError(Exception):
    """简历解析失败（类型不支持 / 内容为空 / 未注册解析器等）。"""


class ResumeService:
    """简历服务：上传、解析（后台任务安全）、查询。"""

    def __init__(self, db: Session):
        self.db = db

    # ---------- 上传 ----------

    def upload(self, file: UploadFile, source: str = "h5_form") -> Resume:
        """保存文件到本地存储并创建解析任务记录（pending）。

        解析由调用方决定同步/后台执行（见 parse）。
        """
        file_name = file.filename or "unnamed"
        ext = Path(file_name).suffix.lower()
        if ext not in SUPPORTED_FILE_TYPES:
            raise ResumeParseError(
                f"暂不支持的文件类型: {ext or '未知'}，MVP 仅支持 .docx"
            )
        data = file.file.read()
        if not data:
            raise ResumeParseError("上传文件内容为空")

        # 落盘：data/files/YYYY/MM/<uuid>.docx（按时间分目录）
        rel_dir = time.strftime("%Y/%m")
        abs_dir = Path(settings.STORAGE_PATH) / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}{ext}"
        (abs_dir / stored_name).write_bytes(data)

        resume = Resume(
            file_name=file_name,
            file_path=f"{rel_dir}/{stored_name}",
            file_type=ext.lstrip("."),
            source=source,
            parse_status="pending",
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    # ---------- 解析 ----------

    def parse(self, resume_id: int, llm: Optional[LLMClient] = None) -> Resume:
        """解析管线（同步）：pending → parsing → done | failed。

        自建数据库会话执行 —— 可安全用于 BackgroundTasks
        （请求级 session 在响应后已关闭的场景）。
        """
        db = SessionLocal()
        try:
            return self._parse_with_db(db, resume_id, llm)
        finally:
            db.close()

    def _parse_with_db(
        self, db: Session, resume_id: int, llm: Optional[LLMClient] = None
    ) -> Resume:
        resume = db.get(Resume, resume_id)
        if resume is None:
            raise ResumeParseError(f"简历不存在: id={resume_id}")
        if resume.parse_status == "parsing":
            return resume
        resume.parse_status = "parsing"
        resume.parse_error = None
        db.commit()
        try:
            extractor = get_extractor(f".{resume.file_type}")
            if extractor is None:
                raise ResumeParseError(f"未注册的解析器: .{resume.file_type}")
            abs_path = Path(settings.STORAGE_PATH) / resume.file_path
            result = extractor.extract(str(abs_path))
            if not result.text.strip():
                raise ResumeParseError("文档中未提取到文本内容")
            resume.raw_text = result.text

            # LLM 结构化提取（DeepSeek；测试注入 FakeLLM，不产生真实调用）
            llm = llm or get_llm()
            parsed = llm.chat_json(build_resume_extraction_messages(result.text))

            candidate = CandidateService(db).upsert_from_parsed(
                parsed, source=resume.source, resume_text=result.text
            )
            resume.candidate_id = candidate.id
            resume.parsed_json = parsed
            resume.parse_status = "done"
            logger.info("简历 %s 解析完成 → 候选人 %s", resume_id, candidate.id)
        except Exception as exc:  # noqa: BLE001 —— 失败需落库以便前端展示与重试
            resume.parse_status = "failed"
            resume.parse_error = str(exc)[:500]
            logger.exception("简历 %s 解析失败", resume_id)
        db.commit()
        db.refresh(resume)
        return resume

    # ---------- 查询 ----------

    def get(self, resume_id: int) -> Optional[Resume]:
        """按 ID 查询简历。"""
        return self.db.get(Resume, resume_id)

    def list(
        self,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
    ) -> List[Resume]:
        """简历列表（时间倒序，可按解析状态过滤）。"""
        query = self.db.query(Resume)
        if status:
            query = query.filter(Resume.parse_status == status)
        return (
            query.order_by(Resume.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

    def count(self, status: Optional[str] = None) -> int:
        """简历总数（可按解析状态过滤）。"""
        query = self.db.query(Resume)
        if status:
            query = query.filter(Resume.parse_status == status)
        return query.count()
