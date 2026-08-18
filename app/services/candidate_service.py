"""候选人数据管理：字段归一化、去重（手机号/邮箱）、档案维护、关键词检索。"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.candidate import Candidate

logger = logging.getLogger(__name__)

# LLM 结果中允许写入候选人表的字段白名单（防止脏字段入库）
CANDIDATE_FIELDS = {
    "name", "phone", "email", "gender", "birth_date", "education",
    "school", "major", "work_years", "skills", "work_history", "summary",
}

# 学历别名归一化表
EDUCATION_ALIASES = {
    "博士": "博士", "phd": "博士",
    "硕士": "硕士", "研究生": "硕士", "master": "硕士",
    "本科": "本科", "学士": "本科", "bachelor": "本科", "大学本科": "本科",
    "大专": "大专", "专科": "大专", "college": "大专",
    "高中": "高中及以下", "中专": "高中及以下", "高中及以下": "高中及以下",
}


class CandidateService:
    """候选人档案服务：一人一档。"""

    def __init__(self, db: Session):
        self.db = db

    def upsert_from_parsed(
        self,
        parsed: Dict[str, Any],
        source: str,
        resume_text: Optional[str] = None,
    ) -> Candidate:
        """根据 LLM 结构化结果新增或更新候选人（按手机号/邮箱去重）。"""
        normalized = self._normalize(parsed)
        candidate = self._find_by_dedup(normalized)
        if candidate is None:
            fields = {k: v for k, v in normalized.items() if k in CANDIDATE_FIELDS}
            candidate = Candidate(source=source, resume_text=resume_text, **fields)
            self.db.add(candidate)
            logger.info("新建候选人 %s（%s）", candidate.name, source)
        else:
            # 已有档案：用新简历信息补充/更新
            for key, value in normalized.items():
                if key in CANDIDATE_FIELDS and value is not None:
                    setattr(candidate, key, value)
            if resume_text:
                candidate.resume_text = resume_text
            logger.info("候选人 %s 已存在，更新档案", candidate.id)
        self.db.flush()
        return candidate

    def get(self, candidate_id: int) -> Optional[Candidate]:
        """按 ID 查询候选人。"""
        return self.db.get(Candidate, candidate_id)

    def list(
        self,
        page: int = 1,
        size: int = 20,
        q: Optional[str] = None,
        education: Optional[str] = None,
    ) -> List[Candidate]:
        """候选人列表（创建时间倒序，支持关键词与学历过滤）。"""
        query = self._apply_filters(q=q, education=education)
        return (
            query.order_by(Candidate.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

    def count(self, q: Optional[str] = None, education: Optional[str] = None) -> int:
        """候选人总数（与 list 使用相同过滤条件）。"""
        return self._apply_filters(q=q, education=education).count()

    # ---------- 私有 ----------

    def _apply_filters(
        self,
        q: Optional[str] = None,
        education: Optional[str] = None,
    ):
        """关键词(q)匹配 姓名/手机号/邮箱/简历文本；学历精确过滤。"""
        query = self.db.query(Candidate)
        if education:
            query = query.filter(Candidate.education == education)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    Candidate.name.like(pattern),
                    Candidate.phone.like(pattern),
                    Candidate.email.like(pattern),
                    Candidate.resume_text.like(pattern),
                )
            )
        return query

    def _find_by_dedup(self, normalized: Dict[str, Any]) -> Optional[Candidate]:
        """去重：优先手机号精确匹配，其次邮箱精确匹配。"""
        phone = normalized.get("phone")
        if phone:
            hit = self.db.query(Candidate).filter(Candidate.phone == phone).first()
            if hit:
                return hit
        email = normalized.get("email")
        if email:
            hit = self.db.query(Candidate).filter(Candidate.email == email).first()
            if hit:
                return hit
        return None

    def _normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """字段清洗：去空白、学历枚举映射、work_years 转整数、skills 去重。"""
        def _clean(value: Any) -> Any:
            return value.strip() if isinstance(value, str) else value

        name = str(_clean(parsed.get("name")) or "").strip() or "未命名候选人"
        phone = str(_clean(parsed.get("phone")) or "").strip() or None
        email = str(_clean(parsed.get("email")) or "").strip() or None

        education_raw = str(_clean(parsed.get("education")) or "").strip().lower()
        education = EDUCATION_ALIASES.get(education_raw, education_raw or None)

        work_years = parsed.get("work_years")
        try:
            work_years = int(work_years) if work_years is not None else None
        except (TypeError, ValueError):
            work_years = None

        skills = parsed.get("skills") or []
        if not isinstance(skills, list):
            skills = []
        # 大小写不敏感去重（保留首次出现的原始写法）
        seen: set = set()
        deduped: list = []
        for skill in skills:
            key = str(skill).strip().lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(str(skill).strip())
        skills = deduped

        work_history = parsed.get("work_history")
        if not isinstance(work_history, list):
            work_history = None

        return {
            "name": name,
            "phone": phone,
            "email": email,
            "gender": _clean(parsed.get("gender")) or None,
            "birth_date": _clean(parsed.get("birth_date")) or None,
            "education": education,
            "school": _clean(parsed.get("school")) or None,
            "major": _clean(parsed.get("major")) or None,
            "work_years": work_years,
            "skills": skills,
            "work_history": work_history,
            "summary": _clean(parsed.get("summary")) or None,
        }
