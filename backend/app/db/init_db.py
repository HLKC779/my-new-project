import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

# Make sure all SQL Alchemy models are imported before initializing DB
# Otherwise, SQL Alchemy might fail to initialize relationships properly
from app.models.base import Base  # noqa

def init_db(db: Session) -> None:
    ""
    Initialize the database with initial data.
    
    This function creates the database tables (if they don't exist)
    and creates an initial superuser if no users exist.
    ""
    # Create all database tables
    Base.metadata.create_all(bind=db.get_bind())
    
    # Create initial superuser if no users exist
    user = db.query(User).first()
    if not user:
        logger.info("Creating initial superuser")
        user_in = {
            "email": settings.FIRST_SUPERUSER,
            "hashed_password": get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            "full_name": "Initial Super User",
            "is_superuser": True,
            "is_active": True,
        }
        db_obj = User(**user_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info(f"Created initial superuser: {user_in['email']}")
    
    logger.info("Database initialization complete")


def recreate_db(db: Session) -> None:
    ""
    Recreate the database by dropping all tables and recreating them.
    
    WARNING: This will delete all data in the database!
    ""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=db.get_bind())
    logger.info("All tables dropped")
    
    # Recreate all tables
    init_db(db)
