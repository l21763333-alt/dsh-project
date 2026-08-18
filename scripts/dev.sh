#!/usr/bin/env bash
# 本地开发启动脚本：创建 venv（若缺失）并启动 FastAPI
# 用法：./scripts/dev.sh   （PORT 环境变量可覆盖端口，默认 8000）
set -e
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "[dev.sh] 创建虚拟环境并安装依赖..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements-dev.txt
fi

echo "[dev.sh] 启动服务: http://127.0.0.1:${PORT:-8000}"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
