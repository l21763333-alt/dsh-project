# Recruit AI — 招聘数据智能化（MVP）

基于 AI 的招聘简历看板系统 MVP：H5 在线表单收集 Word(.docx) 简历 → python-docx 解析文本 → DeepSeek API 结构化提取候选人信息 → MySQL 存储 → Web 看板展示。

## MVP 范围

| 能力 | 说明 |
|---|---|
| 简历收集 | H5 在线表单（上传 .docx 文件，可附填姓名/电话） |
| 文档解析 | 仅支持 Word(.docx)，python-docx 提取纯文本 |
| 信息提取 | DeepSeek（OpenAI 兼容协议）LLM 结构化抽取候选人字段 |
| 数据存储 | MySQL 8（默认），测试用 SQLite 内存库 |
| 数据展示 | Vue3 + Element Plus 看板：候选人列表 / 详情 / 简历原文 |
| 部署 | 单端口本地部署（FastAPI 托管前端构建产物） |

## 技术栈

- 后端：Python 3.9+ / FastAPI / SQLAlchemy 2 / PyMySQL
- AI：DeepSeek API（`openai` SDK 兼容客户端），Key 全部走环境变量
- 前端：Vue 3 + Vite + Element Plus + ECharts
- 数据库：MySQL 8.0

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env：填入 MYSQL_* 与 LLM_API_KEY（DeepSeek Key，成本预算内按量计费）
```

> ⚠️ `.env` 已在 `.gitignore` 中；**严禁将真实 API Key 提交到公开仓库**。

### 2. 方式 A：Docker Compose（推荐，含 MySQL）

```bash
# 安装 Docker（macOS 可用 colima：brew install colima docker）
colima start
docker compose up -d --build
# 访问 http://127.0.0.1:8000 （前端看板）
# API 文档 http://127.0.0.1:8000/api/docs
```

### 2'. 方式 B：本地运行（MySQL 需自行准备）

```bash
# 初始化数据库（如用本地/远程 MySQL）
MYSQL_ROOT_PASSWORD=xxx ./scripts/init_db.sh

# 启动后端
./scripts/dev.sh          # 监听 8000 端口
# 或手动：
# python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
# .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端（生产单端口部署）
cd web && npm install && npm run build   # FastAPI 自动托管 web/dist

# 前端（开发模式，热更新）
cd web && npm run dev                    # http://localhost:5173（代理到 8000）
```

### 3. 运行测试

```bash
.venv/bin/pytest -q
```

## 开发流程（GitHub PR 规范）

每个功能一个 PR：

1. `git checkout -b feature/xxx`
2. 实现 + 编写测试（`tests/`）
3. 本地 `pytest -q` 全绿
4. `git push origin feature/xxx` → GitHub Actions CI 复核 → 创建 PR → 合并 main

仓库：https://github.com/l21763333-alt/dsh-project （公开）

## 成本控制（预算 20 元）

- 测试全部使用 FakeLLM 桩，不产生真实 API 调用；
- 仅解析简历时调用 DeepSeek，单次提取约几百 token（deepseek-chat 约 ¥0.001/千token 输入）；
- 向量化/长文本二次调用等耗钱功能不在 MVP 范围。

## 目录结构

```
app/
├── main.py              # 应用入口（工厂）
├── core/                # config(环境变量) / database / security
├── api/v1/              # 路由：health → resumes / candidates / search ...
├── models/              # SQLAlchemy ORM
├── schemas/             # Pydantic 出入参
├── services/            # 业务层
├── ai/                  # llm / extractors(docx) / prompts
└── worker/              # 异步任务（后续阶段）
web/                     # Vue3 前端
tests/                   # pytest（PR 质量门禁）
docs/                    # 架构设计
```
