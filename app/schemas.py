from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LinkBase(BaseModel):
    original_url: str

class LinkStats(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    last_accessed_at: Optional[datetime]
    clicks: int
    expires_at: Optional[datetime]
    is_active: bool

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = Field(
        None, 
        min_length=4, 
        max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    expires_at: Optional[datetime] = Field(
        None,
        example="2023-12-31T23:59:59",
        description="Дата истечения в формате ISO 8601"
    )

class LinkSearchResult(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]

class LinkUpdate(BaseModel):
    original_url: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class Link(LinkBase):
    id: int
    short_code: str
    created_at: datetime
    clicks: int
    is_active: bool
    user_id: Optional[int]
    
    class Config:
        orm_mode = True