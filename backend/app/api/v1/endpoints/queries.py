import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.config import settings
from app.models.document import Document
from app.models.query import Query as QueryModel, QuerySource, QueryStatus
from app.models.user import User
from app.schemas.query import (
    Query as QuerySchema,
    QueryCreate,
    QueryResponse,
    QuerySource as QuerySourceSchema,
    Conversation,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for submitting a query."""
    
    question: str = Field(..., description="The question to ask the RAG system")
    document_ids: Optional[List[int]] = Field(
        None,
        description="Optional list of document IDs to restrict the search to"
    )
    conversation_id: Optional[int] = Field(
        None,
        description="Optional conversation ID to continue a previous conversation"
    )
    max_results: Optional[int] = Field(
        5,
        description="Maximum number of results to return",
        ge=1,
        le=20
    )
    temperature: Optional[float] = Field(
        0.7,
        description="Sampling temperature for the LLM",
        ge=0.0,
        le=2.0
    )


@router.post("/", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_rag(
    *,
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Query the RAG system with a question.
    
    This endpoint processes a natural language question, retrieves relevant context,
    and generates an answer using the configured language model.
    """
    # Verify document access if document_ids are provided
    if query_data.document_ids:
        accessible_docs = (
            db.query(Document.id)
            .filter(
                Document.id.in_(query_data.document_ids),
                Document.user_id == current_user.id,
            )
            .all()
        )
        
        accessible_doc_ids = {doc.id for doc in accessible_docs}
        invalid_docs = set(query_data.document_ids) - accessible_doc_ids
        
        if invalid_docs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to document(s): {', '.join(map(str, invalid_docs))}",
            )
    
    # Initialize RAG service
    rag_service = RAGService()
    
    try:
        # Process the query
        result = rag_service.query(
            question=query_data.question,
            user_id=current_user.id,
            db=db,
            conversation_id=query_data.conversation_id,
            max_results=query_data.max_results,
            temperature=query_data.temperature,
            document_ids=query_data.document_ids,
        )
        
        # Format the response
        return QueryResponse(
            query_id=result["query_id"],
            answer=result["answer"],
            sources=[
                QuerySourceSchema(
                    content=src["content"],
                    metadata=src["metadata"],
                )
                for src in result.get("sources", [])
            ],
            conversation_id=query_data.conversation_id,
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}",
        )


@router.get("/{query_id}", response_model=QuerySchema)
async def get_query(
    *,
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get details of a specific query by ID.
    """
    query = (
        db.query(QueryModel)
        .filter(
            QueryModel.id == query_id,
            QueryModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )
    
    return query


@router.get("/conversations/", response_model=List[Conversation])
async def list_conversations(
    *,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all conversations for the current user.
    
    A conversation is a collection of related queries.
    """
    # Get unique conversation IDs with their latest query
    conversations = (
        db.query(
            QueryModel.conversation_id,
            QueryModel.created_at.label("last_activity"),
        )
        .filter(QueryModel.user_id == current_user.id)
        .filter(QueryModel.conversation_id.isnot(None))
        .group_by(QueryModel.conversation_id)
        .order_by(QueryModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Get the first query for each conversation to use as a title
    conversation_data = []
    for conv in conversations:
        first_query = (
            db.query(QueryModel)
            .filter(
                QueryModel.conversation_id == conv.conversation_id,
                QueryModel.user_id == current_user.id,
            )
            .order_by(QueryModel.created_at.asc())
            .first()
        )
        
        if first_query:
            conversation_data.append({
                "id": conv.conversation_id,
                "title": first_query.query_text[:100] + ("..." if len(first_query.query_text) > 100 else ""),
                "created_at": first_query.created_at,
                "updated_at": conv.last_activity,
                "query_count": (
                    db.query(QueryModel)
                    .filter(QueryModel.conversation_id == conv.conversation_id)
                    .count()
                ),
            })
    
    return conversation_data


@router.get("/conversations/{conversation_id}", response_model=List[QuerySchema])
async def get_conversation(
    *,
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all queries in a specific conversation.
    """
    # Verify the conversation exists and belongs to the user
    conversation_exists = (
        db.query(QueryModel)
        .filter(
            QueryModel.conversation_id == conversation_id,
            QueryModel.user_id == current_user.id,
        )
        .first()
    )
    
    if not conversation_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    # Get all queries in the conversation
    queries = (
        db.query(QueryModel)
        .filter(
            QueryModel.conversation_id == conversation_id,
            QueryModel.user_id == current_user.id,
        )
        .order_by(QueryModel.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return queries


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    *,
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a conversation and all its associated queries.
    """
    # Delete all queries in the conversation
    result = (
        db.query(QueryModel)
        .filter(
            QueryModel.conversation_id == conversation_id,
            QueryModel.user_id == current_user.id,
        )
        .delete(synchronize_session=False)
    )
    
    if result == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching conversation found",
        )
    
    db.commit()
    
    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )


@router.get("/recent/", response_model=List[QuerySchema])
async def get_recent_queries(
    *,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the most recent queries for the current user.
    """
    queries = (
        db.query(QueryModel)
        .filter(QueryModel.user_id == current_user.id)
        .order_by(QueryModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return queries
