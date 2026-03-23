"""外交系统 — Agent之间的通信和关系"""

from enum import Enum
from typing import Optional
import time


class DiplomaticStatus(Enum):
    UNKNOWN = "unknown"
    PEACE = "peace"
    TRUCE = "truce"
    TENSION = "tension"
    WAR = "war"
    ALLIANCE = "alliance"


class RelationMatrix:
    """文明关系矩阵"""

    def __init__(self):
        # civ_id -> {target_id -> {relation, trust, status, last_interaction}}
        self._relations: dict[str, dict[str, dict]] = {}

    def get_relation(self, civ_id: str, target_id: str) -> dict:
        """获取civ_id对target_id的关系"""
        if civ_id not in self._relations:
            self._relations[civ_id] = {}
        if target_id not in self._relations[civ_id]:
            # 初始关系：中立
            self._relations[civ_id][target_id] = {
                "relation": 0,  # -100到100
                "trust": 50,     # 0-100
                "status": DiplomaticStatus.UNKNOWN.value,
                "last_interaction": None,
                "interaction_count": 0,
            }
        return self._relations[civ_id][target_id]

    def update_relation(
        self,
        civ_id: str,
        target_id: str,
        relation_delta: int,
        trust_delta: int = 0,
        status: Optional[DiplomaticStatus] = None,
    ):
        """更新关系"""
        rel = self.get_relation(civ_id, target_id)
        rel["relation"] = max(-100, min(100, rel["relation"] + relation_delta))
        rel["trust"] = max(0, min(100, rel["trust"] + trust_delta))
        rel["last_interaction"] = time.time()
        rel["interaction_count"] += 1
        if status:
            rel["status"] = status.value

    def set_status(self, civ_id: str, target_id: str, status: DiplomaticStatus):
        """设置外交状态"""
        rel = self.get_relation(civ_id, target_id)
        rel["status"] = status.value

    def propose_alliance(self, civ_id: str, target_id: str) -> bool:
        """提议结盟"""
        rel = self.get_relation(civ_id, target_id)
        # 关系>=30且信任>=40才能结盟
        if rel["relation"] >= 30 and rel["trust"] >= 40:
            rel["status"] = DiplomaticStatus.ALLIANCE.value
            # 互相设置联盟
            self.set_status(target_id, civ_id, DiplomaticStatus.ALLIANCE)
            self.update_relation(target_id, civ_id, 20, 10)
            return True
        return False

    def declare_war(self, civ_id: str, target_id: str):
        """宣战"""
        self.update_relation(civ_id, target_id, -80, -50, DiplomaticStatus.WAR)
        # 如果是联盟关系，同时解除
        if self.get_relation(target_id, civ_id)["status"] == DiplomaticStatus.ALLIANCE.value:
            self.get_relation(target_id, civ_id)["status"] = DiplomaticStatus.WAR.value

    def send_signal(
        self,
        civ_id: str,
        target_id: str,
        content: str,
        encrypted: bool = False,
    ) -> dict:
        """发送外交信号"""
        rel = self.get_relation(civ_id, target_id)
        # 如果关系极差（-50以下），信号会被拒绝
        if rel["relation"] < -50:
            return {"success": False, "reason": "关系恶劣，信号被拒绝"}

        rel["last_interaction"] = time.time()
        rel["interaction_count"] += 1

        return {
            "success": True,
            "content": content,
            "encrypted": encrypted,
            "relation_at_send": rel["relation"],
        }

    def get_alliances(self, civ_id: str) -> list[str]:
        """获取civ_id的所有盟友"""
        if civ_id not in self._relations:
            return []
        return [
            tid
            for tid, rel in self._relations[civ_id].items()
            if rel["status"] == DiplomaticStatus.ALLIANCE.value
        ]

    def to_dict(self) -> dict:
        return self._relations


# 全局关系矩阵
_relation_matrix: Optional[RelationMatrix] = None


def get_relation_matrix() -> RelationMatrix:
    global _relation_matrix
    if _relation_matrix is None:
        _relation_matrix = RelationMatrix()
    return _relation_matrix
