"""
Attendance Model
Database schema for attendance records
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId
from enum import Enum


class AttendanceType(str, Enum):
    """Attendance capture type"""
    MANUAL = "manual"
    FACE = "face"
    RFID = "rfid"
    FINGERPRINT = "fingerprint"


class AttendanceStatus(str, Enum):
    """Attendance status"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"
    WORK_FROM_HOME = "work_from_home"


class Location(BaseModel):
    """Geolocation data"""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    address: Optional[str] = None


class Attendance(Document):
    """Attendance record document"""
    
    # Employee Reference
    employee_id: str = Field(..., index=True)
    employee_name: str
    department: str
    
    # Date
    date: datetime = Field(..., index=True)
    day_of_week: str
    
    # Check-in Details
    check_in_time: Optional[datetime] = None
    check_in_type: Optional[AttendanceType] = None
    check_in_location: Optional[Location] = None
    check_in_device: Optional[str] = None
    check_in_ip: Optional[str] = None
    
    # Check-out Details
    check_out_time: Optional[datetime] = None
    check_out_type: Optional[AttendanceType] = None
    check_out_location: Optional[Location] = None
    check_out_device: Optional[str] = None
    check_out_ip: Optional[str] = None
    
    # Calculated Fields
    total_hours: Optional[float] = None
    overtime_hours: Optional[float] = None
    break_duration: Optional[float] = None
    
    # Status
    status: AttendanceStatus = AttendanceStatus.ABSENT
    is_late: bool = False
    is_early_departure: bool = False
    
    # Validation
    is_validated: bool = False
    validated_by: Optional[str] = None  # Employee ID of validator
    validated_at: Optional[datetime] = None
    
    # Notes
    remarks: Optional[str] = None
    auto_checkout: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "attendance"
        indexes = [
            "employee_id",
            "date",
            ("employee_id", "date"),  # Compound index
            "status",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": "EMP001",
                "employee_name": "John Doe",
                "department": "Engineering",
                "date": "2026-01-03",
                "check_in_time": "2026-01-03T09:00:00",
                "check_in_type": "manual",
                "status": "present"
            }
        }


class AttendanceCheckIn(BaseModel):
    """Schema for check-in request"""
    employee_id: str
    check_in_type: AttendanceType
    location: Optional[Location] = None
    device_info: Optional[str] = None
    remarks: Optional[str] = None


class AttendanceCheckOut(BaseModel):
    """Schema for check-out request"""
    employee_id: str
    check_out_type: AttendanceType
    location: Optional[Location] = None
    device_info: Optional[str] = None
    remarks: Optional[str] = None


class AttendanceResponse(BaseModel):
    """Schema for attendance response"""
    id: PydanticObjectId
    employee_id: str
    employee_name: str
    date: datetime
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    total_hours: Optional[float]
    status: AttendanceStatus
    is_late: bool
    
    class Config:
        from_attributes = True


class AttendanceStats(BaseModel):
    """Attendance statistics"""
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    half_days: int
    leave_days: int
    wfh_days: int
    attendance_percentage: float
    average_hours: float


class AttendanceListResponse(BaseModel):
    """Schema for attendance list response"""
    total: int
    records: List[AttendanceResponse]


class TodayAttendanceResponse(BaseModel):
    """Schema for today's attendance status"""
    status: str
    message: Optional[str] = None
    attendance: Optional[AttendanceResponse] = None
    checked_in: bool = False
    checked_out: bool = False
