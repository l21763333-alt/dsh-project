"""H5 在线表单收集入口：公开提交 Word 简历（与 /resumes 共用解析管线）。

后续扩展：企微文档 / 小程序收集可在此统一接入（Collector 抽象）。
"""
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.resume import ResumeUploadOut
from app.services.resume_service import ResumeParseError, ResumeService

router = APIRouter()


@router.post("/resume", response_model=ResumeUploadOut, status_code=201)
def collect_resume(
    file: UploadFile = File(..., description="Word 简历文件(.docx)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> ResumeUploadOut:
    """H5 在线表单提交入口：上传 Word 简历 → 后台解析 → 结构化入库。"""
    service = ResumeService(db)
    try:
        resume = service.upload(file, source="h5_form")
    except ResumeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(service.parse, resume.id)
    return ResumeUploadOut(
        id=resume.id, file_name=resume.file_name, parse_status=resume.parse_status
    )
