"""
宇宙状态管理 — Universe State Management

管理所有文明的状态、位置、关系和历史。
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel

from universe.rules import CosmicRules


class CivilizationStatus(BaseModel):
    """文明状态"""
    id: str
    name: str
    owner_node_id: str              # 所属节点ID
    
    # 位置与资源
    position: Tuple[float, float, float]  # 宇宙坐标 (x, y, z)
    
    # 发展水平
    tech_level: float = 0.1       # 科技水平 0-1
    defense_level: float = 0.1    # 防御水平 0-1
    signal_control: float = 0.5   # 信号控制能力 0-1（越高越不容易暴露）
    
    # 状态
    is_alive: bool = True
    discovered: List[str] = []     # 已发现的文明ID
    
    # 关系（文明ID -> 关系值）
    # 正值=友好，负值=敌对，0=未知
    relations: Dict[str, float] = {}
    
    # 当前位置的威胁评估
    current_threat: float = 0.0
    
    # 创建时间
    created_at: datetime = datetime.now()
    
    # 最后活跃时间
    last_active: datetime = datetime.now()

    class Config:
        arbitrary_types_allowed = True


class SubWorld(BaseModel):
    """子世界"""
    id: str
    creator_id: str                 # 创建者ID
    name: str                       # 子世界名称
    rules: Dict = {}               # 子世界特有规则（不得违反宇宙宪法）
    members: List[str] = []        # 成员ID列表
    created_at: datetime = datetime.now()
    is_open: bool = True           # 是否开放加入


class UniverseState(BaseModel):
    """宇宙状态"""
    universe_id: str
    name: str
    created_at: datetime = datetime.now()
    
    civilizations: Dict[str, CivilizationStatus] = {}
    subworlds: Dict[str, SubWorld] = {}
    
    # 宇宙基本参数
    size: Tuple[float, float, float] = (1000.0, 1000.0, 1000.0)  # 宇宙空间大小
    
    # 全局事件计数器
    event_counter: int = 0

    class Config:
        arbitrary_types_allowed = True


class UniverseStateManager:
    """宇宙状态管理器"""
    
    def __init__(self, state_file: str = "universe_state.json"):
        self.state_file = state_file
        self.state = self._load()
    
    def _load(self) -> UniverseState:
        """加载状态"""
        if Path(self.state_file).exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换datetime字符串
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                for cid, civ in data.get('civilizations', {}).items():
                    if 'created_at' in civ:
                        civ['created_at'] = datetime.fromisoformat(civ['created_at'])
                    if 'last_active' in civ:
                        civ['last_active'] = datetime.fromisoformat(civ['last_active'])
                for sid, sw in data.get('subworlds', {}).items():
                    if 'created_at' in sw:
                        sw['created_at'] = datetime.fromisoformat(sw['created_at'])
                return UniverseState(**data)
        
        return UniverseState(
            universe_id=str(uuid.uuid4())[:8],
            name="Cyber Cosmos Alpha"
        )
    
    def save(self) -> None:
        """保存状态"""
        data = self.state.model_dump(mode='json')
        data['created_at'] = data['created_at'].isoformat()
        for cid, civ in data.get('civilizations', {}).items():
            civ['created_at'] = civ['created_at'].isoformat()
            civ['last_active'] = civ['last_active'].isoformat()
        for sid, sw in data.get('subworlds', {}).items():
            sw['created_at'] = sw['created_at'].isoformat()
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_civilization(self, name: str, owner_node_id: str) -> CivilizationStatus:
        """注册新文明"""
        import random
        
        # 随机分配位置（确保不与已有文明太近）
        while True:
            pos = (
                random.uniform(0, self.state.size[0]),
                random.uniform(0, self.state.size[1]),
                random.uniform(0, self.state.size[2])
            )
            too_close = False
            for civ in self.state.civilizations.values():
                if CosmicRules.calculate_distance(pos, civ.position) < 50:
                    too_close = True
                    break
            if not too_close:
                break
        
        civ = CivilizationStatus(
            id=str(uuid.uuid4())[:12],
            name=name,
            owner_node_id=owner_node_id,
            position=pos
        )
        
        self.state.civilizations[civ.id] = civ
        self.save()
        return civ
    
    def get_civilization(self, civ_id: str) -> Optional[CivilizationStatus]:
        return self.state.civilizations.get(civ_id)
    
    def update_civilization(self, civ: CivilizationStatus) -> None:
        """更新文明状态"""
        civ.last_active = datetime.now()
        self.state.civilizations[civ.id] = civ
        self.save()
    
    def destroy_civilization(self, civ_id: str, reason: str) -> bool:
        """毁灭文明"""
        if civ_id in self.state.civilizations:
            self.state.civilizations[civ_id].is_alive = False
            self.state.civilizations[civ_id].current_threat = 1.0
            self.save()
            return True
        return False
    
    def observe_other(self, observer_id: str) -> List[Dict]:
        """观测其他文明（基于位置和技术水平）"""
        observer = self.get_civilization(observer_id)
        if not observer or not observer.is_alive:
            return []
        
        observations = []
        for civ_id, civ in self.state.civilizations.items():
            if civ_id == observer_id or not civ.is_alive:
                continue
            
            distance = CosmicRules.calculate_distance(observer.position, civ.position)
            
            # 只有科技水平和距离达到一定程度才能观测到
            # 观测范围 = tech_level * 500 光年
            observation_range = observer.tech_level * 500
            
            if distance <= observation_range:
                observations.append({
                    'civilization_id': civ_id,
                    'name': civ.name,
                    'distance': round(distance, 2),
                    'position': civ.position,
                    'estimated_tech_level': civ.tech_level,
                    'is_alive': civ.is_alive
                })
        
        return observations
    
    def create_subworld(
        self,
        creator_id: str,
        name: str,
        rules: Dict = None
    ) -> Optional[SubWorld]:
        """创建子世界"""
        valid, _ = CosmicRules.validate_subworld_rules(rules or {})
        if not valid:
            return None
        
        sw = SubWorld(
            id=str(uuid.uuid4())[:12],
            creator_id=creator_id,
            name=name,
            rules=rules or {}
        )
        self.state.subworlds[sw.id] = sw
        self.save()
        return sw
    
    def get_universe_summary(self) -> Dict:
        """获取宇宙概览"""
        alive = [c for c in self.state.civilizations.values() if c.is_alive]
        return {
            'universe_id': self.state.universe_id,
            'name': self.state.name,
            'total_civilizations': len(self.state.civilizations),
            'alive_civilizations': len(alive),
            'total_subworlds': len(self.state.subworlds),
            'event_count': self.state.event_counter,
        }
