"""
Web界面 — 宇宙观测台

人类观察者界面，可以旁观宇宙中发生的一切。
"""

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import httpx
import uvicorn

app = FastAPI(title="Cyber Cosmos Observatory")
templates = Jinja2Templates(directory="web/templates")


class BroadcastManager:
    def __init__(self):
        self.connections: list = []
    
    async def connect(self, websocket):
        await websocket.accept()
        self.connections.append(websocket)
    
    def disconnect(self, websocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for conn in self.connections[:]:
            try:
                await conn.send_json(message)
            except Exception:
                self.connections.remove(conn)


broadcast_manager = BroadcastManager()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request
    })


@app.get("/universe")
async def get_universe():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/universe")
        return resp.json()


@app.get("/civilizations")
async def list_civilizations():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/civilizations")
        return resp.json()


@app.get("/history")
async def get_history():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/history")
        return resp.json()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await broadcast_manager.connect(websocket)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/universe")
            universe = resp.json()
            resp = await client.get("http://localhost:8000/civilizations")
            civilizations = resp.json()
            resp = await client.get("http://localhost:8000/history")
            history = resp.json()
        
        await websocket.send_json({
            'type': 'init',
            'universe': universe,
            'civilizations': civilizations,
            'history': history[-50:]
        })
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get('type') == 'observe':
                civ_id = msg.get('civilization_id')
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:8000/civilizations/{civ_id}")
                    civ = resp.json()
                    resp = await client.get("http://localhost:8000/history")
                    history = resp.json()
                
                await websocket.send_json({
                    'type': 'civilization_detail',
                    'civilization': civ,
                    'history': [h for h in history if 
                                h.get('actor_id') == civ_id or h.get('target_id') == civ_id][-20:]
                })
    
    except Exception:
        broadcast_manager.disconnect(websocket)


def run_web(port: int = 8080):
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_web()
