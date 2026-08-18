"""ORM 模型包：模型在此集中注册（init_db 导入本包后 create_all 建表）。"""
from app.models.candidate import Candidate
from app.models.resume import Resume

__all__ = ["Candidate", "Resume"]
