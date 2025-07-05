from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RAGQuery(BaseModel):
    question: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

class DocumentUploadResponse(BaseModel):
    status: str
    message: str
    files: List[str]

class DocumentListResponse(BaseModel):
    documents: List[str]
    total_chunks: int
