from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter()

async def establish_connection(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            # Keeps the connection alive; optionally handle incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)

@router.websocket("/ws/users/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await establish_connection(websocket, user_id)
    
@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await establish_connection(websocket, project_id)


@router.websocket("/ws/threads/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await establish_connection(websocket, thread_id)
