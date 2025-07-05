import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_admin_user():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
        
        if admin:
            print(f"Admin user {settings.FIRST_SUPERUSER} already exists")
            return
        
        # Create admin user
        admin_user = User(
            email=settings.FIRST_SUPERUSER,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Admin User",
            is_superuser=True,
            is_active=True,
        )
        
        db.add(admin_user)
        db.commit()
        print(f"Created admin user {settings.FIRST_SUPERUSER}")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create tables if they don't exist
    from app.db.base import Base
    from app.db.session import engine
    
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create admin user
    print("Creating admin user...")
    create_admin_user()
    
    print("Database initialization complete!")
