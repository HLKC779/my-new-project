from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from .. import schemas, models, crud
from ..database import get_db
from ..auth.auth import (
    get_password_hash,
    create_access_token,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..config import settings

router = APIRouter()

@router.post("/register", response_model=schemas.User)
def register_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user"""
    # Check if user already exists
    db_user = crud.user.get_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user_in.hashed_password = get_password_hash(user_in.password)
    return crud.user.create(db, obj_in=user_in)

@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Login user and return access token"""
    # Authenticate user
    user = crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(crud.user.get_current_active_user)
) -> Any:
    """Get current user information"""
    return current_user
