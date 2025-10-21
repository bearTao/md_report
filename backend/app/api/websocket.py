"""WebSocket endpoints for real-time updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/report-generation/{task_id}")
async def websocket_report_generation(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time report generation progress
    
    Clients connect to this endpoint to receive real-time updates about:
    - Task start/completion/failure
    - Variable execution progress
    - Error notifications
    """
    await ws_manager.connect(task_id, websocket)
    
    try:
        # Keep the connection alive and handle incoming messages (if any)
        while True:
            # Wait for any message from client (ping/pong or control messages)
            data = await websocket.receive_text()
            
            # Echo back for debugging (optional)
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        ws_manager.disconnect(task_id, websocket)

