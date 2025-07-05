from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base

class Document(Base):
    """
    Model for storing document metadata in the database.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)  # size in bytes
    
    # Document processing status
    status = Column(
        String(20),
        default="uploaded",
        nullable=False,
        comment="Document processing status: uploaded, processing, processed, error"
    )
    
    # Document metadata
    page_count = Column(Integer, nullable=True)
    language = Column(String(10), default="en")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', status='{self.status}')>"


class DocumentChunk(Base):
    """
    Model for storing chunks of text extracted from documents.
    Each chunk is associated with a document and can be used for vector search.
    """
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False, comment="Index of the chunk in the document")
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True, comment="SHA-256 hash of the content")
    
    # Vector embedding metadata
    embedding_model = Column(String(100), nullable=True, comment="Model used to generate the embedding")
    embedding_vector_id = Column(String(100), nullable=True, index=True, comment="ID of the vector in the vector store")
    
    # Metadata for retrieval
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Composite index for faster lookups
    __table_args__ = (
        # Ensure we don't have duplicate chunks for the same document
        # {'sqlite_autoincrement': True}
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
