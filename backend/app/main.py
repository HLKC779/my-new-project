from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import logging
from pathlib import Path
from typing import Dict, Any

# Import models to ensure they are registered with SQLAlchemy
from app.models import Base, User, Document, Query, Conversation, Message
from app.database import engine, get_db
from app.routers import auth, rag, users
from app.api import health as health_router
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    # Create uploads directory if it doesn't exist
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Created uploads directory at: {os.path.abspath(UPLOAD_DIR)}")
    
    logger.info("Application startup complete")
    yield
    # Shutdown: Clean up resources if needed
    logger.info("Application shutdown")

app = FastAPI(
    title="RAG System API",
    description="A RAG (Retrieval-Augmented Generation) system for data engineering and AI research",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the uploads directory
UPLOAD_DIR = "uploads"
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(
    health_router.router,
    prefix="/api",
    tags=["Health"]
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["Users"]
)

app.include_router(
    rag.router,
    prefix="/api/v1/rag",
    tags=["RAG System"]
)

@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "debug": settings.DEBUG,
        "environment": settings.ENVIRONMENT
    }

def start():
    """Launched with 'poetry run start' at root level"""
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=settings.WORKERS
    )

if __name__ == "__main__":
    start()
