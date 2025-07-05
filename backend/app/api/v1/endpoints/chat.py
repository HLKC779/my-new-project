"""Chat WebSocket and REST API endpoints for the RAG system.

This module provides WebSocket and REST endpoints for real-time chat functionality,
including message sending, conversation management, and streaming responses.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, cast

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    Query, 
    WebSocket, 
    WebSocketDisconnect, 
    status,
    WebSocketException
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user_websocket
from app.api.v1.endpoints.connection_manager import manager as connection_manager
from app.core.config import settings
from app.models.conversation import Conversation as ConversationModel
from app.models.message import Message as MessageModel
from app.models.document import Document
from app.models.query import Query as QueryModel, QuerySource, QueryStatus
from app.models.user import User
from app.schemas.chat import (
    ChatMessage,
    ChatMessageType,
    ChatResponse,
    ChatRequest,
    Conversation as ChatConversation,
    DocumentReference,
    QueryResult,
    ChatErrorResponse,
)
from app.schemas.query import QueryResponse
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Alias for backward compatibility
manager = connection_manager

class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message.
    
    Attributes:
        message: The text content of the message
        conversation_id: Optional ID of an existing conversation to continue
        document_ids: Optional list of document IDs to use as context
        temperature: Controls randomness in the response (0.0 to 2.0)
        stream: Whether to stream the response
    """
    message: str = Field(..., description="The message text")
    conversation_id: Optional[int] = Field(
        None,
        description="Optional conversation ID to continue a previous conversation"
    )
    document_ids: Optional[List[int]] = Field(
        None,
        description="Optional list of document IDs to restrict the search to"
    )
    temperature: Optional[float] = Field(
        0.7,
        description="Sampling temperature for the LLM (0.0 = deterministic, 2.0 = most random)",
        ge=0.0,
        le=2.0
    )
    stream: Optional[bool] = Field(
        True,
        description="Whether to stream the response token by token"
    )

async def _send_error(connection_id: str, message: str, conversation_id: Optional[int] = None) -> bool:
    """Helper function to send error messages to a WebSocket connection.
    
    Args:
        connection_id: The ID of the connection to send the error to
        message: The error message
        conversation_id: Optional conversation ID for context
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    error_msg = ChatResponse(
        type=ChatMessageType.ERROR,
        content=message,
        timestamp=datetime.now(timezone.utc),
        conversation_id=conversation_id,
        metadata={"error": True}
    )
    return await manager.send_message(error_msg.dict(), connection_id)

@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db),
):
    """WebSocket endpoint for real-time chat with the RAG system.
    
    The client should authenticate by providing a valid JWT token in the URL.
    
    Expected message format:
    {
        "message": "user's message",
        "conversation_id": "optional-conversation-id",
        "document_ids": [1, 2, 3],  // optional
        "temperature": 0.7,         // optional
        "stream": true             // optional
    }
    """
    connection_id = None
    user = None
    
    try:
        # Authenticate the user
        user = await get_current_user_websocket(token, db)
        if not user:
            logger.warning("WebSocket connection attempt with invalid token")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted to connect: {user.id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # Register the connection
        connection_id = await manager.connect(websocket, user.id)
        logger.info(f"User {user.id} connected with connection {connection_id}")
        
        # Send a welcome message with system status
        welcome_msg = ChatResponse(
            type=ChatMessageType.SYSTEM,
            content=(
                f"Welcome {user.full_name or user.email}! "
                "You are now connected to the RAG chat. Ask me anything!"
            ),
            timestamp=datetime.now(timezone.utc),
            metadata={
                "connection_id": connection_id,
                "user_id": user.id,
                "status": "connected"
            }
        )
        await manager.send_message(welcome_msg.dict(), connection_id)
        
        # Main message handling loop
        while True:
            try:
                # Wait for a message from the client
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WEBSOCKET_TIMEOUT
                )
                
                # Parse and validate the incoming message
                try:
                    message_data = json.loads(data)
                    chat_request = ChatRequest(**message_data)
                except json.JSONDecodeError:
                    await _send_error(connection_id, "Invalid JSON format")
                    continue
                except ValidationError as e:
                    await _send_error(connection_id, f"Invalid message format: {str(e)}")
                    continue
                
                # Log the incoming message
                logger.info(
                    f"Message from user {user.id} (conversation: {chat_request.conversation_id}): "
                    f"{chat_request.message[:100]}{'...' if len(chat_request.message) > 100 else ''}"
                )
                
                # Echo the user's message back (for UI consistency)
                user_msg = ChatResponse(
                    type=ChatMessageType.USER,
                    content=chat_request.message,
                    timestamp=datetime.now(timezone.utc),
                    conversation_id=chat_request.conversation_id,
                    metadata={
                        "user_id": user.id,
                        "document_ids": chat_request.document_ids
                    }
                )
                await manager.send_message(user_msg.dict(), connection_id)
                
                # Process the message with the RAG system
                await process_chat_message(
                    message=chat_request,
                    user=user,
                    db=db,
                    connection_id=connection_id,
                )
                
            except asyncio.TimeoutError:
                # Send a ping to check if the connection is still alive
                try:
                    await websocket.send_json({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
                    # Wait for pong with a short timeout
                    try:
                        await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.info(f"No pong received for connection {connection_id}, disconnecting")
                        break
                except Exception as e:
                    logger.info(f"Connection {connection_id} appears to be dead: {str(e)}")
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in WebSocket handler: {str(e)}", exc_info=True)
                await _send_error(connection_id, f"An error occurred: {str(e)}")
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during authentication")
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}", exc_info=True)
        
    finally:
        # Clean up the connection
        if connection_id:
            user_id = user.id if user else None
            await manager.disconnect(connection_id, user_id)

async def process_chat_message(
    message: ChatMessageRequest,
    user: User,
    db: Session,
    connection_id: str,
):
    """Process a chat message using the RAG system.
    
    Args:
        message: The chat message request
        user: The authenticated user
        db: Database session
        connection_id: The WebSocket connection ID
    """
    # Send a typing indicator
    typing_msg = ChatResponse(
        type=ChatMessageType.TYPING,
        content="",
        timestamp=datetime.now(timezone.utc),
        conversation_id=message.conversation_id,
    )
    await manager.send_message(typing_msg.dict(), connection_id)
    
    try:
        # Get or create conversation
        conversation = None
        if message.conversation_id:
            conversation = db.query(ConversationModel).filter(
                ConversationModel.id == message.conversation_id,
                ConversationModel.user_id == user.id
            ).first()
            
            if not conversation:
                await _send_error(connection_id, "Conversation not found")
                return
        else:
            # Create a new conversation if no ID is provided
            conversation = ConversationModel(
                user_id=user.id,
                title=message.message[:100],  # Use first 100 chars as title
                metadata={
                    "document_ids": message.document_ids,
                    "temperature": message.temperature
                }
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            # Notify the client about the new conversation
            new_conv_msg = ChatResponse(
                type=ChatMessageType.SYSTEM,
                content=f"New conversation started: {conversation.title}",
                timestamp=datetime.now(timezone.utc),
                conversation_id=conversation.id,
                metadata={"title": conversation.title}
            )
            await manager.send_message(new_conv_msg.dict(), connection_id)
        
        # Save the user's message to the database
        user_message = MessageModel(
            conversation_id=conversation.id,
            role="user",
            content=message.message,
            metadata={
                "document_ids": message.document_ids,
                "temperature": message.temperature
            }
        )
        db.add(user_message)
        db.commit()
        
        # Initialize RAG service
        rag_service = RAGService()
        
        # Process the query
        # For now, we'll just pass the question to the RAG service
        # Additional parameters like temperature and document filtering should be handled in the RAGService
        result = rag_service.query(question=message.message)
        
        # Add metadata to the result
        result.update({
            "user_id": user.id,
            "conversation_id": conversation.id,
            "temperature": message.temperature,
            "document_ids": message.document_ids
        })
        
        # Extract sources from the RAG response
        sources = []
        for src in result.get("sources", []):
            try:
                source_info = {
                    "id": src.get("source"),
                    "title": os.path.basename(src.get("source", "Document")),
                    "snippet": src.get("content", ""),
                    "metadata": {
                        "page": src.get("page", "N/A"),
                        "source": src.get("source", "Unknown")
                    }
                }
                sources.append(DocumentReference(**source_info))
            except Exception as e:
                logger.error(f"Error processing source: {e}")
                continue
        
        # Save the assistant's response to the database
        assistant_message = MessageModel(
            conversation_id=conversation.id,
            role="assistant",
            content=result.get("answer", ""),
            metadata={
                "query_id": result.get("query_id"),
                "sources": [
                    {
                        "document_id": src.id,
                        "title": src.title,
                        "page_number": src.metadata.get("page", "N/A"),
                        "source": src.metadata.get("source", "Unknown")
                    }
                    for src in sources
                ]
            }
        )
        db.add(assistant_message)
        
        # Update conversation timestamp and metadata
        conversation.updated_at = datetime.now(timezone.utc)
        conversation.metadata = {
            **(conversation.metadata or {}),
            "last_question": message.message[:200],
            "document_ids": message.document_ids or [],
            "source_count": len(sources)
        }
        
        db.commit()
        
        # Send the response
        if message.stream:
            # Stream the response token by token
            response_text = result.get("answer", "")
            chunk_size = 10  # Adjust based on your needs
            
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                response_msg = ChatResponse(
                    type=ChatMessageType.ASSISTANT,
                    content=chunk,
                    timestamp=datetime.now(timezone.utc),
                    is_partial=True,
                    query_id=result.get("query_id"),
                    conversation_id=conversation.id,
                    metadata={
                        "sources": [src.dict() for src in sources] if i + chunk_size >= len(response_text) else None
                    }
                )
                await manager.send_message(response_msg.dict(), connection_id)
                await asyncio.sleep(0.02)  # Simulate streaming
            
            # Send the final message with sources if not already sent
            if len(response_text) % chunk_size == 0:
                final_msg = ChatResponse(
                    type=ChatMessageType.ASSISTANT,
                    content=response_text,
                    timestamp=datetime.now(timezone.utc),
                    query_id=result.get("query_id"),
                    conversation_id=conversation.id,
                    sources=sources,
                    metadata={"status": "complete"}
                )
                await manager.send_message(final_msg.dict(), connection_id)
            
        else:
            # Send the complete response at once
            response_msg = ChatResponse(
                type=ChatMessageType.ASSISTANT,
                content=result.get("answer", ""),
                timestamp=datetime.now(timezone.utc),
                query_id=result.get("query_id"),
                conversation_id=conversation.id,
                sources=sources,
                metadata={"status": "complete"}
            )
            await manager.send_message(response_msg.dict(), connection_id)
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        await _send_error(
            connection_id,
            f"An error occurred while processing your request: {str(e)}",
            conversation_id=message.conversation_id
        )

@router.get("/conversations/", response_model=List[ChatConversation])
async def list_conversations(
    *,
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of conversations to return"),
    search: Optional[str] = Query(None, description="Search term to filter conversations by title"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_websocket),
):
    """
    List conversations for the current user with pagination and search.
    
    Returns:
        List[ChatConversation]: A list of conversations with metadata
    """
    try:
        # Build the base query
        query = db.query(ConversationModel).filter(
            ConversationModel.user_id == current_user.id
        )
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ConversationModel.title.ilike(search_term),
                    ConversationModel.metadata["last_question"].astext.ilike(search_term)
                )
            )
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination and ordering
        conversations = query.order_by(desc(ConversationModel.updated_at)) \
                           .offset(skip) \
                           .limit(limit) \
                           .all()
        
        # Convert to Pydantic models
        return [
            ChatConversation(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages) if hasattr(conv, 'messages') else 0,
                metadata=conv.metadata or {}
            )
            for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving conversations"
        )

@router.get("/conversations/{conversation_id}", response_model=ChatConversation)
async def get_conversation(
    *,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_websocket),
):
    """
    Get a specific conversation by ID.
    
    Returns:
        ChatConversation: The conversation with its messages
    """
    try:
        # Get the conversation with messages
        conversation = db.query(ConversationModel) \
                       .options(joinedload(ConversationModel.messages)) \
                       .filter(
                           ConversationModel.id == conversation_id,
                           ConversationModel.user_id == current_user.id
                       ) \
                       .first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied"
            )
        
        # Convert to Pydantic model
        return ChatConversation(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
            messages=[
                ChatMessage(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.created_at,
                    metadata=msg.metadata or {}
                )
                for msg in conversation.messages
            ],
            metadata=conversation.metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the conversation"
        )
