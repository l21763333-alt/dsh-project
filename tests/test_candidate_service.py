"""候选人服务单元测试：归一化与去重。"""
from app.core.database import SessionLocal
from app.models.candidate import Candidate
from app.services.candidate_service import CandidateService
from tests.fakes import DEFAULT_PARSE_RESULT


def test_normalize_cleans_fields() -> None:
    """学历别名映射、年限转整数、技能去重。"""
    db = SessionLocal()
    try:
        svc = CandidateService(db)
        raw = {
            "name": "  张三  ",
            "phone": " 13800138000 ",
            "education": "研究生",
            "work_years": "3",
            "skills": ["Python", " python ", "Java", "Java"],
        }
        normalized = svc._normalize(raw)
        assert normalized["name"] == "张三"
        assert normalized["phone"] == "13800138000"
        assert normalized["education"] == "硕士"
        assert normalized["work_years"] == 3
        assert normalized["skills"] == ["Python", "Java"]
    finally:
        db.close()


def test_upsert_dedup_by_phone() -> None:
    """相同手机号重复入库只产生一条候选人档案。"""
    db = SessionLocal()
    try:
        svc = CandidateService(db)
        data = dict(DEFAULT_PARSE_RESULT)
        first = svc.upsert_from_parsed(data, source="h5_form")
        second = svc.upsert_from_parsed(data, source="h5_form")
        assert first.id == second.id
        assert db.query(Candidate).count() == 1
    finally:
        db.close()


def test_upsert_dedup_by_email() -> None:
    """无手机号时按邮箱去重。"""
    db = SessionLocal()
    try:
        svc = CandidateService(db)
        data = dict(DEFAULT_PARSE_RESULT)
        data["phone"] = None
        data["email"] = "same@example.com"
        first = svc.upsert_from_parsed(data, source="h5_form")
        second = svc.upsert_from_parsed(data, source="h5_form")
        assert first.id == second.id
        assert db.query(Candidate).count() == 1
    finally:
        db.close()


def test_missing_name_fallback() -> None:
    """模型未提取到姓名时使用占位名，保证入库不报错。"""
    db = SessionLocal()
    try:
        svc = CandidateService(db)
        data = dict(DEFAULT_PARSE_RESULT)
        data["name"] = ""
        cand = svc.upsert_from_parsed(data, source="h5_form")
        assert cand.name == "未命名候选人"
    finally:
        db.close()
