from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl

class UserRole(str, Enum):
    """User roles in the system."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    ANALYST = "analyst"
    GUEST = "guest"

class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class UserPreferences(BaseModel):
    """User preferences and settings."""
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    email_notifications: bool = True
    push_notifications: bool = True
    ui_settings: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)

class UserBase(BaseModel):
    """Base user model with essential fields."""
    email: EmailStr = Field(..., description="User's email address (must be unique)")
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        description="Unique username (alphanumeric with underscores)"
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="User's full name"
    )
    avatar_url: Optional[HttpUrl] = Field(
        None,
        description="URL to the user's profile picture"
    )
    bio: Optional[str] = Field(
        None, 
        max_length=500,
        description="Short bio or description"
    )
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if v is not None and not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores allowed)')
        return v.lower() if v else v

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 characters, must include uppercase, lowercase, number, and special character)"
    )
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(not c.isalnum() for c in v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        description="New username"
    )
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = Field(None, max_length=500)
    date_of_birth: Optional[date] = Field(
        None,
        description="User's date of birth (YYYY-MM-DD)"
    )
    phone_number: Optional[str] = Field(
        None,
        pattern=r'^\+?[1-9]\d{1,14}$',
        description="Phone number in E.164 format"
    )
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[HttpUrl] = None
    preferences: Optional[UserPreferences] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "bio": "Software developer and AI enthusiast",
                "location": "San Francisco, CA",
                "website": "https://example.com"
            }
        }

class UserInDBBase(UserBase):
    """Base user model for database operations."""
    id: int = Field(..., description="Unique user ID")
    role: UserRole = Field(UserRole.USER, description="User's role in the system")
    status: UserStatus = Field(UserStatus.PENDING_VERIFICATION, description="Account status")
    is_active: bool = Field(True, description="Whether the user account is active")
    is_verified: bool = Field(False, description="Whether the user's email is verified")
    is_superuser: bool = Field(False, description="Whether the user has superuser privileges")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    date_joined: datetime = Field(..., description="When the user registered")
    updated_at: Optional[datetime] = Field(None, description="When the user was last updated")
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
        description="User preferences and settings"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the user"
    )
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }

class User(UserInDBBase):
    """User model for API responses (excludes sensitive data)."""
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "role": "user",
                "status": "active",
                "is_active": True,
                "is_verified": True,
                "date_joined": "2023-01-01T00:00:00Z",
                "preferences": {
                    "theme": "light",
                    "language": "en",
                    "timezone": "UTC"
                }
            }
        }

class UserInDB(UserInDBBase):
    """User model for database operations (includes sensitive data)."""
    hashed_password: str = Field(..., description="Hashed password")
    email_verification_token: Optional[str] = Field(
        None,
        description="Token for email verification"
    )
    password_reset_token: Optional[str] = Field(
        None,
        description="Token for password reset"
    )
    password_reset_expires: Optional[datetime] = Field(
        None,
        description="When the password reset token expires"
    )
    failed_login_attempts: int = Field(
        0,
        description="Number of failed login attempts"
    )
    last_failed_login: Optional[datetime] = Field(
        None,
        description="Timestamp of the last failed login attempt"
    )
    
    class Config:
        from_attributes = True
