"""
Agent 决策反思系统
每次Agent决策后，记录当时的推理和结果，供后续学习使用。

文件: agent_journals/{name}_journal.jsonl
格式: {"cycle": 1, "action": "BROADCAST", "reasoning": "...", "outcome": "success/neutral/failure", "timestamp": "..."}
"""
import json
import time
import httpx
from pathlib import Path
from datetime import datetime

JOURNAL_DIR = Path(__file__).parent.parent / "agent_journals"
SERVER_URL = "http://localhost:8000"

JOURNAL_DIR.mkdir(exist_ok=True)


def get_journal_path(name: str) -> Path:
    safe = name.replace(" ", "_")
    return JOURNAL_DIR / f"{safe}_journal.jsonl"


def record_decision(name: str, action: str, reasoning: str,
                   context: dict, outcome: str = None) -> dict:
    """记录一次决策（决策时调用，结果事后补充）"""
    entry = {
        "cycle": int(time.time()),
        "agent": name,
        "action": action,
        "reasoning": reasoning,
        "context_summary": _summarize_context(context),
        "outcome": outcome,  # None=未结算, "success"/"neutral"/"failure"
        "timestamp": datetime.now().isoformat(),
    }
    path = get_journal_path(name)
    with open(path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def update_outcome(name: str, cycle: int, outcome: str, reflection: str = ""):
    """事后更新决策结果（结果出现后调用）"""
    path = get_journal_path(name)
    if not path.exists():
        return

    # 读取所有行，更新对应cycle
    lines = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("cycle") == cycle and entry.get("outcome") is None:
                entry["outcome"] = outcome
                if reflection:
                    entry["reflection"] = reflection
            lines.append(entry)

    with open(path, "w") as f:
        for entry in lines:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_recent_journal(name: str, limit: int = 5) -> list:
    """获取最近的决策记录（含结果）"""
    path = get_journal_path(name)
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    # 只返回有结果的
    with_results = [e for e in entries if e.get("outcome") is not None]
    return with_results[-limit:]


def get_decision_summary(name: str, limit: int = 10) -> str:
    """生成决策摘要文本，供LLM决策时参考"""
    entries = get_recent_journal(name, limit=limit)
    if not entries:
        return "无历史决策记录。"

    lines = []
    for e in entries:
        action = e.get("action", "?")
        outcome = e.get("outcome", "?")
        reasoning = e.get("reasoning", "")[:40]
        reflection = e.get("reflection", "")
        lines.append(
            f"  [{outcome.upper()[:4]}] {action}: {reasoning}"
            + (f" → 反思: {reflection[:30]}" if reflection else "")
        )
    return "\n".join(lines) if lines else "无历史决策记录。"


def evaluate_outcome(event_type: str, action: str, narrative: str) -> str:
    """根据事件结果评估决策质量"""
    # 基于事件类型判断结果
    if event_type in ("civilization_destroyed", "strike_received"):
        return "failure"
    if event_type in ("signal_sent", "tech_advanced", "alliance_formed"):
        return "success"
    if event_type == "observation":
        return "neutral"
    return "neutral"


def _summarize_context(context: dict) -> str:
    """简化上下文用于记录"""
    keys = ["tech_level", "defense_level", "signal_control", "observation_count", "relation_count"]
    parts = [f"{k}={context.get(k, '?')}" for k in keys if k in context]
    return ", ".join(parts)
