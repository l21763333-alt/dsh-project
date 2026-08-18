"""简历收集与解析：上传存储 → 文档解析 → LLM 结构化提取 → 候选人落库。"""
import logging
import time
import uuid
from datetime import datetime
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
        resume.parse_steps = self._init_steps(resume)
        db.commit()
        try:
            # 步骤 2：文档解析（python-docx 提取纯文本）
            self._set_step(resume, 1, "running")
            db.commit()
            extractor = get_extractor(f".{resume.file_type}")
            if extractor is None:
                raise ResumeParseError(f"未注册的解析器: .{resume.file_type}")
            abs_path = Path(settings.STORAGE_PATH) / resume.file_path
            result = extractor.extract(str(abs_path))
            if not result.text.strip():
                raise ResumeParseError("文档中未提取到文本内容")
            resume.raw_text = result.text
            self._set_step(resume, 1, "done", f"提取文本 {len(result.text)} 字符")

            # 步骤 3：DeepSeek 大模型结构化提取
            self._set_step(resume, 2, "running")
            db.commit()  # 提交中间状态，前端可实时看到"文档解析完成、LLM 进行中"
            llm = llm or get_llm()
            parsed = llm.chat_json(build_resume_extraction_messages(result.text))
            self._set_step(
                resume, 2, "done",
                f"模型 {settings.LLM_MODEL}，提取 {len(parsed)} 个字段",
            )

            # 步骤 4：候选人入库（归一化 / 去重）
            self._set_step(resume, 3, "running")
            db.commit()
            candidate = CandidateService(db).upsert_from_parsed(
                parsed, source=resume.source, resume_text=result.text
            )
            resume.candidate_id = candidate.id
            resume.parsed_json = parsed
            self._set_step(resume, 3, "done", f"候选人 #{candidate.id}")
            resume.parse_status = "done"
            logger.info("简历 %s 解析完成 → 候选人 %s", resume_id, candidate.id)
        except Exception as exc:  # noqa: BLE001 —— 失败需落库以便前端展示与重试
            # 将当前 running 的步骤标记为 failed（重建列表以确保 SQLAlchemy 检测到变更）
            steps = []
            for step in resume.parse_steps or []:
                step = dict(step)
                if step.get("status") == "running":
                    step["status"] = "failed"
                    step["detail"] = str(exc)[:200]
                steps.append(step)
            resume.parse_steps = steps
            resume.parse_status = "failed"
            resume.parse_error = str(exc)[:500]
            logger.exception("简历 %s 解析失败", resume_id)
        db.commit()
        db.refresh(resume)
        return resume

    # ---------- 解析步骤辅助 ----------

    def _init_steps(self, resume: Resume) -> List[dict]:
        """初始化解析管线步骤（上传已完成，后续步骤待执行）。"""
        now = datetime.now().isoformat(timespec="seconds")
        return [
            {"name": "文件上传", "status": "done",
             "detail": f"{resume.file_name} 已保存", "at": now},
            {"name": "文档解析（python-docx）", "status": "pending", "detail": "", "at": None},
            {"name": "DeepSeek 大模型提取", "status": "pending", "detail": "", "at": None},
            {"name": "候选人入库（归一化/去重）", "status": "pending", "detail": "", "at": None},
        ]

    def _set_step(
        self, resume: Resume, index: int, status: str, detail: str = ""
    ) -> None:
        """更新某一步骤状态与时间戳。

        重建列表并重新赋值 —— 保证 SQLAlchemy 检测到 JSON 列变更并随 commit 持久化。
        """
        steps = list(resume.parse_steps or [])
        if 0 <= index < len(steps):
            updated = dict(steps[index])
            updated["status"] = status
            if detail:
                updated["detail"] = detail
            updated["at"] = datetime.now().isoformat(timespec="seconds")
            steps[index] = updated
            resume.parse_steps = steps

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
