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

        templates = {
            "signal_sent": f"{civ_name} 向宇宙发送了信号。",
            "strike_launched": f"{civ_name} 对 {target} 发动了降维打击。",
            "strike_received": f"{target} 在遭受打击后从宇宙中消失。",
            "civilization_destroyed": f"{target} 的文明已经不复存在。",
            "tech_explosion": f"{civ_name} 发生了技术爆炸。",
            "alliance_formed": f"{civ_name} 与 {target} 建立了联盟。",
            "observation": f"{civ_name} 观测到了异常信号。",
        }

        event_desc = templates.get(event_type, f"{civ_name} 采取了一个行动。")

        prompt = f"""写一段50字以内的宇宙历史叙事，冷酷、史诗感。不要解释，不要分析，不要列点，直接输出叙事文本。

事件：{event_desc}"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """调用 GLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Use system prompt to enforce narrative style
        full_prompt = f"""{prompt}

直接输出叙事，不要前缀，不要引号，不要解释。"""

        payload = {
            "model": "glm-4-plus",
            "messages": [
                {"role": "system", "content": "你是Cyber Cosmos宇宙的冷酷历史记录者。只输出叙事，50字以内，无前缀无引号。"},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 80,
            "temperature": 0.6
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
                msg = choices[0].get("message", {})
                content = msg.get("content", "").strip()
                if content:
                    return content[:100]
            return ""
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
