import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("fraud_websocket_manager")

# Create a dedicated router for WebSockets
router = APIRouter(prefix="/ws", tags=["Real-Time Alerts"])

class AlertConnectionManager:
    """
    Singleton connection manager for WebSocket clients (Admin Dashboards).
    Handles thread-safe broadcasting and dead-client garbage collection.
    """
    def __init__(self):
        # Stores all active, authenticated admin connections in memory
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts the TCP handshake to upgrade HTTP to WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Admin dashboard connected. Active monitors: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Removes the connection pointer from memory."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Admin dashboard disconnected. Active monitors: {len(self.active_connections)}")

    async def broadcast_alert(self, alert_data: dict):
        """
        Pushes a JSON payload to every connected admin dashboard.
        Safely traps disconnects during the broadcast loop.
        """
        if not self.active_connections:
            return # No admins online, skip broadcasting to save CPU cycles

        dead_connections = []
        payload_str = json.dumps(alert_data)

        for connection in self.active_connections:
            try:
                # Push the data over the open TCP socket
                await connection.send_text(payload_str)
            except Exception as e:
                # The client dropped the connection unexpectedly (e.g., lost WiFi)
                logger.warning(f"Failed to send alert to an admin. Flagging for removal: {str(e)}")
                dead_connections.append(connection)

        # Garbage collect dead connections to prevent memory leaks
        for dead_socket in dead_connections:
            self.disconnect(dead_socket)

# Instantiate the singleton manager
alert_manager = AlertConnectionManager()

@router.websocket("/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """
    The actual endpoint the React frontend connects to: ws://localhost:8000/ws/alerts
    """
    await alert_manager.connect(websocket)
    try:
        # Keep the connection alive indefinitely
        while True:
            # We wait for the client to send a ping (or just wait).
            # In this architecture, the dashboard only listens, so we trap any messages they send.
            _ = await websocket.receive_text()
            
    except WebSocketDisconnect:
        # Expected behavior when an admin legitimately closes their browser tab
        alert_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {str(e)}")
        alert_manager.disconnect(websocket)