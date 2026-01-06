"""
Leave Model
Database schema for leave management
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId
from enum import Enum


class LeaveType(str, Enum):
    """Types of leave"""
    CASUAL = "casual"
    SICK = "sick"
    ANNUAL = "annual"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    UNPAID = "unpaid"
    COMPENSATORY = "compensatory"


class LeaveStatus(str, Enum):
    """Leave application status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveApproval(BaseModel):
    """Leave approval/rejection record"""
    approver_id: str
    approver_name: str
    status: LeaveStatus
    comments: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Leave(Document):
    """Leave application document"""
    
    # Employee Reference
    employee_id: str = Field(..., index=True)
    employee_name: str
    department: str
    reporting_manager: Optional[str] = None
    
    # Leave Details
    leave_type: LeaveType
    start_date: datetime = Field(..., index=True)
    end_date: datetime = Field(..., index=True)
    total_days: float
    is_half_day: bool = False
    half_day_session: Optional[str] = None  # morning, afternoon
    
    # Reason
    reason: str
    attachments: List[str] = []  # URLs to uploaded documents
    
    # Status
    status: LeaveStatus = LeaveStatus.PENDING
    
    # Approval Workflow
    approvals: List[LeaveApproval] = []
    current_approver: Optional[str] = None
    
    # HR Comments
    hr_comments: Optional[str] = None
    
    # Metadata
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "leaves"
        indexes = [
            "employee_id",
            "status",
            "leave_type",
            ("start_date", "end_date"),
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": "EMP001",
                "employee_name": "John Doe",
                "department": "Engineering",
                "leave_type": "casual",
                "start_date": "2026-01-10",
                "end_date": "2026-01-12",
                "total_days": 3.0,
                "reason": "Personal work",
                "status": "pending"
            }
        }


class LeaveCreate(BaseModel):
    """Schema for creating leave application"""
    employee_id: str
    leave_type: LeaveType
    start_date: datetime
    end_date: datetime
    is_half_day: bool = False
    half_day_session: Optional[str] = None
    reason: str
    attachments: List[str] = []


class LeaveUpdate(BaseModel):
    """Schema for updating leave application"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[LeaveStatus] = None


class LeaveApprovalRequest(BaseModel):
    """Schema for approving/rejecting leave"""
    leave_id: str
    approver_id: Optional[str] = None
    status: LeaveStatus
    comments: Optional[str] = None


class LeaveResponse(BaseModel):
    """Schema for leave response slice"""
    id: PydanticObjectId
    employee_id: str
    employee_name: str
    leave_type: LeaveType
    start_date: datetime
    end_date: datetime
    total_days: float
    reason: str
    status: LeaveStatus
    applied_at: datetime
    
    class Config:
        from_attributes = True


class LeaveBalance(BaseModel):
    """Leave balance for an employee"""
    employee_id: str
    casual_leave: float
    sick_leave: float
    annual_leave: float
    total_available: float
    total_used: float


class LeaveListResponse(BaseModel):
    """Schema for list of leaves"""
    total: int
    leaves: List[LeaveResponse]
