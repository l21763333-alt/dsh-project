"""候选人接口：列表（关键词搜索）/ 详情 / 删除。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateDetailOut, CandidateOut
from app.schemas.common import Page
from app.services.candidate_service import CandidateService

router = APIRouter()


@router.get("", response_model=Page[CandidateOut])
def list_candidates(
    page: int = 1,
    size: int = 20,
    q: Optional[str] = None,
    education: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Page[CandidateOut]:
    """候选人列表：支持关键词搜索(q)与学历过滤(education)。

    q 匹配：姓名 / 手机号 / 邮箱 / 简历文本（模糊匹配）。
    """
    service = CandidateService(db)
    items = service.list(page=page, size=size, q=q, education=education)
    total = service.count(q=q, education=education)
    return Page(total=total, page=page, size=size, items=items)


@router.get("/{candidate_id}", response_model=CandidateDetailOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)) -> Candidate:
    """候选人详情（含关联简历列表）。"""
    candidate = (
        db.query(Candidate)
        .options(selectinload(Candidate.resumes))
        .filter(Candidate.id == candidate_id)
        .first()
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="候选人不存在")
    return candidate


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)) -> None:
    """删除候选人档案（级联删除关联简历记录）。"""
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="候选人不存在")
    db.delete(candidate)
    db.commit()
