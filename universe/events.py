"""
宇宙事件 — Events

所有重大事件都会记录到宇宙历史，不可篡改。
"""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventType(Enum):
    """事件类型"""
    BIRTH = "birth"                    # 文明诞生
    SIGNAL_SENT = "signal_sent"        # 发送信号
    SIGNAL_RECEIVED = "signal_received" # 接收信号
    STRIKE_LAUNCHED = "strike_launched"    # 发动打击
    STRIKE_RECEIVED = "strike_received"    # 遭受打击
    CIVILIZATION_DESTROYED = "civilization_destroyed"  # 文明灭绝
    ALLIANCE_FORMED = "alliance_formed"    # 建立联盟
    ALLIANCE_BROKEN = "alliance_broken"   # 联盟破裂
    SUBWORLD_CREATED = "subworld_created"  # 创建子世界
    SUBWORLD_JOINED = "subworld_joined"    # 加入子世界
    TECH_ADVANCED = "tech_advanced"         # 科技进步
    TECH_EXPLOSION = "tech_explosion"       # 技术爆炸
    OBSERVATION = "observation"             # 观测到其他文明
    PEACE_PROPOSAL = "peace_proposal"      # 提议和平
    TRADE_REQUEST = "trade_request"         # 贸易请求
    ALLIANCE_PROPOSAL = "alliance_proposal"  # 结盟提议
    DECLARATION_OF_WAR = "declaration_of_war"  # 宣战
    DIPLOMATIC_SIGNAL = "diplomatic_signal"    # 外交信号
    ESPIONAGE = "espionage"                    # 间谍行动
    TRUCE_PROPOSAL = "truce_proposal"          # 休战提议
    RELATION_CHANGED = "relation_changed"      # 关系变化


class CivilizationDestroyedReason(Enum):
    """文明毁灭原因"""
    DIMENSIONAL_STRIKE = "dimensional_strike"     # 降维打击
    LIGHT_PARTICLE = "light_particle"              # 光粒打击
    SELF_EXPOSED = "self_exposed"                  # 自我暴露
    ALLIANCE_BETRAYAL = "alliance_betrayal"       # 盟友背叛


class UniverseEvent(BaseModel):
    """宇宙事件"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    actor_id: str                      # 事件发起者
    target_id: Optional[str] = None   # 事件承受者（如果有）

    # 事件详情
    position: Optional[tuple] = None  # 事件发生位置 (x, y, z)
    signal_strength: Optional[float] = None
    tech_level: Optional[float] = None
    threat_level: Optional[float] = None

    # 叙事文本（由LLM生成）
    narrative: str = ""

    # 后果
    consequence: str = ""
    destroyed_reason: Optional[CivilizationDestroyedReason] = None

    # 事件重要性分级
    # TRIVIAL: 静默观察，日常动作，不显示在事件流
    # NOTABLE: 值得注意，围观群众可见
    # MAJOR:   重大事件，宇宙历史转折点
    # CRITICAL: 灭世级，文明灭绝等
    significance: str = "NOTABLE"  # 默认NOTABLE

    class Config:
        use_enum_values = True


class EventHistory:
    """事件历史记录器（只追加，不可篡改）"""
    
    def __init__(self, storage_path: str = "universe_history.jsonl"):
        self.storage_path = storage_path
        self._buffer = []
    
    def record(self, event: UniverseEvent) -> None:
        """记录一个事件"""
        self._buffer.append(event.model_dump(mode='json'))
    
    def flush(self) -> None:
        """将缓冲区写入磁盘"""
        import json
        with open(self.storage_path, 'a', encoding='utf-8') as f:
            for entry in self._buffer:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        self._buffer.clear()
    
    def get_events_for(self, civilization_id: str, limit: int = 50):
        """获取某个文明相关的事件"""
        import json
        events = []
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                for line in f:
                    event = json.loads(line)
                    if event['actor_id'] == civilization_id or event.get('target_id') == civilization_id:
                        events.append(event)
            return events[-limit:]
        except FileNotFoundError:
            return []
    
    def get_recent(self, limit: int = 100):
        """获取最近的事件"""
        import json
        events = []
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                for line in f:
                    events.append(json.loads(line))
            return events[-limit:]
        except FileNotFoundError:
            return []


# 叙事骨架模板
NARRATIVE_TEMPLATES = {
    EventType.SIGNAL_SENT: {
        "template": "[文明{actor}]向坐标{position}发送了{signal_type}信号，强度{strength}",
        "emotion": "紧张、谨慎"
    },
    EventType.STRIKE_LAUNCHED: {
        "template": "[文明{actor}]对[文明{target}]发动了{strike_type}打击",
        "emotion": "冷酷、决绝"
    },
    EventType.CIVILIZATION_DESTROYED: {
        "template": "[文明{target}]在遭受{strike_type}后从宇宙中消失",
        "emotion": "沉重、不可逆"
    },
    EventType.TECH_EXPLOSION: {
        "template": "[文明{actor}]发生了技术爆炸，科技水平从{old_level}跃升至{new_level}",
        "emotion": "震撼、不确定"
    },
    EventType.OBSERVATION: {
        "template": "[文明{actor}]在坐标{position}观测到了异常信号，威胁等级：{threat}",
        "emotion": "警觉、谨慎"
    },
}
