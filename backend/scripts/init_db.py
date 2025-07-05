#!/usr/bin/env python3
"""
Database initialization script.
This script creates the database tables and optionally populates them with sample data.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.base import Base, engine, init_db
from app.db.session import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.document import Document
from app.core.security import get_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_user(db: SessionLocal) -> User:
    """Create a sample user."""
    logger.info("Creating sample user...")
    user = db.query(User).filter(User.email == "user@example.com").first()
    
    if not user:
        user = User(
            email="user@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Sample User",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created sample user with ID: {user.id}")
    else:
        logger.info("Sample user already exists")
    
    return user

def create_sample_conversation(db: SessionLocal, user: User) -> Conversation:
    """Create a sample conversation."""
    logger.info("Creating sample conversation...")
    conversation = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .first()
    )
    
    if not conversation:
        conversation = Conversation(
            user_id=user.id,
            title="Sample Conversation",
            metadata_={"source": "sample_data"}
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"Created sample conversation with ID: {conversation.id}")
        
        # Add sample messages
        messages = [
            {
                "role": MessageRole.USER,
                "content": "Hello, how are you?",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "role": MessageRole.ASSISTANT,
                "content": "I'm doing well, thank you for asking! How can I assist you today?",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "role": MessageRole.USER,
                "content": "Tell me about the RAG system.",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "role": MessageRole.ASSISTANT,
                "content": "The RAG (Retrieval-Augmented Generation) system combines retrieval-based and generation-based approaches to provide accurate and contextually relevant responses by retrieving information from a knowledge base and generating responses based on that information.",
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        for msg in messages:
            message = Message(
                conversation_id=conversation.id,
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"]
            )
            db.add(message)
        
        db.commit()
        logger.info(f"Added {len(messages)} sample messages to the conversation")
    else:
        logger.info("Sample conversation already exists")
    
    return conversation

def create_sample_document(db: SessionLocal, user: User) -> Document:
    """Create a sample document."""
    logger.info("Creating sample document...")
    document = (
        db.query(Document)
        .filter(Document.owner_id == user.id)
        .order_by(Document.created_at.desc())
        .first()
    )
    
    if not document:
        document = Document(
            owner_id=user.id,
            filename="sample_document.txt",
            content_type="text/plain",
            file_path="/uploads/sample_document.txt",
            file_size=1024,
            metadata_={
                "title": "Sample Document",
                "description": "This is a sample document for testing purposes.",
                "source": "sample_data"
            }
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Created sample document with ID: {document.id}")
    else:
        logger.info("Sample document already exists")
    
    return document

def main() -> None:
    """Initialize the database and create sample data."""
    logger.info("Initializing database...")
    
    # Create all tables
    init_db()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Create sample data
        user = create_sample_user(db)
        create_sample_conversation(db, user)
        create_sample_document(db, user)
        
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
