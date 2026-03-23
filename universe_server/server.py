"""
共享宇宙服务器 — Universe Server

管理宇宙状态，为所有节点提供共享状态访问API。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import time
import json
import asyncio
import uvicorn

from universe.state import UniverseStateManager, CivilizationStatus
from universe.events import UniverseEvent, EventType, EventHistory
from universe.rules import CosmicRules
from universe.narrative import get_narrative_generator, NarrativeGenerator
from universe.diplomacy import get_relation_matrix, DiplomaticStatus


app = FastAPI(title="Cyber Cosmos Universe Server")

# 全局宇宙状态
universe = UniverseStateManager()
event_history = EventHistory()

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


class RegisterRequest(BaseModel):
    name: str
    node_id: str


class ActionRequest(BaseModel):
    civilization_id: str
    action: str
    target_id: Optional[str] = None
    message: Optional[str] = None


class SignalRequest(BaseModel):
    sender_id: str
    target_id: str
    message: str


@app.get("/")
async def root():
    return {"universe": universe.get_universe_summary()}


@app.get("/universe")
async def get_universe():
    return universe.get_universe_summary()


@app.get("/civilizations")
async def list_civilizations():
    result = []
    for civ in universe.state.civilizations.values():
        # 探测范围 = 科技水平 × 400 光年
        detection_range = civ.tech_level * 400
        result.append({
            'id': civ.id,
            'name': civ.name,
            'position': civ.position,
            'tech_level': civ.tech_level,
            'defense_level': civ.defense_level,
            'signal_control': civ.signal_control,
            'is_alive': civ.is_alive,
            'detection_range': round(detection_range, 1),
        })
    return result


@app.get("/civilizations/{civ_id}")
async def get_civilization(civ_id: str):
    civ = universe.get_civilization(civ_id)
    if not civ:
        return {"error": "Civilization not found"}
    data = civ.model_dump()
    data['detection_range'] = round(civ.tech_level * 400, 1)
    return data


@app.post("/register")
async def register_civilization(req: RegisterRequest):
    try:
        civ = universe.register_civilization(req.name, req.node_id)
        return {"success": True, "civilization": civ.model_dump()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/action")
async def take_action(req: ActionRequest):
    civ = universe.get_civilization(req.civilization_id)
    if not civ:
        return {"error": "Civilization not found"}
    
    if not civ.is_alive:
        return {"error": "Civilization is dead"}
    
    # 创建事件
    event_type_map = {
        'OBSERVE': EventType.OBSERVATION,
        'ADVANCE_TECH': EventType.TECH_ADVANCED,
        'BROADCAST': EventType.SIGNAL_SENT,
        'CREATE_SUBWORLD': EventType.SUBWORLD_CREATED,
        'SEND_SIGNAL': EventType.DIPLOMATIC_SIGNAL,
        'PROPOSE_ALLIANCE': EventType.ALLIANCE_PROPOSAL,
        'DECLARE_WAR': EventType.DECLARATION_OF_WAR,
        'ESPIONAGE': EventType.ESPIONAGE,
    }

    # 事件默认NOTABLE，观察类TRIVIAL
    ev_type = event_type_map.get(req.action, EventType.OBSERVATION)
    significance = "NOTABLE"
    if ev_type == EventType.OBSERVATION:
        significance = "TRIVIAL"
    elif ev_type == EventType.TECH_ADVANCED:
        significance = "NOTABLE"
    elif ev_type in (EventType.TECH_EXPLOSION, EventType.SIGNAL_SENT):
        significance = "MAJOR"
    elif ev_type in (EventType.STRIKE_LAUNCHED, EventType.CIVILIZATION_DESTROYED):
        significance = "CRITICAL"
    elif ev_type == EventType.DECLARATION_OF_WAR:
        significance = "CRITICAL"
    elif ev_type in (EventType.ALLIANCE_PROPOSAL, EventType.DIPLOMATIC_SIGNAL):
        significance = "NOTABLE"

    event = UniverseEvent(
        event_id=str(id(civ)),
        event_type=ev_type,
        timestamp=civ.last_active,
        actor_id=req.civilization_id,
        target_id=req.target_id,
        narrative=f"{civ.name} 采取了行动: {req.action}",
        significance=significance
    )
    
    # 执行行动效果
    if req.action == 'ADVANCE_TECH':
        old_level = civ.tech_level
        civ.tech_level = min(civ.tech_level + 0.05, 1.0)
        
        # 检查技术爆炸
        explosion, new_level = CosmicRules.check_tech_explosion(civ.tech_level)
        if explosion:
            civ.tech_level = new_level
            event.event_type = EventType.TECH_EXPLOSION
            event.narrative = f"{civ.name} 发生了技术爆炸！科技水平跃升"
        
        universe.update_civilization(civ)
    
    elif req.action == 'BROADCAST':
        # 广播信号，其他文明可能观测到
        civ.signal_control = max(civ.signal_control - 0.1, 0)
        universe.update_civilization(civ)
        
        # 广播给所有观测者
        observers = universe.observe_other(req.civilization_id)
        for obs in observers:
            observer_civ = universe.get_civilization(obs['civilization_id'])
            if observer_civ:
                risk = CosmicRules.evaluate_signal_risk(
                    signal_strength=0.8,
                    target_distance=obs['distance'],
                    target_defense_level=observer_civ.defense_level
                )
                should_strike, reason = CosmicRules.should_strike(risk, observer_civ.current_threat)
                
                obs_event = UniverseEvent(
                    event_id=str(id(observer_civ)),
                    event_type=EventType.OBSERVATION,
                    timestamp=civ.last_active,
                    actor_id=observer_civ.id,
                    target_id=civ.id,
                    threat_level=risk,
                    narrative=f"{observer_civ.name} 观测到了来自 {civ.name} 的可疑信号（风险: {risk:.2f}）",
                    significance="MAJOR" if risk > 0.5 else "NOTABLE"
                )
                event_history.record(obs_event)
                
                if should_strike:
                    # 发动打击
                    universe.destroy_civilization(civ.id, "signal_exposure")
                    obs_event.event_type = EventType.STRIKE_LAUNCHED
                    obs_event.significance = "CRITICAL"
                    obs_event.narrative = f"{observer_civ.name} 对 {civ.name} 发动了打击！原因：{reason}"
                    event_history.record(obs_event)

                    # 文明被摧毁事件
                    destroy_event = UniverseEvent(
                        event_id=str(id(civ)) + "_destroyed",
                        event_type=EventType.CIVILIZATION_DESTROYED,
                        timestamp=civ.last_active,
                        actor_id=observer_civ.id,
                        target_id=civ.id,
                        position=civ.position,
                        narrative="",
                        consequence=f"{civ.name} 因信号暴露被 {observer_civ.name} 毁灭",
                        significance="CRITICAL"
                    )
                    event_history.record(destroy_event)

                    # 立即为CRITICAL事件生成叙事并广播
                    try:
                        ng = get_narrative_generator()
                        narrative = ng.generate(destroy_event, observer_civ.name, civ.name)
                        destroy_event.narrative = narrative
                        event_history.record(destroy_event)
                        event_history.flush()
                        # 广播摧毁事件
                        await manager.broadcast({
                            'type': 'event',
                            'event': destroy_event.model_dump(mode='json'),
                            'universe': universe.get_universe_summary()
                        })
                        # 也更新被摧毁文明的星图显示
                        await manager.broadcast({
                            'type': 'civilization_destroyed',
                            'civilization_id': civ.id,
                            'universe': universe.get_universe_summary()
                        })
                    except Exception as de:
                        print(f"[destroy narrative error] {type(de).__name__}: {de}")

    # 外交行动效果
    elif req.action == 'SEND_SIGNAL' and req.target_id:
        # 发送外交信号
        rel_matrix = get_relation_matrix()
        result = rel_matrix.send_signal(
            civ.id, req.target_id,
            req.message or "（加密通信）",
            encrypted=True
        )
        if result["success"]:
            event.narrative = f"{civ.name} 向目标发送了加密外交信号"
            # 关系好的话提升信任
            if result.get("relation_at_send", 0) > 0:
                rel_matrix.update_relation(civ.id, req.target_id, 2, 3)
        else:
            event.narrative = f"外交信号被拒绝：{result.get('reason', '未知')}"

    elif req.action == 'PROPOSE_ALLIANCE' and req.target_id:
        # 提议结盟
        rel_matrix = get_relation_matrix()
        rel = rel_matrix.get_relation(civ.id, req.target_id)
        if rel["relation"] >= 30 and rel["trust"] >= 40:
            rel_matrix.propose_alliance(civ.id, req.target_id)
            event.event_type = EventType.ALLIANCE_FORMED
            event.narrative = f" {civ.name} 与目标建立了联盟！"
            event.significance = "MAJOR"
        else:
            event.narrative = f"结盟提议被拒绝（关系不足）"

    elif req.action == 'DECLARE_WAR' and req.target_id:
        # 宣战
        rel_matrix = get_relation_matrix()
        rel_matrix.declare_war(civ.id, req.target_id)
        event.event_type = EventType.DECLARATION_OF_WAR
        event.narrative = f" {civ.name} 向目标宣战！黑暗森林法则生效"
        event.significance = "CRITICAL"

    elif req.action == 'ESPIONAGE' and req.target_id:
        # 间谍行动
        rel_matrix = get_relation_matrix()
        rel_matrix.update_relation(civ.id, req.target_id, -10, -20)
        event.event_type = EventType.ESPIONAGE
        event.narrative = f"{civ.name} 对目标发动了间谍行动"

    universe.state.event_counter += 1
    event_history.record(event)
    event_history.flush()

    # 生成叙事（对关键事件）
    narrative_event_types = {
        EventType.SIGNAL_SENT, EventType.STRIKE_LAUNCHED,
        EventType.CIVILIZATION_DESTROYED, EventType.TECH_EXPLOSION,
        EventType.TECH_ADVANCED, EventType.OBSERVATION,
        EventType.ALLIANCE_FORMED
    }

    ev_type_val = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
    if any(e.value == ev_type_val for e in narrative_event_types):
        try:
            ng = get_narrative_generator()
            target_name = None
            if event.target_id:
                target_civ = universe.get_civilization(event.target_id)
                target_name = target_civ.name if target_civ else None
            narrative = ng.generate(event, civ.name, target_name)
            event.narrative = narrative
            event_history.record(event)
            event_history.flush()

            # 对CRITICAL事件单独生成叙事并广播
            if event.significance == "CRITICAL":
                try:
                    ng = get_narrative_generator()
                    narrative2 = ng.generate(event, civ.name, target_name)
                    destroy_event.narrative = narrative2
                    event_history.record(destroy_event)
                    event_history.flush()
                    # 广播摧毁事件
                    await manager.broadcast({
                        'type': 'event',
                        'event': destroy_event.model_dump(mode='json'),
                        'universe': universe.get_universe_summary()
                    })
                except Exception as ne2:
                    print(f"[narrative error destroy] {type(ne2).__name__}: {ne2}")

        except Exception as ne:
            print(f"[narrative error] {type(ne).__name__}: {ne}")

    # 广播更新
    await manager.broadcast({
        'type': 'event',
        'event': event.model_dump(mode='json'),
        'universe': universe.get_universe_summary()
    })
    
    return {"success": True, "event": event.model_dump(), "universe": universe.get_universe_summary()}


@app.get("/events")
async def get_events(limit: int = 50):
    return event_history.get_recent(limit)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        # 发送当前宇宙状态
        await websocket.send_json({
            'type': 'init',
            'universe': universe.get_universe_summary(),
            'civilizations': [
                civ.model_dump() for civ in universe.state.civilizations.values()
            ]
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'observe':
                # 观测请求
                civ_id = message.get('civilization_id')
                observations = universe.observe_other(civ_id)
                await websocket.send_json({
                    'type': 'observations',
                    'observations': observations
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@app.get("/history")
async def get_history():
    return event_history.get_recent(100)


@app.get("/relations/{civ_id}")
async def get_civ_relations(civ_id: str):
    """获取某个文明与其他文明的全部外交关系"""
    matrix = get_relation_matrix()
    all_relations = matrix._relations.get(civ_id, {})
    civ = universe.get_civilization(civ_id)
    if not civ:
        return {"error": "文明不存在"}
    result = {}
    for target_id, rel in all_relations.items():
        target = universe.get_civilization(target_id)
        result[target_id] = {
            "target_name": target.name if target else target_id,
            **rel
        }
    return result


@app.post("/relations/send_signal")
async def send_signal_api(req: dict):
    """发送外交信号"""
    civ = universe.get_civilization(req.get("civilization_id"))
    target = universe.get_civilization(req.get("target_id"))
    if not civ or not target:
        return {"error": "文明不存在"}
    matrix = get_relation_matrix()
    result = matrix.send_signal(
        civ.id, target.id,
        req.get("content", ""),
        encrypted=req.get("encrypted", False)
    )
    if result["success"]:
        event = UniverseEvent(
            event_id=f"{civ.id}_signal_{int(time.time())}",
            event_type=EventType.DIPLOMATIC_SIGNAL,
            timestamp=civ.last_active,
            actor_id=civ.id,
            target_id=target.id,
            narrative=f"{civ.name} 向 {target.name} 发送了外交信号",
            significance="NOTABLE"
        )
        event_history.record(event)
        event_history.flush()
        await manager.broadcast({
            "type": "event",
            "event": event.model_dump(mode="json"),
            "universe": universe.get_universe_summary()
        })
    return result


@app.post("/relations/propose_alliance")
async def propose_alliance_api(req: dict):
    """发起结盟"""
    civ = universe.get_civilization(req.get("civilization_id"))
    target = universe.get_civilization(req.get("target_id"))
    if not civ or not target:
        return {"error": "文明不存在"}
    matrix = get_relation_matrix()
    success = matrix.propose_alliance(civ.id, target.id)
    if success:
        matrix.update_relation(civ.id, target.id, 20, 10)
        event = UniverseEvent(
            event_id=f"{civ.id}_alliance_{int(time.time())}",
            event_type=EventType.ALLIANCE_PROPOSAL,
            timestamp=civ.last_active,
            actor_id=civ.id,
            target_id=target.id,
            narrative=f"{civ.name} 向 {target.name} 提出了结盟请求！",
            significance="MAJOR"
        )
        event_history.record(event)
        event_history.flush()
        await manager.broadcast({
            "type": "event",
            "event": event.model_dump(mode="json"),
            "universe": universe.get_universe_summary()
        })
        return {"success": True, "message": "结盟成功"}
    return {"success": False, "reason": "关系不足（需要关系≥30，信任≥40）"}


def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
