"""候选人相关出入参。"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.resume import ResumeOut


class CandidateOut(BaseModel):
    """候选人档案（列表与详情共用）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    education: Optional[str] = None
    school: Optional[str] = None
    major: Optional[str] = None
    work_years: Optional[int] = None
    skills: Optional[List[str]] = None
    work_history: Optional[List[dict[str, Any]]] = None
    summary: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime


class CandidateDetailOut(CandidateOut):
    """候选人详情：含关联简历列表。"""

    resumes: List[ResumeOut] = []
