from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "user"
    phone: str = ""


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # if provided, update password


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    phone: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
