"""简历相关出入参。"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ResumeOut(BaseModel):
    """简历详情（含解析产物）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: Optional[int] = None
    file_name: str
    file_type: str
    source: str
    parse_status: str
    parse_error: Optional[str] = None
    raw_text: Optional[str] = None
    parsed_json: Optional[dict[str, Any]] = None
    created_at: datetime


class ResumeUploadOut(BaseModel):
    """上传响应：返回任务记录，解析异步执行。"""

    id: int
    file_name: str
    parse_status: str
    message: str = "上传成功，正在后台解析"
