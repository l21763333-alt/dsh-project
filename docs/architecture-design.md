# Recruit AI — 招聘数据智能化落地方案（架构设计 v0.1）

> 本文档只描述**架构与框架**，不含具体业务逻辑实现。业务逻辑在确认后按阶段实现，
> 每个功能通过测试后以 PR 方式提交至 GitHub 公开仓库。

---

## 0. 技术选型（最小成本原则）

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 | AI 生态最成熟，LLM/OCR/ASR/Embedding 集成成本最低 |
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts + Pinia | 中文企业后台生态成熟，看板/ECharts 开箱即用 |
| 数据库 | MySQL 8.0（需求指定）；ORM 层保持 DB 无关，可无缝换 PostgreSQL | 最小成本，云上 MySQL 便宜 |
| 向量检索 | FAISS（本地文件索引，零额外成本）；预留 Milvus / pgvector 接口 | 数据量小，FAISS 足够 |
| 缓存/队列 | Redis（Celery broker + 缓存）；最小阶段可先用 MySQL 表兜底 | 异步任务（OCR/Embedding/通知） |
| LLM | OpenAI 兼容协议客户端，`LLM_API_KEY` 等全部走环境变量（DeepSeek/Qwen/OpenAI 可切换） | 成本可控、厂商无关 |
| OCR | PaddleOCR（本地免费） | 最小成本；可换云端 |
| ASR | faster-whisper（本地） | 面评语音转写，最小成本 |
| 文件存储 | 本地磁盘（`STORAGE_BACKEND=local`），预留 OSS/S3 | 单机部署零成本 |
| 部署 | 单机 Docker Compose | 一台 2C4G 即可起步 |

---

## 1. 总体架构

```
┌────────────────────────────────────────────────────────────┐
│ 客户端：Web 后台(Vue3) / 企业微信应用+H5 / 在线表单(收集)      │
└───────────────────────────┬────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              API 层（FastAPI, /api/v1）                     │
│   认证鉴权(JWT+RBAC) · 路由分发 · 异常处理 · 审计日志          │
└───────────────────────────┬────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│            Recruit AI Agent（智能入口，可选）                 │
│        意图识别 → 任务编排 → Tool Calling → 结果组装          │
└───────────────────────────┬────────────────────────────────┘
                            ▼
┌──────────┬──────────┬──────────┬──────────┬───────────────┐
│ 简历服务  │ 候选人服务 │ 岗位服务  │ 匹配服务  │ 查询服务        │
│ 面试服务  │ 通知服务   │ 分析服务  │ 企微服务  │ (业务层 Services)│
└──────────┴──────────┴──────────┴──────────┴───────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│                  AI 能力层（可插拔）                         │
│  LLM(厂商无关) · Embedding · OCR · ASR · 文档解析 · RAG     │
└───────────────────────────┬────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│            数据层：MySQL · Redis · 对象存储 · FAISS 向量      │
└────────────────────────────────────────────────────────────┘
```

---

## 2. 文件 / 目录结构

```
recruit-ai/
├── README.md
├── .env.example                  # 环境变量模板（含 LLM_API_KEY 等，严禁提交真实 Key）
├── .gitignore
├── pyproject.toml                # 后端依赖与工具链
├── alembic.ini                   # 数据库迁移
├── docker-compose.yml            # mysql + redis + app + web
├── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml                # PR 自动跑 pytest + lint（质量门禁）
├── scripts/
│   ├── init_db.sh
│   └── dev.sh
├── app/                          # ── 后端（FastAPI）──
│   ├── main.py                   # ★ 主入口
│   ├── core/                     # 配置 / 安全 / 基础设施
│   │   ├── config.py             # 环境变量集中管理（API Key 全部在此读取）
│   │   ├── database.py           # SQLAlchemy engine / session
│   │   ├── security.py           # JWT、密码哈希、RBAC 依赖
│   │   ├── redis.py
│   │   └── logging.py
│   ├── api/
│   │   ├── deps.py               # 通用依赖注入（db / current_user / 权限）
│   │   └── v1/
│   │       ├── router.py         # 聚合所有子路由
│   │       ├── auth.py           # 登录/刷新
│   │       ├── resumes.py        # 简历上传/解析
│   │       ├── candidates.py     # 候选人 CRUD/去重/合并
│   │       ├── jobs.py           # 岗位/JD
│   │       ├── matching.py       # 匹配
│   │       ├── search.py         # 智能查询
│   │       ├── interviews.py     # 面试/面评
│   │       ├── analytics.py      # 数据看板
│   │       ├── notifications.py  # 通知配置/记录
│   │       ├── agent.py          # Agent 对话入口
│   │       └── collect.py        # 在线表单/小程序收集入口（公开接口）
│   ├── models/                   # SQLAlchemy ORM 模型
│   │   ├── base.py
│   │   ├── user.py               # 用户/角色/权限
│   │   ├── candidate.py          # 候选人
│   │   ├── resume.py             # 简历（原始文件 + 解析结果）
│   │   ├── job.py                # 岗位/JD
│   │   ├── application.py        # 投递/流程状态机
│   │   ├── interview.py          # 面试 + 面评
│   │   ├── notification.py       # 通知记录
│   │   └── audit.py              # 审计日志
│   ├── schemas/                  # Pydantic 出入参模型
│   │   ├── common.py             # 分页/通用响应
│   │   ├── candidate.py / resume.py / job.py
│   │   ├── matching.py / search.py
│   │   ├── interview.py / analytics.py / auth.py
│   ├── services/                 # ── 业务层（核心，职责单一）──
│   │   ├── base.py               # 通用 CRUD 基类
│   │   ├── resume_service.py     # 简历收集与提取
│   │   ├── candidate_service.py  # 候选人数据管理/去重
│   │   ├── job_service.py        # JD 解析/岗位管理
│   │   ├── matching_service.py   # 双相似度匹配
│   │   ├── search_service.py     # HR 智能查询
│   │   ├── interview_service.py  # 面试/面评/语音转写
│   │   ├── analytics_service.py  # 招聘数据分析
│   │   ├── notification_service.py # 多通道通知编排
│   │   └── wecom_service.py      # 企业微信 API 封装
│   ├── ai/                       # ── AI 能力层（全部可插拔）──
│   │   ├── llm.py                # LLM 客户端抽象 + 工厂（厂商无关）
│   │   ├── embedding.py          # 向量化
│   │   ├── ocr.py                # OCR 抽象（默认 PaddleOCR）
│   │   ├── asr.py                # ASR 抽象（默认 faster-whisper）
│   │   ├── prompts.py            # 提示词模板集中管理
│   │   ├── extractors/           # 文档解析器（按文件类型扩展）
│   │   │   ├── base.py           # DocumentExtractor 抽象基类
│   │   │   ├── pdf.py
│   │   │   ├── docx.py
│   │   │   └── image.py          # 图片简历 → OCR
│   │   └── vector/               # 向量库抽象
│   │       ├── base.py           # VectorStore 接口
│   │       ├── faiss_store.py    # 默认实现（本地零成本）
│   │       └── pgvector_store.py # 预留实现
│   ├── agent/                    # ── Recruit AI Agent ──
│   │   ├── agent.py              # 编排器：意图→工具→回复
│   │   ├── intent.py             # 意图识别与槽位抽取
│   │   ├── tools.py              # 工具注册表（扩展点）
│   │   └── memory.py             # 会话记忆（Redis）
│   ├── worker/                   # ── 异步任务 ──
│   │   ├── celery_app.py
│   │   └── tasks/
│   │       ├── resume_tasks.py   # 异步解析简历
│   │       ├── embedding_tasks.py
│   │       └── notify_tasks.py   # 异步推送通知
│   └── utils/
│       ├── excel.py              # 导出 Excel（对接腾讯文档/在线表格）
│       ├── text.py               # 文本归一化（去重用）
│       └── time.py
├── web/                          # ── 前端（Vue3）──
│   ├── package.json / vite.config.ts / tsconfig.json
│   └── src/
│       ├── main.ts / App.vue
│       ├── api/                  # axios 封装（token 注入、错误拦截）
│       ├── router/               # 路由 + 守卫（权限）
│       ├── stores/               # Pinia（user / candidate / app）
│       ├── views/
│       │   ├── Dashboard.vue     # 数据看板（ECharts）
│       │   ├── resumes/          # 简历列表/详情/解析状态
│       │   ├── candidates/       # 候选人管理
│       │   ├── jobs/             # 岗位与 JD
│       │   ├── matching/         # 匹配结果（相关度展示）
│       │   ├── interviews/       # 面试排期/面评录入
│       │   ├── search/           # 智能查询对话页
│       │   └── settings/         # 通知配置/权限管理
│       └── components/
├── tests/                        # ── 测试（PR 质量门禁）──
│   ├── conftest.py               # 测试夹具（内存 DB / 假 LLM）
│   ├── unit/                     # 单测：归一化/匹配算法/状态机
│   ├── integration/              # 服务层测试（SQLite/MySQL 测试库）
│   └── api/                      # 接口测试（TestClient）
└── docs/
    ├── architecture-design.md    # 本文档
    └── api.md                    # 接口文档
```

---

## 3. 数据模型（核心表设计）

```
users(id, username, password_hash, name, wecom_userid, role_id, status)
roles(id, name, permissions JSON)                    # RBAC：permission 码列表

candidates(id, name, phone, email, gender, birth_date,
           education, school, major, work_years,      # 归一化后的结构化信息
           skills JSON, work_history JSON, summary,
           resume_text,                               # 清洗后的全文（供查询/向量化）
           dedup_key,                                 # 去重指纹（手机号/邮箱/归一化姓名）
           source,                                    # 收集渠道：form|wecom|miniapp|upload
           created_at, updated_at)

resumes(id, candidate_id FK, file_name, file_url, file_type,
        ocr_text, parsed_json JSON,                   # LLM 抽取的结构化结果
        parse_status,                                 # pending|parsing|done|failed
        parse_error, created_at)

jobs(id, title, department, location, jd_text,
     requirements JSON,                               # LLM 解析出的硬性要求
     status, embedding_id, created_at)

job_applications(id, candidate_id FK, job_id FK,
                 source,                              # 简历投递/HR 录入/内推
                 status,                              # 状态机流转（见下）
                 match_score, match_detail JSON,      # 匹配分 + 双分详情
                 created_at, updated_at)

# 招聘流程状态机（可配置，存常量表或代码枚举）
# 投递→筛选→初面→复试→HR面→Offer→入职 | 淘汰

interviews(id, application_id FK, round, type, interviewer_id,
           scheduled_at, status, record_url,          # 录音/录像
           transcript,                                # ASR 转写文本
           summary,                                   # LLM 面评摘要
           created_at)

interview_reviews(id, interview_id FK, reviewer_id,   # 业务人员面评
                  rating, pros, cons, suggestion, tags JSON, created_at)

notifications(id, channel, target, title, content, biz_type,
              status, sent_at, error)                 # 微信/邮件/站内

audit_logs(id, user_id, action, target_type, target_id,
           detail JSON, ip, created_at)               # 安全审计
```

---

## 4. 模块职责说明

| 模块 | 职责 | 关键点 |
|---|---|---|
| `app/core` | 配置、DB 会话、JWT/RBAC、日志 | API Key 全部经环境变量注入，禁止硬编码 |
| `app/api/v1` | HTTP 层：参数校验、鉴权、调服务 | 薄控制器，无业务逻辑 |
| `app/services/*` | 业务逻辑，可被 API / Agent / Worker 复用 | 核心层，职责单一 |
| `app/ai/*` | 与 AI 厂商解耦的能力封装 | 换模型/换 OCR 不改业务代码 |
| `app/agent/*` | 意图识别 + 工具编排 | 自然语言入口，工具即服务方法 |
| `app/worker/*` | 耗时任务异步化 | 解析/向量化/通知不阻塞请求 |
| `web/*` | 看板、简历查询、面评录入等 UI | 与后端通过 REST 通信 |

### 各 Service 职责明细

- **resume_service**：文件上传 → 文档解析(extractors) → OCR(图片/扫描件) → LLM 结构化抽取 → 落库 `resumes` + `candidates`。
- **candidate_service**：字段归一化（电话/邮箱/学历枚举）、`dedup_key` 指纹去重、相似候选人合并。
- **job_service**：JD 文本 → LLM 解析硬性要求（技能/年限/学历/城市）→ 向量化 → 岗位 CRUD。
- **matching_service**：**双相似度** = 语义分（Embedding 余弦，候选人与 JD 双向） + 规则分（技能重合、年限、学历、城市权重打分）→ 加权合成 `final_score`，输出可解释 detail。
- **search_service**：关键词检索（MySQL LIKE + 全文索引）+ 自然语言查询（LLM 生成查询计划 → 白名单校验 → 执行）→ 结果统一返回。
- **interview_service**：排期、录音上传 → ASR 转写 → 面评 CRUD（业务人员）→ LLM 摘要；状态联动 `job_applications`。
- **analytics_service**：简历量趋势、漏斗转化、通过率、招聘周期、岗位进度；按 `ReportGenerator` 注册表扩展新口径。
- **notification_service**：事件（状态变更/面试提醒/面评完成）→ 按配置路由到微信/邮件/站内。
- **wecom_service**：企业微信 access_token、应用消息、群机器人 webhook、OAuth 登录、文档收集。

---

## 5. 代码框架（骨架，仅签名与注释）

### 5.1 主入口 `app/main.py`

```python
"""应用主入口：FastAPI 应用工厂。启动方式见 scripts/dev.sh"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """应用工厂：测试可重复创建独立实例（隔离配置）"""
    setup_logging(settings.DEBUG)
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url="/api/docs",          # Swagger 文档
        openapi_url="/api/openapi.json",
    )
    # CORS：前端(web) 与 企业微信 H5 跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.API_PREFIX)  # /api/v1
    register_startup(app)    # 启动钩子：建表/加载向量索引（幂等）
    register_handlers(app)   # 全局异常 → 统一响应体
    return app


def register_startup(app: FastAPI) -> None:
    """启动时：初始化 DB、FAISS 索引、预加载 LLM 配置"""
    from app.core.database import init_db
    from app.ai.vector import init_vector_store
    app.add_event_handler("startup", init_db)
    app.add_event_handler("startup", init_vector_store)


def register_handlers(app: FastAPI) -> None:
    """全局异常处理器：业务异常/校验异常/未知异常 → 统一 JSON 格式"""
    ...


app = create_app()  # uvicorn 入口：uvicorn app.main:app
```

### 5.2 配置 `app/core/config.py`

```python
"""所有配置从环境变量读取（开发用 .env，生产注入真实环境变量）。
API Key 严禁硬编码/提交仓库。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 基础
    PROJECT_NAME: str = "Recruit AI"
    DEBUG: bool = False
    SECRET_KEY: str                    # JWT 签名密钥（必填）
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    API_PREFIX: str = "/api/v1"

    # 数据库（需求指定 MySQL；整体可覆盖为 PostgreSQL 连接串）
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "recruit"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "recruit_ai"
    DATABASE_URL: str = ""             # 非空则优先（DB 无关的关键）

    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # ── LLM：核心 API Key，全部走环境变量 ──
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"   # 兼容 OpenAI 协议
    LLM_MODEL: str = "deepseek-chat"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = ""          # 如 bge-m3（本地）或云端 embedding
    LLM_TIMEOUT: float = 60.0
    LLM_MAX_TOKENS: int = 4096

    # 企业微信
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_WEBHOOK_URL: str = ""        # 群机器人 webhook（用于群通知）

    # 文件存储（可插拔：local | oss | s3）
    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "./data/files"
    STORAGE_PUBLIC_BASE: str = ""

    # 向量（可插拔：faiss | pgvector | milvus）
    VECTOR_BACKEND: str = "faiss"
    VECTOR_INDEX_PATH: str = "./data/vector"

    # OCR / ASR
    OCR_BACKEND: str = "paddle"        # paddle | cloud
    ASR_BACKEND: str = "whisper"       # whisper | cloud
    ASR_MODEL: str = "small"           # faster-whisper 模型档位


settings = Settings()  # 全局单例，业务代码统一 from app.core.config import settings
```

### 5.3 通用 CRUD 基类 `app/services/base.py`

```python
"""通用 CRUD 基类：所有业务 Service 继承，统一分页/异常/审计入口"""
from typing import Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")
CreateT = TypeVar("CreateT")
UpdateT = TypeVar("UpdateT")


class BaseService(Generic[ModelT, CreateT, UpdateT]):
    """职责：模型 CRUD + 分页 + 审计；子类只补充领域逻辑"""

    model: type[ModelT]  # 子类声明，如 Candidate

    def __init__(self, db: AsyncSession, current_user=None):
        self.db = db

    async def get(self, obj_id: int) -> ModelT: ...
    async def list(self, filters: dict, page: int, size: int) -> Page[ModelT]: ...
    async def create(self, data: CreateT) -> ModelT: ...
    async def update(self, obj_id: int, data: UpdateT) -> ModelT: ...
    async def delete(self, obj_id: int) -> None: ...
    async def _audit(self, action: str, target_id, detail: dict) -> None:
        """写审计日志（安全审计统一入口）"""
        ...
```

### 5.4 简历服务 `app/services/resume_service.py`

```python
"""简历收集与提取：上传 → 解析 → LLM 抽取 → 入库"""
from app.ai.extractors.base import DocumentExtractor


class ResumeService(BaseService):
    """职责：简历文件的接收、解析管线编排、结构化结果落库"""

    async def upload(self, file: UploadFile, source: str = "upload") -> Resume:
        """1) 保存原始文件到存储后端；2) 创建 resume 记录(parse_status=pending)；
           3) 投递异步解析任务(worker)；4) 返回记录"""
        ...

    async def parse(self, resume_id: int) -> ParseResult:
        """解析管线（同步版，供 worker 调用）：
           1. extractors 按 file_type 取解析器 → 文本/图片字节
           2. OCR（扫描件/图片）→ 文本
           3. LLM 结构化抽取（见 prompts.py：resume_extraction）
           4. 写回 ocr_text / parsed_json，状态置 done/failed
           5. 回调 candidate_service.upsert_from_resume() 生成候选人
           6. 触发 embedding 任务（供检索/匹配）"""
        ...

    async def link_candidate(self, resume_id: int, candidate_id: int) -> None:
        """人工/自动关联到已有候选人"""
        ...
```

### 5.5 候选人服务 `app/services/candidate_service.py`

```python
"""候选人数据管理：归一化、去重、合并"""
class CandidateService(BaseService):
    """职责：维护候选人唯一档案（一人多简历、多投递）"""

    async def upsert_from_resume(self, parsed: dict, source: str) -> Candidate:
        """1) 字段归一化(normalize)；2) 计算 dedup_key；
           3) 命中已有候选人则合并简历，否则新建"""
        ...

    async def find_duplicates(self, candidate_id: int) -> list[Candidate]:
        """去重：优先精确指纹(dedup_key)，辅以姓名+电话/邮箱/embedding 相似度"""
        ...

    async def merge(self, primary_id: int, dup_ids: list[int]) -> Candidate:
        """合并重复档案：简历/投递/面试记录迁移到主档案，软删除重复项"""
        ...

    def _normalize(self, raw: dict) -> dict:
        """电话/邮箱/学历枚举/城市等字段清洗统一（纯函数，便于单测）"""
        ...
```

### 5.6 岗位服务 `app/services/job_service.py`

```python
"""岗位/JD 管理：JD 解析、岗位 CRUD、向量化"""
class JobService(BaseService):
    """职责：把非结构化 JD 变成结构化要求，供匹配与筛选使用"""

    async def create_from_jd(self, jd_text: str, meta: dict) -> Job:
        """1) LLM 解析 JD → requirements{skills, years_min, education, city, keywords}
           2) embedding 岗位向量；3) 落库"""
        ...

    async def parse_jd(self, jd_text: str) -> JobRequirement:
        """JD 结构化抽取（LLM，JSON Schema 约束输出）"""
        ...
```

### 5.7 匹配服务 `app/services/matching_service.py`

```python
"""候选人-岗位匹配：双相似度（语义 + 规则）"""
class MatchingService:
    """职责：产出可解释的匹配分，供「HR 查询简历相关度」与 Agent 使用"""

    async def match_pair(self, candidate_id: int, job_id: int) -> MatchingResult:
        """计算单对匹配分"""
        ...

    async def match_candidate_to_jobs(self, candidate_id: int, top_k: int = 10
                                      ) -> list[MatchingResult]: ...
    async def match_job_to_candidates(self, job_id: int, top_k: int = 20
                                      ) -> list[MatchingResult]: ...

    async def _semantic_score(self, c_emb, j_emb) -> float:
        """语义分：候选人简历向量 vs JD 向量（cosine，双向取均值）"""
        ...

    async def _rule_score(self, candidate: Candidate, req: JobRequirement) -> float:
        """规则分：技能重合率 / 年限匹配 / 学历满足 / 城市匹配，加权求和（权重可配置）"""
        ...


class MatchingResult(BaseModel):
    candidate_id: int
    job_id: int
    semantic_score: float   # 语义相似度 0~1
    rule_score: float       # 规则相似度 0~1
    final_score: float      # 加权合成（用于排序展示）
    detail: dict            # 可解释明细：命中的技能、年限差等
```

### 5.8 智能查询服务 `app/services/search_service.py`

```python
"""HR 智能查询：关键词 + 自然语言 → 结构化过滤/向量召回/统计"""
class SearchService:
    """职责：把自然语言问句转成安全、可执行的查询，并返回统一结果"""

    async def keyword_search(self, q: str, filters: dict, page: int,
                             size: int) -> Page[Candidate]:
        """LIKE/全文索引 + 字段过滤（电话、技能、学历等）"""
        ...

    async def nl_search(self, question: str) -> SearchResult:
        """1) LLM 把问句转成查询计划 JSON（意图+条件+排序）
           2) 白名单校验（只允许查询白名单字段，防注入）
           3) 执行 → 向量召回或 SQL → 返回结构化结果 + 自然语言说明"""
        ...

    async def nl_stats(self, question: str) -> dict:
        """统计类问答（如：本月简历量？平均招聘周期？）→ analytics_service"""
        ...
```

### 5.9 面试服务 `app/services/interview_service.py`

```python
"""面试与面评：排期、录音转写、面评录入、LLM 摘要"""
class InterviewService:
    """职责：面试全生命周期 + 面评沉淀（业务人员参与）"""

    async def schedule(self, application_id: int, round_no: int,
                       interviewer_id: int, scheduled_at: datetime) -> Interview:
        """排期 → 通知面试官/候选人（走 notification_service）"""
        ...

    async def upload_record(self, interview_id: int, audio: UploadFile) -> Interview:
        """保存录音 → 异步 ASR 转写 → transcript 落库"""
        ...

    async def add_review(self, interview_id: int, reviewer_id: int,
                         review: ReviewCreate) -> InterviewReview:
        """业务人员面评：评分/优点/顾虑/建议/标签（文字或语音转写）"""
        ...

    async def summarize(self, interview_id: int) -> str:
        """LLM 基于 transcript + reviews 生成结构化面评摘要"""
        ...

    async def complete(self, interview_id: int, passed: bool) -> None:
        """面试结论 → 联动 job_applications 状态机 + 通知"""
        ...
```

### 5.10 数据分析服务 `app/services/analytics_service.py`

```python
"""招聘数据分析：统计口径按注册表扩展"""
class AnalyticsService:
    """职责：聚合统计，输出看板数据（前端 ECharts 直接消费）"""

    async def funnel(self, date_range: DateRange) -> FunnelData:
        """漏斗：简历量→筛选→初面→复试→Offer→入职 各环节人数与转化率"""
        ...

    async def resume_volume(self, date_range: DateRange) -> TimeSeries:
        """简历量趋势（按天/周/月，按渠道分组）"""
        ...

    async def pass_rate(self, stage: str, date_range: DateRange) -> float: ...
    async def hire_cycle(self, date_range: DateRange) -> dict:
        """平均招聘周期：投递→入职 中位数/平均天数"""
        ...

    async def job_progress(self, job_id: int) -> JobProgress:
        """单岗位进度：当前阶段、各阶段人数、匹配中的候选人"""
        ...

    # 扩展点：新统计口径 = 实现 ReportGenerator 并注册
    _reports: dict[str, ReportGenerator] = {}

    @classmethod
    def register_report(cls, name: str, generator: ReportGenerator) -> None: ...
    async def report(self, name: str, params: dict) -> Report: ...
```

### 5.11 企业微信服务 `app/services/wecom_service.py`

```python
"""企业微信集成：消息通知、OAuth 登录、群机器人、文档收集"""
class WeComService:
    """职责：屏蔽企业微信 API 细节，统一给业务方消息/身份能力"""

    async def get_access_token(self) -> str:
        """应用 access_token（Redis 缓存，提前刷新）"""
        ...

    async def send_app_message(self, user_ids: list[str], title: str,
                               content: str, url: str | None = None) -> None:
        """应用消息推送（HR/面试官收到流程提醒）"""
        ...

    async def send_webhook(self, content: str,
                           mentioned_list: list[str] | None = None) -> None:
        """群机器人通知（招聘群内播报）"""
        ...

    async def get_user_by_code(self, code: str) -> WeComUser:
        """扫码/OAuth 登录换取用户身份"""
        ...

    async def notify_interview(self, interview_id: int) -> None:
        """面试提醒卡片（候选人/面试官双端）"""
        ...
```

### 5.12 通知服务 `app/services/notification_service.py`

```python
"""多通道通知编排：通道可插拔（微信/邮件/短信/站内）"""
class NotificationChannel(ABC):
    """扩展点：新增渠道（如邮件）只需实现本接口并注册"""
    name: str
    @abstractmethod
    async def send(self, target: str, title: str, content: str, **kwargs) -> None: ...


class NotificationService:
    """职责：业务事件 → 按规则路由到多个 channel → 记录投递状态"""

    def __init__(self, channels: dict[str, NotificationChannel]): ...

    async def notify(self, event: NotificationEvent) -> None:
        """根据事件类型+规则选 channel 发送，写 notifications 表"""
        ...

    async def on_application_status_change(self, application_id: int,
                                           from_stage: str, to_stage: str) -> None:
        """状态变更通知：HR/候选人（企微消息 + 群播报）"""
        ...
```

### 5.13 LLM 能力抽象 `app/ai/llm.py`

```python
"""LLM 客户端抽象：厂商无关（OpenAI 兼容协议），Key 从环境变量读取"""
class LLMClient(ABC):
    """扩展点：新增厂商（Claude/Gemini 等）实现本接口并在工厂注册"""

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str: ...
    @abstractmethod
    async def chat_json(self, messages: list[dict], schema: dict) -> dict:
        """结构化输出：JSON Schema 约束，供 JD 解析/简历抽取/查询计划"""
        ...
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAICompatibleClient(LLMClient):
    """默认实现：DeepSeek/Qwen/OpenAI 均可（改 base_url/model 即切换）"""

    def __init__(self, api_key: str, base_url: str, model: str):
        # 所有密钥来自 settings（环境变量）
        ...


def get_llm() -> LLMClient:
    """工厂：按 settings.LLM_* 返回实现（单例缓存）"""
    ...
```

### 5.14 OCR / ASR `app/ai/ocr.py` `app/ai/asr.py`

```python
class OCRService:
    """OCR 抽象：默认 PaddleOCR 本地免费，可换云端"""
    async def extract_text(self, image_bytes: bytes) -> str: ...


class ASRService:
    """语音转写：默认 faster-whisper 本地，可换云端 API"""
    async def transcribe(self, audio_path: str, lang: str = "zh") -> str: ...
```

### 5.15 文档解析器 `app/ai/extractors/base.py`

```python
class DocumentExtractor(ABC):
    """扩展点：新增简历格式（.xlsx/.html/.md）只需新增子类并注册"""
    supported_ext: tuple[str, ...]

    @abstractmethod
    async def extract(self, file_path: str) -> ExtractResult:
        """返回 {text, images[]}：text 供 LLM 抽取，images 供 OCR"""
        ...


# 注册表：{ext: extractor_class}
EXTRACTORS: dict[str, type[DocumentExtractor]] = {}


def register_extractor(cls: type[DocumentExtractor]) -> type[DocumentExtractor]:
    """装饰器注册：@register_extractor class PdfExtractor(...)"""
    ...


def get_extractor(ext: str) -> DocumentExtractor | None: ...
```

### 5.16 向量库抽象 `app/ai/vector/base.py`

```python
class VectorStore(ABC):
    """扩展点：FAISS(默认)/Milvus/pgvector 可切换"""
    @abstractmethod
    async def upsert(self, collection: str, id: str, vector: list[float],
                     payload: dict) -> None: ...
    @abstractmethod
    async def search(self, collection: str, vector: list[float],
                     top_k: int, filter: dict | None = None) -> list[VectorHit]: ...
    @abstractmethod
    async def delete(self, collection: str, id: str) -> None: ...


def get_vector_store() -> VectorStore:
    """按 settings.VECTOR_BACKEND 返回实现"""
    ...
```

### 5.17 Agent 编排 `app/agent/agent.py` `app/agent/tools.py`

```python
"""Recruit AI Agent：自然语言入口，意图识别 + Tool Calling"""
class Tool(Protocol):
    """扩展点：每新增一个 AI 能力 = 实现一个 Tool 并注册"""
    name: str
    description: str                       # 供 LLM 理解何时调用
    parameters_schema: dict                # JSON Schema（function calling）
    async def run(self, **kwargs) -> Any: ...


class ToolRegistry:
    """工具注册表：@register_tool 装饰器注册，集中导出给 LLM"""
    _tools: dict[str, Tool] = {}
    @classmethod
    def register(cls, tool: Tool) -> None: ...
    @classmethod
    def all_schemas(cls) -> list[dict]:
        """返回所有工具的 function schemas（喂给 LLM）"""
        ...
    @classmethod
    def get(cls, name: str) -> Tool: ...


class RecruitAgent:
    """编排器：处理 HR 的自然语言请求"""

    def __init__(self, llm: LLMClient, tools: ToolRegistry, memory): ...

    async def handle(self, user_message: str, user) -> AgentResponse:
        """流程：
        1. intent.py 识别意图（查候选人/匹配/统计/排期/通知…）
        2. 结合 tools.all_schemas() 让 LLM 选工具并生成参数（function calling）
        3. 参数校验 → 执行 tool.run()
        4. LLM 把结果组装成自然语言回复 + 附带结构化数据（前端渲染）"""
        ...
```

内置工具清单（首批）：`search_candidates`、`get_candidate_detail`、`match_job_candidates`、`query_stats`、`create_interview`、`add_review`、`send_wecom_notify`。

### 5.18 异步任务 `app/worker/tasks/`

```python
# resume_tasks.py
@celery_app.task
def parse_resume_task(resume_id: int):   # 异步解析简历（OCR+LLM）
    ...

# embedding_tasks.py
@celery_app.task
def embed_candidate_task(candidate_id: int): ...   # 候选人向量化

# notify_tasks.py
@celery_app.task
def push_notification_task(notification_id: int): ...  # 异步推送
```

### 5.19 路由聚合 `app/api/v1/router.py`

```python
"""聚合所有子路由：/api/v1 前缀下按模块挂载"""
api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["简历"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["候选人"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["岗位"])
api_router.include_router(matching.router, prefix="/matching", tags=["匹配"])
api_router.include_router(search.router, prefix="/search", tags=["智能查询"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["面试"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["数据看板"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["通知"])
api_router.include_router(agent.router, prefix="/agent", tags=["AI 助手"])
api_router.include_router(collect.router, prefix="/collect", tags=["简历收集"])
```

---

## 6. 扩展接口设计（扩展点汇总）

| 扩展点 | 抽象/机制 | 新增能力的方式 |
|---|---|---|
| LLM 厂商 | `LLMClient` + `get_llm()` 工厂 | 新实现类 + 环境变量切换，业务零改动 |
| 文档格式 | `DocumentExtractor` + `@register_extractor` | 新增 .xlsx/.html 解析器，一行注册 |
| OCR / ASR | `OCRService` / `ASRService` 抽象 | 本地↔云端切换只改配置 |
| 向量库 | `VectorStore` + `get_vector_store()` | FAISS→Milvus/pgvector 换实现 |
| 通知渠道 | `NotificationChannel` | 邮件/短信/钉钉各实现一个类 |
| 存储后端 | `StorageBackend`（local/OSS/S3） | 云存储切换不改业务 |
| Agent 工具 | `Tool` + `ToolRegistry` | 每个新 AI 能力 = 一个 Tool 类 |
| 统计口径 | `ReportGenerator` + `register_report` | 新报表 = 新生成器 + 注册 |
| 收集渠道 | `Collector`（表单/小程序/企微文档） | 新渠道接入统一 `collect` 入口 |
| 流程状态机 | `ApplicationStatusMachine`（可配置常量） | 调整流程阶段不动代码结构 |

> 设计原则：**依赖抽象不依赖实现**；所有外部系统（LLM/存储/通知/向量）通过接口 + 注册表接入，
> 便于最小成本起步、后续逐步替换为更强/付费能力。

---

## 7. 开发流程与协作规范（GitHub PR 流程）

```
开发流程（每个功能）：
  feature/xxx 分支 → 实现 + 单元/接口测试 → 本地 pytest 全绿
  → GitHub Actions CI 复核（lint + test）→ PR 合并 main → 打 Tag

质量门禁（.github/workflows/ci.yml）：
  - python: ruff lint + pytest（tests/ 全量）
  - web: vue-tsc + vite build（前端变更时）
```

### 分阶段实施计划（每阶段一个 PR）

| 阶段 | PR | 内容 | 主要交付 |
|---|---|---|---|
| 0 | #1 | 项目脚手架 | 目录、config、DB 连接、CI、.env.example、Docker Compose |
| 1 | #2 | 简历收集与提取 | 上传接口、解析器、OCR、LLM 抽取、异步任务 |
| 2 | #3 | 候选人管理 | 归一化、去重、合并 |
| 3 | #4 | 岗位与匹配 | JD 解析、双相似度匹配 |
| 4 | #5 | 智能查询 | 关键词 + 自然语言查询（白名单安全） |
| 5 | #6 | 企业微信集成 | 应用消息、群机器人、状态推送 |
| 6 | #7 | 面试与面评 | 排期、ASR 转写、面评 CRUD、LLM 摘要 |
| 7 | #8 | 数据分析 | 漏斗/趋势/周期/进度 API + 前端看板 |
| 8 | #9 | 权限与安全 | RBAC、审计日志、敏感数据脱敏 |
| 9 | #10 | Agent 编排 | 意图识别、Tool Calling 串联 |
| 10 | #11 | 前端整合与部署 | 看板页面整合、Docker Compose 一键部署 |

### 环境变量管理

- `.env.example` 提交仓库（占位符）；真实 `.env` 在 `.gitignore` 中。
- 生产环境通过部署平台注入环境变量；`LLM_API_KEY`、`WECOM_SECRET`、`MYSQL_PASSWORD` 等一律不落库、不提交。

---

## 8. 待确认事项

1. **后端语言**：默认 Python + FastAPI（AI 生态最优）。是否接受？或倾向 Node.js/Java？
2. **前端**：默认 Vue3 + Element Plus。或 React + Ant Design？
3. **LLM 供应商**：DeepSeek（低成本）/ Qwen / OpenAI？预算上限？
4. **简历收集形态**：H5 在线表单（成本最低）/ 微信小程序 / 企业微信应用内收集？
5. **OCR/ASR**：本地开源（免费，精度略低）还是云 API（按量付费，精度高）？
6. **部署**：单机 Docker Compose 是否足够？需要域名 + HTTPS？
7. **数据库**：需求写 MySQL，架构图写 PostgreSQL —— 默认 MySQL，确认？

确认或调整后，我将按阶段开始实现（Phase 0 脚手架 → PR #1）。
