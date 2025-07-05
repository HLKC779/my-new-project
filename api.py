from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from rag_system import RAGSystem

app = FastAPI(title="RAG System API",
             description="API for Data Engineering and AI Research RAG System",
             version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag_system = None

class DocumentRequest(BaseModel):
    file_paths: List[str]
    recreate_index: bool = False

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

@app.on_event("startup")
async def startup_event():
    global rag_system
    rag_system = RAGSystem()
    print("RAG System initialized")

@app.post("/load_documents")
async def load_documents(request: DocumentRequest):
    try:
        documents = rag_system.load_documents(request.file_paths)
        rag_system.create_vector_store(documents, recreate=request.recreate_index)
        return {"status": "success", "message": f"Loaded {len(documents)} document chunks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    if not rag_system.qa_chain:
        raise HTTPException(status_code=400, detail="Please load documents first")
    
    try:
        result = rag_system.query(request.question)
        return {
            "answer": result["result"],
            "sources": [
                {
                    "source": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", "N/A"),
                    "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                }
                for doc in result["source_documents"]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
