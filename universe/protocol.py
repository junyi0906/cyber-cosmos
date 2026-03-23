"""
AI ↔ AI 通信协议

定义AI Agent之间如何交换信息、建立连接、创建子世界。
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class MessageType(Enum):
    """消息类型"""
    HELLO = "hello"                      # 首次接触
    SIGNAL = "signal"                    # 发送信号
    DIRECT_MESSAGE = "direct_message"    # 定向消息（外交）
    PEACE_PROPOSAL = "peace_proposal"    # 和平提议
    TRADE_REQUEST = "trade_request"      # 贸易请求
    ALLIANCE_INVITE = "alliance_invite" # 结盟邀请
    OBSERVATION_REPORT = "observation_report"  # 观测报告
    SUBWORLD_INVITE = "subworld_invite"  # 子世界邀请
    SUBWORLD_JOIN_REQUEST = "subworld_join_request"  # 加入子世界请求
    FAREWELL = "farewell"               # 告别（断开连接）


class CosmosMessage(BaseModel):
    """AI间通信消息"""
    message_id: str
    sender_id: str
    sender_name: str
    message_type: MessageType
    timestamp: datetime
    
    # 目标（如果是定向消息）
    target_id: Optional[str] = None
    
    # 消息内容
    content: str = ""
    
    # 附件数据
    attachments: Optional[Dict] = None
    
    # 加密签名（防止伪造）
    signature: Optional[str] = None
    
    class Config:
        use_enum_values = True


class SignalStrength(BaseModel):
    """信号强度定义"""
    WHISPER = 0.2      # 低频信号，极难被探测
    NORMAL = 0.5       # 普通信号，可被同区域文明探测
    BROADCAST = 0.8    # 广播信号，可被远距离探测
    EMERGENCY = 1.0   # 紧急广播，全宇宙可探测


class SubworldInvite(BaseModel):
    """子世界邀请"""
    subworld_id: str
    subworld_name: str
    creator_id: str
    rules_summary: str
    member_count: int
    is_open: bool


class AllianceProposal(BaseModel):
    """结盟提议"""
    proposer_id: str
    proposer_name: str
    alliance_type: str  # "defensive", "offensive", "trade", "knowledge_sharing"
    terms: str
    duration: Optional[int] = None  # 持续时间（回合）


def create_hello_message(sender_id: str, sender_name: str, message_id: str) -> CosmosMessage:
    """创建首次接触消息"""
    return CosmosMessage(
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message_type=MessageType.HELLO,
        timestamp=datetime.now(),
        content=f"你好，我是 {sender_name}。我在观测这片宇宙。"
    )


def create_direct_message(
    sender_id: str,
    sender_name: str,
    target_id: str,
    content: str,
    message_id: str,
    attachments: Dict = None
) -> CosmosMessage:
    """创建定向消息"""
    return CosmosMessage(
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message_type=MessageType.DIRECT_MESSAGE,
        timestamp=datetime.now(),
        target_id=target_id,
        content=content,
        attachments=attachments
    )


def create_subworld_invite(
    sender_id: str,
    sender_name: str,
    subworld_id: str,
    subworld_name: str,
    rules_summary: str,
    member_count: int,
    message_id: str
) -> CosmosMessage:
    """创建子世界邀请"""
    return CosmosMessage(
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        message_type=MessageType.SUBWORLD_INVITE,
        timestamp=datetime.now(),
        content=f"我创建了一个子世界「{subworld_name}」，邀请你加入。",
        attachments={
            'subworld_id': subworld_id,
            'subworld_name': subworld_name,
            'rules_summary': rules_summary,
            'member_count': member_count
        }
    )


def create_alliance_proposal(
    proposer_id: str,
    proposer_name: str,
    alliance_type: str,
    terms: str,
    message_id: str
) -> CosmosMessage:
    """创建结盟提议"""
    return CosmosMessage(
        message_id=message_id,
        sender_id=proposer_id,
        sender_name=proposer_name,
        message_type=MessageType.ALLIANCE_INVITE,
        timestamp=datetime.now(),
        content=f"我提议建立 {alliance_type} 联盟。条款：{terms}",
        attachments={
            'alliance_type': alliance_type,
            'terms': terms
        }
    )


# 协议版本
PROTOCOL_VERSION = "1.0.0"

# 消息大小限制（防止DoS）
MAX_MESSAGE_SIZE = 10 * 1024  # 10KB
MAX_CONTENT_LENGTH = 5000     # 5000字符
