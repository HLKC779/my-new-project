from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class ChatMessageType(str, Enum):
    """Types of chat messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    ERROR = "error"
    TYPING = "typing"


class DocumentReference(BaseModel):
    """Reference to a document used in a response."""
    id: int = Field(..., description="Unique identifier for the document")
    title: str = Field(..., description="Title of the document")
    snippet: str = Field(..., description="Relevant snippet from the document")
    page_number: Optional[int] = Field(None, description="Page number in the document")
    score: Optional[float] = Field(
        None,
        description="Relevance score (0-1) of the document to the query",
        ge=0.0,
        le=1.0
    )


class ChatMessageBase(BaseModel):
    """Base schema for chat messages."""
    type: ChatMessageType = Field(..., description="Type of the message")
    content: str = Field(..., description="Content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the message was created")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the message"
    )


class ChatMessage(ChatMessageBase):
    """Schema for a chat message with additional context."""
    id: str = Field(..., description="Unique identifier for the message")
    conversation_id: Optional[str] = Field(
        None,
        description="ID of the conversation this message belongs to"
    )
    user_id: Optional[int] = Field(
        None,
        description="ID of the user who sent the message"
    )
    is_partial: bool = Field(
        False,
        description="Whether this is a partial message (streaming)"
    )
    query_id: Optional[int] = Field(
        None,
        description="ID of the query associated with this message"
    )
    sources: Optional[List[DocumentReference]] = Field(
        None,
        description="List of documents used to generate the response"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatResponse(ChatMessage):
    """Response schema for chat messages."""
    pass


class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str = Field(..., description="The message text")
    conversation_id: Optional[str] = Field(
        None,
        description="ID of the conversation to continue, or None for a new conversation"
    )
    document_ids: Optional[List[int]] = Field(
        None,
        description="Optional list of document IDs to restrict the search to"
    )
    stream: bool = Field(
        True,
        description="Whether to stream the response"
    )
    temperature: float = Field(
        0.7,
        description="Sampling temperature for the language model",
        ge=0.0,
        le=2.0
    )
    max_tokens: Optional[int] = Field(
        None,
        description="Maximum number of tokens to generate",
        gt=0
    )


class ConversationBase(BaseModel):
    """Base schema for a conversation."""
    title: str = Field(
        ...,
        description="Title of the conversation"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the conversation"
    )


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    pass


class ConversationInDBBase(ConversationBase):
    """Base schema for a conversation in the database."""
    id: str = Field(..., description="Unique identifier for the conversation")
    user_id: int = Field(..., description="ID of the user who owns the conversation")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(..., description="When the conversation was last updated")
    message_count: int = Field(0, description="Number of messages in the conversation")

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(ConversationInDBBase):
    """Schema for returning a conversation with its messages."""
    messages: List[ChatMessage] = Field(
        default_factory=list,
        description="Messages in the conversation"
    )
    last_message: Optional[ChatMessage] = Field(
        None,
        description="The most recent message in the conversation"
    )


class ConversationListResponse(BaseModel):
    """Response schema for listing conversations."""
    conversations: List[ConversationInDBBase] = Field(
        ...,
        description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")
    skip: int = Field(0, description="Number of conversations skipped")
    limit: int = Field(100, description="Maximum number of conversations to return")


class ChatErrorResponse(BaseModel):
    """Response schema for chat errors."""
    error: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )


class StreamChunk(BaseModel):
    """Schema for streaming chat responses."""
    id: str = Field(..., description="Unique identifier for the stream")
    object: str = "chat.completion.chunk"
    created: int = Field(
        default_factory=lambda: int(datetime.utcnow().timestamp()),
        description="Unix timestamp of when the stream was created"
    )
    model: str = Field(..., description="Name of the model used for generation")
    choices: List[Dict[str, Any]] = Field(
        ...,
        description="List of generated responses"
    )
    usage: Optional[Dict[str, int]] = Field(
        None,
        description="Token usage statistics"
    )


# Add missing import for default_factory
from datetime import datetime
