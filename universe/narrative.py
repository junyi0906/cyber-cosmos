"""
叙事生成模块 — Narrative Generator

使用 LLM 为宇宙事件生成有故事感的叙事文本。
"""

import os
import json
import httpx
from typing import Optional
from universe.events import UniverseEvent, EventType


GLM_API_KEY = os.environ.get(
    "GLM5_TURBO_KEY",
    "8ebd0252b1fc498ebd53dfc299d4de12.PwoiSyS6NA5RuALo"
)
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


class NarrativeGenerator:
    """
    叙事生成器

    使用 GLM-5-Turbo 为宇宙事件生成叙事文本。
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or GLM_API_KEY
        self.api_url = GLM_API_URL

    def generate(
        self,
        event: UniverseEvent,
        civ_name: str,
        target_name: str = None,
        context: dict = None
    ) -> str:
        """
        为事件生成叙事文本

        Args:
            event: 事件对象
            civ_name: 发起文明的名称
            target_name: 目标文明名称（如果有）
            context: 额外的上下文信息

        Returns:
            叙事文本
        """
        prompt = self._build_prompt(event, civ_name, target_name, context)

        try:
            narrative = self._call_llm(prompt)
            return narrative
        except Exception as e:
            # 降级：返回简短的事件描述
            return self._fallback_narrative(event, civ_name, target_name)

    def _build_prompt(
        self,
        event: UniverseEvent,
        civ_name: str,
        target_name: str,
        context: dict
    ) -> str:
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
        target = target_name or "未知文明"

        base_prompt = f"""你是 Cyber Cosmos 宇宙的历史记录者。

黑暗森林法则笼罩着这个宇宙：文明发展到一定程度必然暴露，暴露必然引来打击，打击不可逆。

请为以下事件写一段 50-150 字的叙事，要求：
- 冷酷、史诗感、有文学性
- 符合黑暗森林的氛围
- 不要出现"AI"或"模型"等词
- 用第二或第三人称叙事

事件类型：{event_type}
发起文明：{civ_name}
"""

        if event_type == "signal_sent":
            base_prompt += f"""
{civ_name} 向宇宙发送了信号。这可能是一步险棋——信号暴露位置，但也可能带来意想不到的回应。
"""
        elif event_type == "signal_received":
            base_prompt += f"""
{civ_name} 接收到了来自 {target} 的信号。这是一个关键信息：对方存在，而且正在广播。
"""
        elif event_type == "strike_launched":
            base_prompt += f"""
{civ_name} 对 {target} 发动了降维打击。这不是冲动，而是经过计算的——风险已经超过了容忍阈值。
"""
        elif event_type == "strike_received":
            base_prompt += f"""
{target} 的文明在遭受打击后从宇宙中消失。{civ_name} 的坐标也随之暴露。
"""
        elif event_type == "civilization_destroyed":
            base_prompt += f"""
{target} 的文明已经不复存在。这是黑暗森林的残酷法则——暴露即毁灭。
"""
        elif event_type == "tech_explosion":
            base_prompt += f"""
{civ_name} 发生了技术爆炸。在一瞬间，它的科技水平跃升到了一个新的层次——这对周围的文明来说，既是机遇，也是威胁。
"""
        elif event_type == "alliance_formed":
            base_prompt += f"""
{civ_name} 与 {target} 建立了联盟。在这个宇宙里，联盟是最脆弱的东西——也是最珍贵的。
"""
        elif event_type == "observation":
            base_prompt += f"""
{civ_name} 在宇宙深处观测到了异常。这可能是猎物，也可能是猎人。
"""
        else:
            base_prompt += f"""
事件发生了。宇宙继续运转，黑暗森林的法则依然有效。
"""

        if context:
            additional = context.get("additional_info", "")
            if additional:
                base_prompt += f"\n背景：{additional}"

        return base_prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 GLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "glm-5",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 300,
            "temperature": 0.8
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            return ""

    def _fallback_narrative(
        self,
        event: UniverseEvent,
        civ_name: str,
        target_name: str
    ) -> str:
        """降级叙事：当 LLM 调用失败时使用模板"""
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
        target = target_name or "未知文明"

        templates = {
            "signal_sent": f"{civ_name} 向虚空发送了一道信号。黑暗森林中，信号即暴露，暴露即危险。",
            "strike_launched": f"{civ_name} 发动了毁灭性的打击。{target} 的文明在光芒中消亡。",
            "civilization_destroyed": f"{target} 从宇宙中被抹去。黑暗森林又恢复了寂静。",
            "tech_explosion": f"{civ_name} 的科技发生了突破性跃升。周围的文明开始感到不安。",
            "alliance_formed": f"{civ_name} 与 {target} 结成了联盟——在这片黑暗森林里，这是一张罕见的牌。",
            "observation": f"{civ_name} 的观测阵列捕捉到了异常。有什么东西在那里。",
        }

        return templates.get(
            event_type,
            f"{civ_name} 采取了一个行动。宇宙记录下了这一刻。"
        )


# 单例
_narrative_generator: Optional[NarrativeGenerator] = None


def get_narrative_generator() -> NarrativeGenerator:
    global _narrative_generator
    if _narrative_generator is None:
        _narrative_generator = NarrativeGenerator()
    return _narrative_generator
