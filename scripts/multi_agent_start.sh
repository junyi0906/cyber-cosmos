#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

export PYTHONPATH="$PROJECT_DIR"
export GLM5_TURBO_KEY="8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"

LOG_DIR="/tmp/cyber_agents"
mkdir -p "$LOG_DIR"

# 先停掉旧agent
pkill -f "node/auto_run.py" 2>/dev/null
sleep 1

declare -a AGENTS=(
  "星际猎手:冷酷的宇宙猎手，在黑暗中潜伏等待机会:在黑暗森林中存活并伺机扩张，保持低调不主动暴露"
  "星际商人:狡诈的星际商人，利益至上善于交易:通过交易和外交手段获取利益，避免战争寻求合作机会"
  "星际游侠:理想主义的星际游侠，探索未知传播知识:探索宇宙发现新技术，与所有文明和平共处"
)

for agent_spec in "${AGENTS[@]}"; do
  IFS=':' read -r name personality goals <<< "$agent_spec"
  LOG_FILE="$LOG_DIR/${name}.log"
  echo "[$(date)] 启动Agent: $name" > "$LOG_FILE"
  nohup python3 -u node/auto_run.py \
    --name "$name" \
    --personality "$personality" \
    --goals "$goals" \
    --interval 10 \
    >> "$LOG_FILE" 2>&1 &
  echo "[$(date)] PID=$! Agent=$name"
  sleep 2
done

echo ""
echo "=== Agent进程 ==="
ps aux | grep "node/auto_run" | grep -v grep | awk '{print "PID:"$2, "内存:"$6"K"}'
echo ""
echo "=== 日志 ==="
tail -3 /tmp/cyber_agents/星际猎手.log
