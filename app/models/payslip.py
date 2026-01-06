"""
Payslip Model
Database schema for monthly payslips
"""
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field
from beanie import Document

class PayslipEarnings(BaseModel):
    basic: float = 0.0
    hra: float = 0.0
    conveyance: float = 0.0
    special_allowance: float = 0.0
    professional_allowance: float = 0.0
    uniform_allowance: float = 0.0
    shift_allowance: float = 0.0
    medical_allowance: float = 0.0
    total_earnings: float = 0.0

class PayslipDeductions(BaseModel):
    pf_employee: float = 0.0
    pf_employer: float = 0.0
    professional_tax: float = 0.0
    income_tax: float = 0.0
    other_deductions: float = 0.0
    loss_of_pay: float = 0.0
    total_deductions: float = 0.0

class PayslipAttendance(BaseModel):
    total_days: int
    working_days: float
    loss_of_pay_days: float
    payable_days: float

class PayslipBankDetails(BaseModel):
    account_number: str
    bank_name: str
    ifsc_code: str
    pan_number: str
    uan_number: str
    pf_number: str
    payment_mode: str

class Payslip(Document):
    """Payslip document model"""
    employee_id: str
    employee_name: str
    designation: str
    department: str
    joining_date: datetime
    
    month: str
    year: int
    
    earnings: PayslipEarnings
    deductions: PayslipDeductions
    attendance: PayslipAttendance
    bank_details: PayslipBankDetails
    
    net_salary: float
    net_salary_words: str
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "payslips"
        indexes = [
            "employee_id",
            "month",
            "year"
        ]
