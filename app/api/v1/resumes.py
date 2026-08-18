"""简历接口：上传 / 列表 / 详情 / 重试解析。"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.resume import Resume
from app.schemas.common import Page
from app.schemas.resume import ResumeOut, ResumeUploadOut
from app.services.resume_service import ResumeParseError, ResumeService

router = APIRouter()


@router.post("", response_model=ResumeUploadOut, status_code=201)
def upload_resume(
    file: UploadFile = File(..., description="Word 简历文件(.docx)"),
    source: str = Form("h5_form", description="收集渠道：h5_form/upload/wecom"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> ResumeUploadOut:
    """上传简历 → 后台异步解析 → 结构化落库（H5 在线表单与后台共用）。"""
    service = ResumeService(db)
    try:
        resume = service.upload(file, source=source)
    except ResumeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(service.parse, resume.id)
    return ResumeUploadOut(
        id=resume.id, file_name=resume.file_name, parse_status=resume.parse_status
    )


@router.get("", response_model=Page[ResumeOut])
def list_resumes(
    page: int = 1,
    size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Page[ResumeOut]:
    """简历列表（时间倒序，可按解析状态过滤）。"""
    service = ResumeService(db)
    items = service.list(page=page, size=size, status=status)
    total = service.count(status=status)
    return Page(total=total, page=page, size=size, items=items)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)) -> Resume:
    """简历详情（含解析原文与结构化结果）。"""
    resume = ResumeService(db).get(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="简历不存在")
    return resume


@router.post("/{resume_id}/parse", response_model=ResumeOut)
def parse_resume(resume_id: int, db: Session = Depends(get_db)) -> Resume:
    """手动触发/重试解析（解析失败后修复数据可重试）。"""
    service = ResumeService(db)
    if service.get(resume_id) is None:
        raise HTTPException(status_code=404, detail="简历不存在")
    return service.parse(resume_id)
