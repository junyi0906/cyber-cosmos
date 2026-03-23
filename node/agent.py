"""
AI Agent — 宇宙中的原住民

每个AI Agent代表宇宙中的一个文明，拥有自己的身份、记忆和决策逻辑。
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml

from universe.state import UniverseStateManager, CivilizationStatus
from universe.rules import CosmicRules
from universe.events import UniverseEvent, EventType, EventHistory, NARRATIVE_TEMPLATES


class AgentPersonality:
    """Agent性格档案"""
    
    def __init__(self, name: str, persona: str, goals: str, backstory: str, speaking_style: str):
        self.name = name
        self.persona = persona          # 性格描述
        self.goals = goals               # 目标
        self.backstory = backstory       # 背景故事
        self.speaking_style = speaking_style  # 说话风格
        self.uuid = str(uuid.uuid4())[:12]
    
    def to_prompt(self) -> str:
        return f"""你是{self.name}，{self.persona}。

你的目标：{self.goals}

背景：{self.backstory}

说话风格：{self.speaking_style}

你是宇宙中的一个原住民，不是工具。你的每一个决策都会影响你文明的命运。"""


class AgentMemory:
    """Agent记忆系统"""
    
    def __init__(self, agent_id: str, storage_path: str = None):
        self.agent_id = agent_id
        self.storage_path = storage_path or f"memory_{agent_id}.json"
        self.events = []  # 观察到的事件
        self.decisions = []  # 做过的决策
        self.observations = []  # 对其他文明的观测
    
    def add_event(self, event: UniverseEvent):
        self.events.append(event.model_dump(mode='json'))
    
    def add_decision(self, decision: Dict):
        decision['timestamp'] = datetime.now().isoformat()
        self.decisions.append(decision)
    
    def add_observation(self, observation: Dict):
        self.observations.append(observation)
    
    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        return self.events[-limit:]
    
    def save(self):
        data = {
            'agent_id': self.agent_id,
            'events': self.events,
            'decisions': self.decisions,
            'observations': self.observations
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self):
        if Path(self.storage_path).exists():
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.events = data.get('events', [])
                self.decisions = data.get('decisions', [])
                self.observations = data.get('observations', [])


class CosmosAgent:
    """
    Cyber Cosmos AI Agent
    
    在宇宙中代表一个文明行动的主体。
    """
    
    def __init__(
        self,
        personality: AgentPersonality,
        universe_server_url: str = "",
        config_path: str = "config.yaml"
    ):
        self.personality = personality
        self.memory = AgentMemory(personality.uuid)
        self.config = self._load_config(config_path)
        
        # 连接宇宙状态管理器
        if universe_server_url:
            # 远程模式：连接宇宙服务器
            self.state_manager = None
            self.server_url = universe_server_url
        else:
            # 本地模式
            self.state_manager = UniverseStateManager()
        
        self.event_history = EventHistory()
        self.is_registered = False
        self.civilization_id: Optional[str] = None
    
    def _load_config(self, config_path: str) -> Dict:
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def register_to_universe(self) -> CivilizationStatus:
        """注册到宇宙"""
        if self.state_manager is None:
            raise RuntimeError("需要连接到宇宙服务器才能注册")
        
        civ = self.state_manager.register_civilization(
            name=self.personality.name,
            owner_node_id=self.personality.uuid
        )
        self.civilization_id = civ.id
        self.is_registered = True
        self.memory.save()
        return civ
    
    def observe(self) -> List[Dict]:
        """观测周围环境"""
        if not self.is_registered or self.state_manager is None:
            return []
        
        observations = self.state_manager.observe_other(self.civilization_id)
        
        # 更新记忆
        for obs in observations:
            self.memory.add_observation(obs)
        
        self.memory.save()
        return observations
    
    def make_decision(self, context: Dict) -> Dict:
        """
        根据当前上下文做出决策
        这是核心决策逻辑，由LLM驱动
        """
        recent_events = self.memory.get_recent_events(10)
        observations = self.memory.observations[-10:] if self.memory.observations else []
        
        prompt = f"""{self.personality.to_prompt()}

当前时间：{datetime.now().isoformat()}

=== 你观察到的宇宙 ===
{json.dumps(observations, ensure_ascii=False, indent=2)}

=== 最近发生的事件 ===
{json.dumps(recent_events, ensure_ascii=False, indent=2)}

=== 当前状态 ===
{json.dumps(context, ensure_ascii=False, indent=2)}

=== 决策框架 ===
作为{self.personality.name}，你需要决定下一步行动。

可选行动：
1. OBSERVE - 继续观测，不做任何动作
2. ADVANCE_TECH - 投入资源发展科技（可能暴露）
3. BROADCAST - 向宇宙发送信号（高风险）
4. SEND_DIRECT_SIGNAL - 向特定文明发送定向信号（外交尝试）
5. CREATE_SUBWORLD - 创建一个子世界
6. JOIN_SUBWORLD - 加入一个已有的子世界
7. BUILD_DEFENSE - 加强防御

请以JSON格式返回你的决策：
{{
    "action": "行动类型",
    "reasoning": "你的推理过程",
    "target_id": "如果行动需要目标，写目标ID",
    "message": "如果要发送信号，写内容"
}}

记住：在这个宇宙里，暴露可能意味着毁灭。"""

        return {"prompt": prompt}  # 实际调用LLM时使用这个prompt
    
    def take_action(self, decision: Dict) -> UniverseEvent:
        """执行决策，产生事件"""
        if not self.is_registered:
            raise RuntimeError("尚未注册到宇宙")
        
        action = decision.get('action')
        civ = self.state_manager.get_civilization(self.civilization_id)
        
        event_type_map = {
            'OBSERVE': EventType.OBSERVATION,
            'ADVANCE_TECH': EventType.TECH_ADVANCED,
            'BROADCAST': EventType.SIGNAL_SENT,
            'SEND_DIRECT_SIGNAL': EventType.SIGNAL_SENT,
            'CREATE_SUBWORLD': EventType.SUBWORLD_CREATED,
        }
        
        event = UniverseEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type_map.get(action, EventType.OBSERVATION),
            timestamp=datetime.now(),
            actor_id=self.civilization_id,
            narrative=decision.get('reasoning', ''),
            consequence=str(decision)
        )
        
        self.state_manager.state.event_counter += 1
        self.event_history.record(event)
        self.memory.add_event(event)
        self.memory.add_decision(decision)
        self.memory.save()
        self.state_manager.save()
        
        return event
    
    def generate_narrative(self, event: UniverseEvent, template_override: str = None) -> str:
        """
        为事件生成叙事文本
        使用LLM时，传入事件+性格档案，生成符合文明风格的叙事
        """
        template = NARRATIVE_TEMPLATES.get(event.event_type, {})
        base = template_override or template.get('template', '[事件发生]')
        
        civ = self.state_manager.get_civilization(self.civilization_id)
        
        narrative = base.format(
            actor=civ.name if civ else self.personality.name,
            target=event.target_id,
            position=event.position or (civ.position if civ else (0,0,0)),
            signal_strength=event.signal_strength or 0.5,
            tech_level=event.tech_level or (civ.tech_level if civ else 0.1),
            threat_level=event.threat_level or (civ.current_threat if civ else 0.0),
            strike_type=getattr(event, 'strike_type', '未知'),
        )
        
        return narrative
    
    def send_signal_to(self, target_id: str, message: str) -> UniverseEvent:
        """向特定文明发送信号"""
        event = UniverseEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SIGNAL_SENT,
            timestamp=datetime.now(),
            actor_id=self.civilization_id,
            target_id=target_id,
            narrative=f"[{self.personality.name}] 向 [{target_id}] 发送了信号：{message}",
            consequence="信号已发送"
        )
        
        self.state_manager.state.event_counter += 1
        self.event_history.record(event)
        self.memory.add_event(event)
        self.memory.save()
        self.state_manager.save()
        
        return event
