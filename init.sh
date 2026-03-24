#!/bin/bash
set -e
PORT=${PORT:-3000}
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
echo "[init] 启动开发服务器 (PORT=$PORT)..."
# Node.js 项目
if [[ -f "package.json" ]]; then
    npm install 2>&1 | tail -3
    npm run dev -- --port $PORT --host 0.0.0.0 > /tmp/dev_server.log 2>&1 &
# Python 项目
elif [[ -f "requirements.txt" || -f "pyproject.toml" ]]; then
    pip install -r requirements.txt 2>&1 | tail -3
    python -m uvicorn app:app --port $PORT --host 0.0.0.0 > /tmp/dev_server.log 2>&1 &
else
    echo "[init] 未检测到技术栈，手动启动开发服务器"
    echo "[init] PORT=$PORT"
fi
DEV_PID=$!
echo $DEV_PID > "$PROJECT_DIR/.dev_server.pid"
echo "[init] 开发服务器 PID: $DEV_PID"
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT" > /dev/null 2>&1; then
        echo "[init] ✅ 服务器已就绪 http://localhost:$PORT"
        exit 0
    fi
    sleep 1
done
echo "[init] ⚠️ 启动超时"
exit 1
