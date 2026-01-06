"""
Request Model
Database schema for Requests data
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId

class Request(Document):
    """
    Request model for handling various employee requests (e.g., Update Bank Details)
    """
    employee_id: str
    employee_name: str
    request_type: str  # 'bank_details_update', 'profile_update', 'other'
    reason: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    admin_comment: Optional[str] = None
    
    approver_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "requests"
        indexes = [
            "employee_id",
            "approver_id",
            "status",
            "request_type",
            "created_at"
        ]

class RequestCreate(BaseModel):
    request_type: str
    reason: str
    approver_id: Optional[str] = None

class RequestUpdate(BaseModel):
    status: str
    admin_comment: Optional[str] = None
