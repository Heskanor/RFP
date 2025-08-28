from fastapi import WebSocket
from typing import Dict, List
from collections import defaultdict
import json

class WebSocketManager:
    def __init__(self):
        # Allow multiple connections per user
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
    
    async def connect(self, channel_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[channel_id].append(websocket)

    def disconnect(self, channel_id: str, websocket: WebSocket):
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]

    async def send(self, channel_id: str, event: str, data: dict, completed: bool = False):
        """
        Send a structured event to a user's WebSocket(s).
        """
        message = json.dumps({"event": event, "data": data, "completed": completed})
        for ws in self.active_connections.get(channel_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(channel_id, ws)

    async def broadcast(self, event: str, data: dict):
        """
        Send a message to all connected users.
        """
        message = json.dumps({"event": event, "data": data})
        for channel_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    self.disconnect(channel_id, ws)


        
ws_manager = WebSocketManager()