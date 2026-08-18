"""候选人接口测试：列表 / 关键词搜索 / 学历过滤 / 详情 / 删除。"""
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.services.candidate_service import CandidateService
from tests.fakes import DEFAULT_PARSE_RESULT


def _seed_candidates(count: int = 3) -> None:
    """直接通过服务层写入候选人（不走 LLM，测试隔离）。"""
    db = SessionLocal()
    try:
        svc = CandidateService(db)
        for i in range(count):
            data = dict(DEFAULT_PARSE_RESULT)
            data["name"] = f"候选人{i}"
            data["phone"] = f"1380000000{i}"
            data["email"] = f"cand{i}@example.com"
            if i == 1:
                data["education"] = "硕士"
                data["skills"] = ["Go", "Kubernetes"]
            svc.upsert_from_parsed(
                data, source="h5_form", resume_text="熟悉 Python 与 Java 开发"
            )
        db.commit()
    finally:
        db.close()


def test_list_candidates_pagination(client: TestClient) -> None:
    _seed_candidates(3)
    resp = client.get("/api/v1/candidates", params={"page": 1, "size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_search_by_name(client: TestClient) -> None:
    _seed_candidates(3)
    resp = client.get("/api/v1/candidates", params={"q": "候选人1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "候选人1"


def test_search_by_phone(client: TestClient) -> None:
    _seed_candidates(3)
    resp = client.get("/api/v1/candidates", params={"q": "13800000002"})
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["phone"] == "13800000002"


def test_search_by_resume_text(client: TestClient) -> None:
    """关键词能命中简历文本内容。"""
    _seed_candidates(3)
    resp = client.get("/api/v1/candidates", params={"q": "Python"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


def test_filter_by_education(client: TestClient) -> None:
    _seed_candidates(3)
    resp = client.get("/api/v1/candidates", params={"education": "硕士"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "候选人1"


def test_candidate_detail_with_resumes(client: TestClient) -> None:
    db = SessionLocal()
    try:
        cand = CandidateService(db).upsert_from_parsed(
            dict(DEFAULT_PARSE_RESULT), source="h5_form"
        )
        db.add(
            Resume(
                candidate_id=cand.id,
                file_name="张三.docx",
                file_path="2025/08/abc.docx",
                file_type="docx",
                source="h5_form",
                parse_status="done",
                raw_text="张三的简历文本",
                parsed_json=dict(DEFAULT_PARSE_RESULT),
            )
        )
        db.commit()
        candidate_id = cand.id
    finally:
        db.close()

    resp = client.get(f"/api/v1/candidates/{candidate_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "张三"
    assert len(body["resumes"]) == 1
    assert body["resumes"][0]["parse_status"] == "done"


def test_candidate_detail_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/candidates/99999")
    assert resp.status_code == 404


def test_delete_candidate(client: TestClient) -> None:
    db = SessionLocal()
    try:
        cand = CandidateService(db).upsert_from_parsed(
            dict(DEFAULT_PARSE_RESULT), source="h5_form"
        )
        db.commit()
        candidate_id = cand.id
    finally:
        db.close()

    resp = client.delete(f"/api/v1/candidates/{candidate_id}")
    assert resp.status_code == 204

    db = SessionLocal()
    try:
        assert db.get(Candidate, candidate_id) is None
    finally:
        db.close()
