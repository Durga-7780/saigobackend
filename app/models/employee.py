"""
Employee Model
Database schema for employee data
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from beanie import Document, PydanticObjectId


class Address(BaseModel):
    """Employee address"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "India"


class EmergencyContact(BaseModel):
    """Emergency contact information"""
    name: str
    relationship: str
    phone: str
    email: Optional[EmailStr] = None


class BankDetails(BaseModel):
    """Employee bank and tax details"""
    account_number: str = ""
    bank_name: str = ""
    ifsc_code: str = ""
    pan_number: str = ""
    uan_number: str = ""
    pf_number: str = ""
    payment_mode: str = "Bank Transfer"


class SalaryStructure(BaseModel):
    """Employee salary breakdown"""
    basic: float = 0.0
    hra: float = 0.0
    conveyance: float = 0.0
    special_allowance: float = 0.0
    professional_allowance: float = 0.0
    uniform_allowance: float = 0.0
    shift_allowance: float = 0.0
    medical_allowance: float = 0.0
    pf_employer: float = 1500.0
    pf_employee: float = 1500.0
    professional_tax: float = 200.0


class EmployeeDocument(BaseModel):
    """Employee uploaded document"""
    title: str
    document_type: str # 'certificate', 'aadhar', 'pan', 'other'
    file_url: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending" # pending, verified, rejected


class Employee(Document):
    """Employee document model"""
    
    # Basic Information
    employee_id: str = Field(..., unique=True, index=True)
    first_name: str
    last_name: str
    email: EmailStr = Field(..., unique=True, index=True)
    phone: str
    date_of_birth: datetime
    gender: str  # Male, Female, Other
    
    # Employment Details
    department: str
    designation: str
    role: str = "employee"  # employee, manager, hr, admin
    joining_date: datetime
    employment_type: str = "full-time"  # full-time, part-time, contract
    reporting_manager: Optional[str] = None  # Employee ID of manager
    
    # Address
    address: Address
    
    # Emergency Contact
    emergency_contact: EmergencyContact
    
    # Authentication
    password_hash: str
    is_active: bool = True
    is_verified: bool = False
    
    # Face Recognition (Future)
    face_encoding: Optional[str] = None
    
    # Leave Balance
    casual_leave_balance: float = 12.0
    sick_leave_balance: float = 10.0
    annual_leave_balance: float = 20.0
    
    # Work Schedule
    shift_start_time: str = "09:00"
    shift_end_time: str = "18:00"
    working_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # Payroll
    bank_details: BankDetails = Field(default_factory=BankDetails)
    salary_details: SalaryStructure = Field(default_factory=SalaryStructure)
    
    # Compliance & Documents
    aadhar_number: Optional[str] = None
    documents: List[EmployeeDocument] = []
    is_bank_details_locked: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Profile
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    
    class Settings:
        name = "employees"
        indexes = [
            "employee_id",
            "email",
            "department",
            "role",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "employee_id": "EMP001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@company.com",
                "phone": "+91-9876543210",
                "date_of_birth": "1990-01-15",
                "gender": "Male",
                "department": "Engineering",
                "designation": "Senior Developer",
                "role": "employee",
                "joining_date": "2020-01-01",
                "employment_type": "full-time"
            }
        }


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee"""
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    date_of_birth: datetime
    gender: str
    department: str
    designation: str
    role: str = "employee"
    joining_date: datetime
    employment_type: str = "full-time"
    reporting_manager: Optional[str] = None
    address: Address
    emergency_contact: EmergencyContact
    password: str
    bank_details: Optional[BankDetails] = None
    salary_details: Optional[SalaryStructure] = None


class EmployeeUpdate(BaseModel):
    """Schema for updating employee information"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = None
    reporting_manager: Optional[str] = None
    address: Optional[Address] = None
    emergency_contact: Optional[EmergencyContact] = None
    is_active: Optional[bool] = None
    shift_start_time: Optional[str] = None
    shift_end_time: Optional[str] = None
    working_days: Optional[List[str]] = None
    bank_details: Optional[BankDetails] = None
    salary_details: Optional[SalaryStructure] = None
    aadhar_number: Optional[str] = None
    documents: Optional[List[EmployeeDocument]] = None


class EmployeeResponse(BaseModel):
    """Schema for employee response (without sensitive data)"""
    id: PydanticObjectId
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    department: str
    designation: str
    role: str
    is_active: bool
    joining_date: datetime
    employment_type: str
    shift_start_time: str
    shift_end_time: str
    address: Optional[Address] = None
    emergency_contact: Optional[EmergencyContact] = None
    profile_picture: Optional[str] = None
    bank_details: Optional[BankDetails] = None
    salary_details: Optional[SalaryStructure] = None
    aadhar_number: Optional[str] = None
    documents: List[EmployeeDocument] = []
    is_bank_details_locked: bool
    
    class Config:
        from_attributes = True
