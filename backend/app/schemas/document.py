from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base schema for document operations."""
    title: str = Field(..., description="Title of the document")
    description: Optional[str] = Field(None, description="Description of the document")
    file_name: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    page_count: Optional[int] = Field(None, description="Number of pages in the document")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata about the document"
    )


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document."""
    title: Optional[str] = Field(None, description="New title for the document")
    description: Optional[str] = Field(None, description="New description for the document")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata to update"
    )


class DocumentInDBBase(DocumentBase):
    """Base schema for document in database."""
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Document(DocumentInDBBase):
    """Schema for returning a document."""
    pass


class DocumentChunkBase(BaseModel):
    """Base schema for document chunks."""
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    content: str = Field(..., description="Text content of the chunk")
    page_number: Optional[int] = Field(None, description="Page number in the original document")
    section_title: Optional[str] = Field(None, description="Title of the section")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata about the chunk"
    )


class DocumentChunkCreate(DocumentChunkBase):
    """Schema for creating a new document chunk."""
    document_id: int


class DocumentChunkInDBBase(DocumentChunkBase):
    """Base schema for document chunk in database."""
    id: int
    document_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class DocumentChunk(DocumentChunkInDBBase):
    """Schema for returning a document chunk."""
    pass


class DocumentWithChunks(Document):
    """Schema for a document with its chunks."""
    chunks: List[DocumentChunk] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""
    document: Document
    chunks_processed: int
    status: str


class DocumentDeleteResponse(BaseModel):
    """Response schema for document deletion."""
    id: int
    status: str
    message: str


# Add missing imports
from typing import Any
