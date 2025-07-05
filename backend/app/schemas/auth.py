from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator, HttpUrl
from .user import User, UserCreate, UserRole


class Token(BaseModel):
    """Authentication token schema."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(
        timedelta(days=1).total_seconds(),
        description="Time in seconds until the token expires"
    )
    refresh_token: Optional[str] = Field(None, description="Refresh token")


class TokenData(BaseModel):
    """Data stored in the JWT token."""
    user_id: int
    email: Optional[str] = None
    username: Optional[str] = None
    scopes: List[str] = []
    is_superuser: bool = False
    exp: Optional[int] = None
    iat: Optional[int] = None


class UserRegister(UserCreate):
    """Schema for user registration."""
    terms_accepted: bool = Field(
        ...,
        description="Must be true to accept terms and conditions"
    )
    newsletter_opt_in: bool = Field(
        False,
        description="Whether to subscribe to the newsletter"
    )
    
    @validator('terms_accepted')
    def must_accept_terms(cls, v):
        if not v:
            raise ValueError('You must accept the terms and conditions')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    remember_me: bool = Field(False, description="Whether to remember the user")


class PasswordResetRequest(BaseModel):
    """Schema for requesting a password reset."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for confirming a password reset."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile information."""
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[HttpUrl] = None
    avatar_url: Optional[HttpUrl] = None


class UserPasswordChange(BaseModel):
    """Schema for changing user password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class UserListResponse(BaseModel):
    """Response schema for listing users with pagination."""
    users: List[User]
    total: int
    page: int
    limit: int
    has_more: bool


class OAuth2Token(BaseModel):
    """OAuth2 token response schema."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class OAuth2TokenData(BaseModel):
    """OAuth2 token data schema."""
    client_id: str
    client_secret: str
    redirect_uri: str
    code: str
    grant_type: str = "authorization_code"


class OAuth2ProviderSettings(BaseModel):
    """OAuth2 provider settings schema."""
    client_id: str
    client_secret: str
    authorize_url: str
    access_token_url: str
    userinfo_url: str
    scopes: List[str] = ["openid", "profile", "email"]


class OAuth2State(BaseModel):
    """OAuth2 state parameter schema."""
    redirect_uri: str
    provider: str
    next_url: Optional[str] = None
    state: Optional[str] = None
    code_verifier: Optional[str] = None


class UserSession(BaseModel):
    """User session schema."""
    user_id: int
    session_id: str
    ip_address: str
    user_agent: str
    expires_at: datetime
    last_activity: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = {}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Permission(BaseModel):
    """Permission schema."""
    name: str
    description: str
    resource: str
    action: str
    
    class Config:
        orm_mode = True


class Role(BaseModel):
    """Role schema."""
    name: str
    description: str
    permissions: List[Permission] = []
    
    class Config:
        orm_mode = True


class UserRoleUpdate(BaseModel):
    """Schema for updating user roles."""
    role: UserRole
    
    class Config:
        schema_extra = {
            "example": {
                "role": "admin"
            }
        }
