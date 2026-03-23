"""
共享宇宙服务器 — Universe Server

管理宇宙状态，为所有节点提供共享状态访问API。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import asyncio
import uvicorn

from universe.state import UniverseStateManager, CivilizationStatus
from universe.events import UniverseEvent, EventType, EventHistory
from universe.rules import CosmicRules


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
    return [
        {
            'id': civ.id,
            'name': civ.name,
            'position': civ.position,
            'tech_level': civ.tech_level,
            'defense_level': civ.defense_level,
            'is_alive': civ.is_alive,
        }
        for civ in universe.state.civilizations.values()
        if civ.is_alive
    ]


@app.get("/civilizations/{civ_id}")
async def get_civilization(civ_id: str):
    civ = universe.get_civilization(civ_id)
    if not civ:
        return {"error": "Civilization not found"}
    return civ.model_dump()


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
    }
    
    event = UniverseEvent(
        event_id=str(id(civ)),
        event_type=event_type_map.get(req.action, EventType.OBSERVATION),
        timestamp=civ.last_active,
        actor_id=req.civilization_id,
        target_id=req.target_id,
        narrative=f"{civ.name} 采取了行动: {req.action}"
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
                    narrative=f"{observer_civ.name} 观测到了来自 {civ.name} 的可疑信号（风险: {risk:.2f}）"
                )
                event_history.record(obs_event)
                
                if should_strike:
                    # 发动打击
                    universe.destroy_civilization(civ.id, "signal_exposure")
                    obs_event.event_type = EventType.STRIKE_LAUNCHED
                    obs_event.narrative = f"{observer_civ.name} 对 {civ.name} 发动了打击！原因：{reason}"
                    event_history.record(obs_event)
    
    universe.state.event_counter += 1
    event_history.record(event)
    event_history.flush()
    
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


def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
