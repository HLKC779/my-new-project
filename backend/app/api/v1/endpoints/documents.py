import logging
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.vector_store import vector_store_manager
from app.models.document import Document as DocumentModel, DocumentChunk
from app.models.user import User
from app.schemas.document import (
    Document as DocumentSchema,
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentChunk as DocumentChunkSchema,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_upload_dir() -> Path:
    """Get the upload directory, creating it if it doesn't exist."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@router.post("/upload/", response_model=DocumentSchema, status_code=status.HTTP_201_CREATED)
async def upload_document(
    *,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a document to the system.
    
    The document will be processed, split into chunks, and indexed for search.
    """
    # Validate file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_EXTENSIONS)}",
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = get_upload_dir()
    
    # Generate a unique filename
    file_hash = await calculate_file_hash_async(file)
    filename = f"{file_hash}{file_extension}"
    file_path = upload_dir / filename
    
    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error saving file",
        )
    
    # Process the document
    try:
        rag_service = RAGService()
        document, chunks = rag_service.process_document(
            file_path=file_path,
            user_id=current_user.id,
            db=db,
            chunk_size=settings.DOCUMENT_CHUNK_SIZE,
            chunk_overlap=settings.DOCUMENT_CHUNK_OVERLAP,
        )
        
        # Convert to Pydantic model for response
        return DocumentSchema.from_orm(document)
        
    except Exception as e:
        # Clean up the file if processing fails
        if file_path.exists():
            file_path.unlink()
            
        logger.error(f"Error processing document {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}",
        )


@router.get("/", response_model=List[DocumentSchema])
async def list_documents(
    *, 
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all documents for the current user.
    """
    documents = (
        db.query(DocumentModel)
        .filter(DocumentModel.user_id == current_user.id)
        .order_by(DocumentModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return documents


@router.get("/{document_id}", response_model=DocumentSchema)
async def get_document(
    *,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a document by ID.
    """
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return document


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkSchema])
async def get_document_chunks(
    *,
    document_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get chunks for a specific document.
    """
    # Verify document exists and belongs to user
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Get chunks
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return chunks


@router.get("/{document_id}/download")
async def download_document(
    *,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download a document file.
    """
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not document or not document.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or file is missing",
        )
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )
    
    return FileResponse(
        path=file_path,
        filename=document.file_name,
        media_type="application/octet-stream",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    *,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a document and all its chunks.
    """
    # Get the document
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Delete using the RAG service
    rag_service = RAGService()
    success = rag_service.delete_document(document_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document",
        )
    
    # Clean up the file if it exists
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.unlink(document.file_path)
        except Exception as e:
            logger.error(f"Error deleting file {document.file_path}: {str(e)}")
    
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )


@router.put("/{document_id}", response_model=DocumentSchema)
async def update_document(
    *,
    document_id: int,
    document_in: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update document metadata.
    """
    # Get the document
    document = (
        db.query(DocumentModel)
        .filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Update fields
    update_data = document_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    document.updated_at = datetime.utcnow()
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document


async def calculate_file_hash_async(file: UploadFile, chunk_size: int = 65536) -> str:
    """
    Calculate the SHA-256 hash of an uploaded file asynchronously.
    """
    import hashlib
    
    sha256_hash = hashlib.sha256()
    
    # Reset file pointer to the beginning
    await file.seek(0)
    
    # Read and update hash in chunks
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        sha256_hash.update(chunk)
    
    # Reset file pointer again for further processing
    await file.seek(0)
    
    return sha256_hash.hexdigest()


# Add datetime import at the top of the file
from datetime import datetime
