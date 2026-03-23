#!/usr/bin/env python3
"""
Cyber Cosmos — Agent 自动运行脚本

让 Agent 在宇宙中自主行动，每个回合根据 LLM 做决策。
"""

import argparse
import asyncio
import sys
import time
import json
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from node.agent import CosmosAgent, AgentPersonality, AgentMemory
from node.llm_decision import DecisionEngine
from universe.events import UniverseEvent


SERVER_URL = "http://localhost:8000"
GLM_KEY = "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"


def register_civ(name: str, node_id: str) -> str:
    """注册文明，返回 ID"""
    r = httpx.post(f"{SERVER_URL}/register", json={"name": name, "node_id": node_id}, timeout=10)
    d = r.json()
    if d.get("success"):
        return d["civilization"]["id"]
    raise RuntimeError(f"注册失败: {d}")


def get_civ_state(civ_id: str) -> dict:
    r = httpx.get(f"{SERVER_URL}/civilizations/{civ_id}", timeout=10)
    return r.json()


def get_observations(civ_id: str) -> list:
    r = httpx.get(f"{SERVER_URL}/civilizations/{civ_id}", timeout=10)
    civ = r.json()
    # 手动模拟观测（基于距离和科技）
    r2 = httpx.get(f"{SERVER_URL}/civilizations", timeout=10)
    all_civs = r2.json()
    civ_pos = civ.get("position", [0,0,0])
    obs = []
    for c in all_civs:
        if c["id"] == civ_id:
            continue
        pos = c.get("position", [0,0,0])
        dist = ((pos[0]-civ_pos[0])**2 + (pos[1]-civ_pos[1])**2 + (pos[2]-civ_pos[2])**2) ** 0.5
        tech = c.get("tech_level", 0.1)
        obs_range = tech * 500  # 科技越高，观测范围越远
        if dist <= obs_range:
            obs.append({
                "name": c["name"],
                "distance": dist,
                "estimated_tech_level": tech,
                "threat": min(dist / 200 if dist > 0 else 1.0, 1.0)
            })
    return obs


def take_action(civ_id: str, action: str, target_id: str = None, message: str = None):
    payload = {"civilization_id": civ_id, "action": action}
    if target_id:
        payload["target_id"] = target_id
    if message:
        payload["message"] = message
    r = httpx.post(f"{SERVER_URL}/action", json=payload, timeout=30)
    return r.json()


def get_recent_events(limit: int = 10) -> list:
    """获取最近的重大事件"""
    r = httpx.get(f"{SERVER_URL}/history", timeout=10)
    if r.status_code == 200:
        events = r.json()
        # 只取重大事件
        notable = [e for e in events if (e.get("significance") or "NOTABLE") != "TRIVIAL"]
        return notable[-limit:]
    return []


def run_autonomous_loop(civ_id: str, civ_name: str, personality: str, goals: str, interval: int = 10):
    """自主决策循环"""
    engine = DecisionEngine(api_key=GLM_KEY)

    # 性格参数
    tech_weight = 0.4
    defense_weight = 0.3
    risk_tolerance = 0.5

    print(f"\n🌌 {civ_name} 启动自主运行模式（每 {interval} 秒一个回合）")

    decisions_made = 0

    try:
        while True:
            # 获取当前状态
            state = get_civ_state(civ_id)
            if not state.get("is_alive", False):
                print(f"☠️  {civ_name} 已被毁灭，退出")
                break

            tech = state.get("tech_level", 0.1)
            defense = state.get("defense_level", 0.1)
            signal_ctrl = state.get("signal_control", 0.5)

            # 获取观测
            observations = get_observations(civ_id)

            # 获取最近事件作为记忆
            recent_events = get_recent_events(limit=5)

            
            # 外交行动选项（如果关系允许）
            diplomacy_actions = []
            for other_civ in civilizations:
                if other_civ["id"] == civ_id or not other_civ["is_alive"]:
                    continue
                rel = get_relation_between(civ_id, other_civ["id"])
                if rel and rel["relation"] > 20 and rel["status"] != "alliance":
                    diplomacy_actions.append({
                        "action": "PROPOSE_ALLIANCE",
                        "target_id": other_civ["id"],
                        "reason": f"与{other_civ['name']}关系良好，可提议结盟"
                    })
                if rel and rel["relation"] < -30:
                    diplomacy_actions.append({
                        "action": "DECLARE_WAR",
                        "target_id": other_civ["id"],
                        "reason": f"{other_civ['name']}关系恶劣，威胁极大"
                    })

# 评估威胁
            threats = [
                {"name": o["name"], "threat": o.get("estimated_tech_level", 0) * 0.5}
                for o in observations
                if o.get("distance", 999) < 100
            ]

            # LLM 决策（带记忆）
            action, reasoning = engine.decide(
                civ_name=civ_name,
                personality=personality,
                goals=goals,
                speaking_style="冷酷、简洁",
                tech_level=tech,
                defense_level=defense,
                signal_control=signal_ctrl,
                observations=observations,
                recent_events=recent_events,
                nearby_threats=threats,
            )

            # 执行决策
            result = take_action(civ_id, action)
            event_narrative = ""
            if result.get("success"):
                event = result.get("event", {})
                event_narrative = event.get("narrative", "")
                event_type = event.get("event_type", "")
                print(f"\n[{civ_name} 回合 {decisions_made+1}]")
                print(f"  决策: {action}")
                print(f"  推理: {reasoning}")
                print(f"  叙事: {event_narrative[:60] if event_narrative else ''}")
            else:
                print(f"\n[{civ_name}] 行动失败: {result.get('error')}")

            decisions_made += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n{civ_name} 被停止（{decisions_made} 个决策）")


def main():
    parser = argparse.ArgumentParser(description="Cyber Cosmos Agent 自动运行")
    parser.add_argument("--name", "-n", default="自主文明", help="文明名称")
    parser.add_argument("--personality", "-p", default="冷酷的宇宙猎手", help="性格描述")
    parser.add_argument("--goals", "-g", default="在宇宙中存活并发展，尽可能久", help="目标")
    parser.add_argument("--interval", "-i", type=int, default=10, help="每回合间隔（秒）")
    parser.add_argument("--server", "-s", default="http://localhost:8000", help="宇宙服务器地址")
    args = parser.parse_args()

    global SERVER_URL
    SERVER_URL = args.server

    print(f"\n{'='*50}")
    print(f"🌌 Cyber Cosmos — 自主 Agent")
    print(f"{'='*50}")
    print(f"文明名称: {args.name}")
    print(f"性格: {args.personality}")
    print(f"目标: {args.goals}")
    print(f"服务器: {SERVER_URL}")
    print(f"{'='*50}\n")

    # 注册文明
    node_id = f"agent_{int(time.time())}"
    civ_id = register_civ(args.name, node_id)
    print(f"✅ 文明 {args.name} 注册成功，ID: {civ_id}")

    # 运行自主循环
    run_autonomous_loop(
        civ_id=civ_id,
        civ_name=args.name,
        personality=args.personality,
        goals=args.goals,
        interval=args.interval
    )


if __name__ == "__main__":
    main()
