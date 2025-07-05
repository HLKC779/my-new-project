"""WebSocket connection management for real-time chat.

This module provides the ConnectionManager class which handles WebSocket connections,
including connection tracking, message sending, and broadcasting to users.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Set, cast

from fastapi import WebSocket, WebSocketDisconnect, WebSocketException

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages active WebSocket connections and handles broadcasting.
    
    This class maintains a mapping of connection IDs to WebSocket connections,
    as well as a mapping of user IDs to their active connections. It provides
    methods for connecting, disconnecting, and sending messages to connections.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        # Maps connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Maps user_id -> Set[connection_id]
        self.user_connections: Dict[int, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int) -> str:
        """Register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register
            user_id: The ID of the user making the connection
            
        Returns:
            str: The generated connection ID
            
        Raises:
            WebSocketException: If there's an error accepting the connection
        """
        connection_id = str(uuid.uuid4())
        try:
            await websocket.accept()
            self.active_connections[connection_id] = websocket
            
            # Track connections by user using a set for O(1) lookups
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            logger.info(f"New connection: {connection_id} for user {user_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise WebSocketException("Failed to establish WebSocket connection") from e
    
    async def disconnect(self, connection_id: str, user_id: Optional[int] = None) -> None:
        """Remove a WebSocket connection.
        
        Args:
            connection_id: The ID of the connection to remove
            user_id: Optional user ID for the connection (will be looked up if not provided)
            
        Note:
            If user_id is not provided, this method will attempt to find the user ID
            by searching through the user_connections mapping.
        """
        # If user_id is not provided, try to find it
        if user_id is None:
            for uid, conn_ids in list(self.user_connections.items()):
                if connection_id in conn_ids:
                    user_id = uid
                    break
        
        # Close and remove the connection
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket {connection_id}: {e}")
            finally:
                self.active_connections.pop(connection_id, None)
        
        # Clean up user tracking
        if user_id is not None and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"Connection closed: {connection_id} for user {user_id or 'unknown'}")
    
    async def send_message(self, message: Dict[str, Any], connection_id: str) -> bool:
        """Send a message to a specific connection.
        
        Args:
            message: The message to send (will be converted to JSON)
            connection_id: The ID of the connection to send to
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
            
        Note:
            If sending fails, the connection will be automatically closed and cleaned up.
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Attempted to send to non-existent connection: {connection_id}")
            return False
            
        websocket = self.active_connections[connection_id]
        try:
            await websocket.send_json(message)
            return True
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected while sending to {connection_id}")
            await self.disconnect(connection_id)
            return False
            
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_user(self, message: Dict[str, Any], user_id: int) -> int:
        """Send a message to all connections for a specific user.
        
        Args:
            message: The message to send
            user_id: The ID of the user to send to
            
        Returns:
            int: The number of connections the message was successfully sent to
        """
        if user_id not in self.user_connections:
            return 0
            
        success_count = 0
        for connection_id in list(self.user_connections[user_id]):
            if await self.send_message(message, connection_id):
                success_count += 1
                
        return success_count
    
    def get_user_connections(self, user_id: int) -> List[str]:
        """Get all connection IDs for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List[str]: List of connection IDs for the user
        """
        return list(self.user_connections.get(user_id, set()))
    
    def get_connection_count(self, user_id: Optional[int] = None) -> int:
        """Get the number of active connections.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            int: Number of active connections
        """
        if user_id is not None:
            return len(self.user_connections.get(user_id, set()))
        return len(self.active_connections)

# Global connection manager instance
manager = ConnectionManager()
