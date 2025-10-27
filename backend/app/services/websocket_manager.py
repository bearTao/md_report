"""WebSocket connection manager for real-time progress updates"""
from typing import Dict, Set, Any
from fastapi import WebSocket
from datetime import datetime
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class WSEventType(str, Enum):
    """WebSocket event types"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    RENDER_FAILED = "render_failed"
    VARIABLE_STARTED = "variable_started"
    VARIABLE_PROGRESS = "variable_progress"
    VARIABLE_COMPLETED = "variable_completed"
    VARIABLE_FAILED = "variable_failed"
    HEARTBEAT = "heartbeat"


class WebSocketManager:
    """Manages WebSocket connections for task progress updates"""
    
    def __init__(self):
        # task_id -> set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        """Register a new WebSocket connection for a task"""
        await websocket.accept()
        
        if task_id not in self._connections:
            self._connections[task_id] = set()
        
        self._connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task {task_id}. Total connections: {len(self._connections[task_id])}")
    
    def disconnect(self, task_id: str, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            
            if not self._connections[task_id]:
                del self._connections[task_id]
            
            logger.info(f"WebSocket disconnected for task {task_id}")
    
    async def send_event(self, task_id: str, event_type: WSEventType, data: Dict[str, Any]):
        """Send an event to all connections for a task"""
        if task_id not in self._connections:
            logger.debug(f"No WebSocket connections for task {task_id}, skipping event {event_type}")
            return
        
        event = {
            "type": event_type.value,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        disconnected = set()
        
        for websocket in self._connections[task_id]:
            try:
                await websocket.send_json(event)
                logger.debug(f"Sent event {event_type} to WebSocket for task {task_id}")
            except Exception as e:
                logger.error(f"Error sending WebSocket event: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(task_id, ws)
    
    async def broadcast_task_started(self, task_id: str, template_id: str, queued_at: datetime, started_at: datetime):
        """Broadcast task started event"""
        await self.send_event(task_id, WSEventType.TASK_STARTED, {
            "template_id": template_id,
            "queued_at": queued_at.isoformat() if queued_at else None,
            "started_at": started_at.isoformat() if started_at else None
        })
    
    async def broadcast_task_completed(self, task_id: str, report_id: str, summary: Dict[str, Any]):
        """Broadcast task completed event"""
        await self.send_event(task_id, WSEventType.TASK_COMPLETED, {
            "report_id": report_id,
            "summary": summary
        })
    
    async def broadcast_task_failed(self, task_id: str, error: Dict[str, str], summary: Dict[str, Any]):
        """Broadcast task failed event"""
        await self.send_event(task_id, WSEventType.TASK_FAILED, {
            "error": error,
            "summary": summary
        })
    
    async def broadcast_render_failed(self, task_id: str, error: Dict[str, Any]):
        """Broadcast template render failure"""
        await self.send_event(task_id, WSEventType.RENDER_FAILED, {
            "error": error
        })
    
    async def broadcast_variable_started(
        self, 
        task_id: str, 
        variable_name: str, 
        source: str, 
        dependencies: list,
        started_at: datetime
    ):
        """Broadcast variable started event"""
        await self.send_event(task_id, WSEventType.VARIABLE_STARTED, {
            "variable_name": variable_name,
            "source": source,
            "dependencies": dependencies,
            "started_at": started_at.isoformat() if started_at else None
        })
    
    async def broadcast_variable_progress(
        self, 
        task_id: str, 
        variable_name: str, 
        progress: int,
        info: Dict[str, Any] = None
    ):
        """Broadcast variable progress event (for AI generation)"""
        await self.send_event(task_id, WSEventType.VARIABLE_PROGRESS, {
            "variable_name": variable_name,
            "progress": progress,
            "info": info or {}
        })
    
    async def broadcast_variable_completed(
        self, 
        task_id: str, 
        variable_name: str, 
        duration_ms: int,
        result_preview: Any = None
    ):
        """Broadcast variable completed event"""
        await self.send_event(task_id, WSEventType.VARIABLE_COMPLETED, {
            "variable_name": variable_name,
            "duration_ms": duration_ms,
            "result_preview": result_preview
        })
    
    async def broadcast_variable_failed(
        self, 
        task_id: str, 
        variable_name: str, 
        error: Dict[str, str],
        duration_ms: int
    ):
        """Broadcast variable failed event"""
        await self.send_event(task_id, WSEventType.VARIABLE_FAILED, {
            "variable_name": variable_name,
            "error": error,
            "duration_ms": duration_ms
        })
    
    async def send_heartbeat(self, task_id: str):
        """Send heartbeat to keep connection alive"""
        await self.send_event(task_id, WSEventType.HEARTBEAT, {})


# Global WebSocket manager instance
ws_manager = WebSocketManager()

