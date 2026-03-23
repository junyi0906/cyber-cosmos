"""
宇宙宪法 — Cyber Cosmos Rules Engine

黑暗森林法则是这个宇宙的基础物理定律，不可违背。
"""

from enum import Enum
from typing import Tuple
import math


class RuleSeverity(Enum):
    """违反规则的严重程度"""
    WARNING = "warning"       # 警告，但不一定致命
    STRIKE = "strike"        # 可招致打击
    FATAL = "fatal"          # 直接导致灭绝


class CosmicRules:
    """
    宇宙宪法 — 所有文明必须遵守的规则
    
    规则是确定性的，不依赖LLM。
    违反规则的行为会产生相应的后果。
    """

    # 信号暴露风险阈值
    SIGNAL_EXPOSURE_THRESHOLD = 0.7
    
    # 打击判定阈值（当风险超过此值时，观测者可发动打击）
    STRIKE_RISK_THRESHOLD = 0.65
    
    # 技术爆炸触发概率（每次科技升级时）
    TECH_EXPLOSION_CHANCE = 0.1
    
    # 技术爆炸带来的威胁等级提升
    TECH_EXPLOSION_THREAT_BOOST = 0.3

    @classmethod
    def evaluate_signal_risk(
        cls,
        signal_strength: float,
        target_distance: float,
        target_defense_level: float
    ) -> float:
        """
        评估信号暴露风险
        
        Args:
            signal_strength: 信号强度 (0-1)
            target_distance: 目标距离 (光年)
            target_defense_level: 目标防御水平 (0-1)
            
        Returns:
            风险值 (0-1)，越高越危险
        """
        # 距离越近，信号越危险
        distance_factor = 1.0 / (1.0 + target_distance * 0.1)
        
        # 信号强度因子
        strength_factor = signal_strength ** 2
        
        # 防御水平抵消部分风险
        defense_factor = 1.0 - (target_defense_level * 0.5)
        
        risk = (strength_factor * distance_factor * defense_factor)
        return min(risk, 1.0)

    @classmethod
    def should_strike(
        cls,
        risk_score: float,
        observer_threat_tolerance: float
    ) -> Tuple[bool, str]:
        """
        判断是否应该发动打击
        
        Returns:
            (是否打击, 原因描述)
        """
        if risk_score >= cls.STRIKE_RISK_THRESHOLD:
            return True, f"风险评分 {risk_score:.2f} 超过阈值 {cls.STRIKE_RISK_THRESHOLD}"
        
        return False, "风险在可接受范围内"

    @classmethod
    def check_tech_explosion(
        cls,
        current_tech_level: float
    ) -> Tuple[bool, float]:
        """
        检查是否触发技术爆炸
        
        Args:
            current_tech_level: 当前科技水平 (0-1)
            
        Returns:
            (是否爆炸, 爆炸后的科技水平)
        """
        import random
        if random.random() < cls.TECH_EXPLOSION_CHANCE:
            # 技术爆炸带来巨大提升
            new_level = min(current_tech_level + random.uniform(0.3, 0.6), 1.0)
            return True, new_level
        return False, current_tech_level

    @classmethod
    def calculate_distance(
        cls,
        pos1: Tuple[float, float, float],
        pos2: Tuple[float, float, float]
    ) -> float:
        """计算两点之间的欧几里得距离"""
        return math.sqrt(
            (pos1[0] - pos2[0]) ** 2 +
            (pos1[1] - pos2[1]) ** 2 +
            (pos1[2] - pos2[2]) ** 2
        )

    @classmethod
    def validate_subworld_rules(cls, subworld_rules: dict) -> Tuple[bool, str]:
        """
        验证子世界的规则是否违反宇宙宪法
        
        Returns:
            (是否有效, 错误信息)
        """
        forbidden = ["永生", "无法被驱逐", "无视距离", "无条件和平"]
        for keyword in forbidden:
            if keyword in str(subworld_rules):
                return False, f"子世界规则包含禁止词: {keyword}"
        return True, "有效"


# 事件后果映射
RULE_CONSEQUENCES = {
    "high_signal_broadcast": RuleSeverity.STRIKE,
    "defense_too_low": RuleSeverity.WARNING,
    "tech_explosion_detected": RuleSeverity.STRIKE,
    "unprovoked_attack": RuleSeverity.FATAL,  # 会被集体抵制
}
