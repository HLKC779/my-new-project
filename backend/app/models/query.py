from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

class QueryStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Query(Base):
    """
    Model for storing user queries and their results.
    """
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    
    # Query metadata
    status = Column(
        Enum(QueryStatus, name="query_status"),
        default=QueryStatus.PENDING,
        nullable=False
    )
    error_message = Column(Text, nullable=True)
    
    # Model and settings used
    model_name = Column(String(100), nullable=True)
    temperature = Column(Integer, default=70, nullable=True)  # 0-100 scale
    max_tokens = Column(Integer, nullable=True)
    
    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="queries")
    
    # Sources and context used for the response
    sources = relationship("QuerySource", back_populates="query", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Query(id={self.id}, status='{self.status}', query_text='{self.query_text[:50]}...')>"


class QuerySource(Base):
    """
    Model for tracking which document chunks were used to answer a query.
    """
    __tablename__ = "query_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    document_chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    
    # Relevance score (0-1) indicating how relevant this chunk was to the query
    relevance_score = Column(Integer, nullable=True)
    
    # Snippet of the source text used
    content_snippet = Column(Text, nullable=True)
    
    # Position/order of this source in the response
    position = Column(Integer, nullable=False, default=0)
    
    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    query = relationship("Query", back_populates="sources")
    document_chunk = relationship("DocumentChunk", lazy="joined")
    
    def __repr__(self):
        return f"<QuerySource(query_id={self.query_id}, document_chunk_id={self.document_chunk_id})>"


class Conversation(Base):
    """
    Model for grouping related queries into conversations.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    
    # Conversation metadata
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="conversations")
    queries = relationship("Query", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"


# Add relationships to the User model
from app.models.user import User
User.documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
User.queries = relationship("Query", back_populates="user", cascade="all, delete-orphan")
User.conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

# Add relationship to the Query model
Query.conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
Query.conversation = relationship("Conversation", back_populates="queries")
