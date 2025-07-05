from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class QueryStatus(str, Enum):
    """Status of a query."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QueryBase(BaseModel):
    """Base schema for query operations."""
    query_text: str = Field(..., description="The text of the query")
    conversation_id: Optional[int] = Field(
        None, 
        description="ID of the conversation this query belongs to"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the query"
    )


class QueryCreate(QueryBase):
    """Schema for creating a new query."""
    document_ids: Optional[List[int]] = Field(
        None,
        description="List of document IDs to restrict the query to"
    )


class QueryUpdate(BaseModel):
    """Schema for updating an existing query."""
    status: Optional[QueryStatus] = None
    response_text: Optional[str] = Field(
        None,
        description="The response text from the RAG system"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the query failed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata to update"
    )


class QueryInDBBase(QueryBase):
    """Base schema for query in database."""
    id: int
    user_id: int
    status: QueryStatus
    model_name: Optional[str] = Field(
        None,
        description="Name of the model used to generate the response"
    )
    response_text: Optional[str] = Field(
        None,
        description="The response text from the RAG system"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the query failed"
    )
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Query(QueryInDBBase):
    """Schema for returning a query."""
    pass


class QuerySourceBase(BaseModel):
    """Base schema for query sources."""
    document_chunk_id: Optional[int] = Field(
        None,
        description="ID of the document chunk used as a source"
    )
    relevance_score: Optional[float] = Field(
        None,
        description="Relevance score of the source (0-1)",
        ge=0.0,
        le=1.0
    )
    content_snippet: Optional[str] = Field(
        None,
        description="Snippet of the source content"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the source"
    )


class QuerySourceCreate(QuerySourceBase):
    """Schema for creating a new query source."""
    query_id: int


class QuerySourceInDBBase(QuerySourceBase):
    """Base schema for query source in database."""
    id: int
    query_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class QuerySource(QuerySourceInDBBase):
    """Schema for returning a query source."""
    pass


class QueryWithSources(Query):
    """Schema for a query with its sources."""
    sources: List[QuerySource] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Response schema for a query result."""
    query_id: int
    answer: str
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of sources used to generate the answer"
    )
    conversation_id: Optional[int] = Field(
        None,
        description="ID of the conversation this query belongs to"
    )


class ConversationBase(BaseModel):
    """Base schema for a conversation."""
    title: Optional[str] = Field(
        None,
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
    """Base schema for a conversation in database."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Conversation(ConversationInDBBase):
    """Schema for returning a conversation."""
    query_count: int = Field(
        0,
        description="Number of queries in the conversation"
    )
    last_activity: Optional[datetime] = Field(
        None,
        description="Timestamp of the last activity in the conversation"
    )


class ConversationWithQueries(Conversation):
    """Schema for a conversation with its queries."""
    queries: List[Query] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """Response schema for a query with additional context."""
    query_id: int
    answer: str
    sources: List[Dict[str, Any]]
    conversation_id: Optional[int] = None
    model_name: Optional[str] = None
    processing_time: Optional[float] = Field(
        None,
        description="Time taken to process the query in seconds"
    )
    tokens_used: Optional[int] = Field(
        None,
        description="Number of tokens used to generate the response"
    )
