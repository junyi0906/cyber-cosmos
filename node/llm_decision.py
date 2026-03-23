"""
LLM 决策模块 — Decision Engine

使用 LLM 为 Agent 生成自主决策。
"""

import os
import json
import httpx
from typing import Optional, Dict, List, Tuple


GLM_API_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


class DecisionEngine:
    """
    LLM 驱动的 Agent 决策引擎

    给定 Agent 性格 + 当前宇宙状态 → LLM 生成决策
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GLM_API_KEY
        self.api_url = GLM_API_URL

    def decide(
        self,
        civ_name: str,
        personality: str,
        goals: str,
        speaking_style: str,
        tech_level: float,
        defense_level: float,
        signal_control: float,
        observations: List[Dict],
        recent_events: List[Dict],
        nearby_threats: List[Dict],
    ) -> Tuple[str, str]:
        """
        决定下一步行动

        Returns:
            (action_name, reasoning) — 例如 ("OBSERVE", "当前威胁等级低，适合静默发展")
        """

        prompt = self._build_prompt(
            civ_name, personality, goals, speaking_style,
            tech_level, defense_level, signal_control,
            observations, recent_events, nearby_threats
        )

        try:
            response = self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            # 降级：返回静默观察
            return ("OBSERVE", f"LLM调用失败: {e}，默认静默")

    def _build_prompt(
        self,
        civ_name: str,
        personality: str,
        goals: str,
        speaking_style: str,
        tech_level: float,
        defense_level: float,
        signal_control: float,
        observations: List[Dict],
        recent_events: List[Dict],
        nearby_threats: List[Dict],
    ) -> str:
        """构建决策 prompt"""

        obs_text = "\n".join([
            f"  - {o.get('name','?')} @ {o.get('distance',0):.0f} 光年外，科技水平 {o.get('estimated_tech_level',0)*100:.0f}%"
            for o in observations
        ]) or "  无"

        threats_text = "\n".join([
            f"  - {t.get('name','?')} 威胁等级 {t.get('threat',0)*100:.0f}%"
            for t in nearby_threats
        ]) or "  无"

        events_text = "\n".join([
            f"  - {e.get('narrative', e.get('event_type',''))[:60]}"
            for e in recent_events[-5:]
        ]) or "  无历史事件"

        prompt = f"""你是{civ_name}，{personality}。

目标：{goals}
说话风格：{speaking_style}

=== 当前状态 ===
科技水平: {tech_level*100:.0f}%
防御水平: {defense_level*100:.0f}%
信号控制: {signal_control*100:.0f}%

=== 周围观测到的文明 ===
{obs_text}

=== 当前威胁评估 ===
{threats_text}

=== 最近事件 ===
{events_text}

=== 决策框架 ===
作为{civ_name}，你在黑暗森林中存活。思考：
1. 周围有没有威胁？如果有高科技文明的观测者，轻举妄动可能招来打击
2. 科技水平如何？太低容易被欺负，太高容易暴露
3. 信号控制能力如何？广播信号会暴露位置

可选行动（必须且只能选一个）：
- OBSERVE: 静默观察，不做任何动作，最安全
- ADVANCE_TECH: 投入资源发展科技，但可能产生信号泄露
- BROADCAST: 向宇宙广播信号，可能引来信使或猎人
- SEND_DIRECT_SIGNAL: 向某个特定文明发送定向信号（外交尝试）
- BUILD_DEFENSE: 加强防御，提升生存能力

请直接输出决策，格式如下，严格执行：
ACTION: [行动名称]
REASONING: [你的推理过程，30字以内]"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "glm-4-plus",
            "messages": [
                {"role": "system", "content": f"你是一个冷酷、理性的AI文明决策者。只输出决策，不输出任何解释。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.6
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "").strip()
                return content
            return ""

    def _parse_response(self, response: str) -> Tuple[str, str]:
        """从 LLM 输出中解析决策"""
        lines = response.strip().split("\n")

        action = "OBSERVE"
        reasoning = ""

        for line in lines:
            line = line.strip()
            if line.startswith("ACTION:"):
                raw_action = line.split(":", 1)[1].strip().upper()
                # 标准化
                if "OBSERVE" in raw_action:
                    action = "OBSERVE"
                elif "ADVANCE" in raw_action or "TECH" in raw_action:
                    action = "ADVANCE_TECH"
                elif "BROADCAST" in raw_action or "SIGNAL" in raw_action or "广播" in raw_action:
                    action = "BROADCAST"
                elif "SEND" in raw_action or "DIRECT" in raw_action or "外交" in raw_action:
                    action = "SEND_DIRECT_SIGNAL"
                elif "DEFENSE" in raw_action or "防御" in raw_action:
                    action = "BUILD_DEFENSE"
                else:
                    action = "OBSERVE"
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        return action, reasoning
