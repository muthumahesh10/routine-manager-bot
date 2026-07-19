from pydantic import BaseModel
from typing import Optional
from datetime import time

# --- USER SCHEMAS ---
class UserCreate(BaseModel):
    name: str
    phone_number: str
    password: str
    role: str = "user"

class UserResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    role: str

    class Config:
        from_attributes = True

# --- AUTH SCHEMAS ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- TASK SCHEMAS ---
class TaskTemplateCreate(BaseModel):
    task_name: str
    start_time: time
    end_time: Optional[time] = None
    frequency: str

class TaskTemplateResponse(BaseModel):
    id: int
    task_name: str
    start_time: time
    end_time: Optional[time]
    frequency: str

    class Config:
        from_attributes = True