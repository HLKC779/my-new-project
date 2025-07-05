import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path

from .. import models, schemas, crud
from ..services.rag_service import RAGService
from ..database import get_db
from ..config import settings

router = APIRouter()
rag_service = RAGService()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: models.User = Depends(crud.user.get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and process documents for the RAG system"""
    saved_files = []
    
    for file in files:
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        saved_files.append(file_path)
    
    try:
        # Process the uploaded documents
        documents = rag_service.load_documents(saved_files)
        rag_service.create_vector_store(documents, recreate=True)
        
        return {
            "status": "success",
            "message": f"Successfully processed {len(documents)} document chunks from {len(saved_files)} files",
            "files": saved_files
        }
    except Exception as e:
        # Clean up saved files if processing fails
        for file_path in saved_files:
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing files: {str(e)}"
        )

@router.post("/query")
async def query_rag(
    query: schemas.RAGQuery,
    current_user: models.User = Depends(crud.user.get_current_active_user)
):
    """Query the RAG system"""
    try:
        result = rag_service.query(query.question)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

@router.get("/documents")
async def list_documents(
    current_user: models.User = Depends(crud.user.get_current_active_user)
):
    """List all documents in the vector store"""
    try:
        if not rag_service.vector_store:
            return {"documents": []}
            
        collection = rag_service.vector_store._client.get_collection("langchain")
        documents = collection.get()
        
        # Get unique document sources
        unique_sources = set()
        for metadata in documents["metadatas"]:
            if "source" in metadata:
                unique_sources.add(metadata["source"])
        
        return {
            "documents": list(unique_sources),
            "total_chunks": len(documents["ids"])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )
