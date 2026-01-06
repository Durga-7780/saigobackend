"""
Payroll Routes
Salary management and payslip generation
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime
import calendar

from app.models.employee import Employee, SalaryStructure, BankDetails
from app.models.payslip import Payslip, PayslipEarnings, PayslipDeductions, PayslipAttendance, PayslipBankDetails
from app.models.attendance import Attendance, AttendanceStatus
from app.api.routes.auth import get_current_employee
from pydantic import BaseModel

router = APIRouter()

class SalaryUpdate(BaseModel):
    salary_structure: SalaryStructure
    bank_details: BankDetails

class GeneratePayslipRequest(BaseModel):
    employee_id: str
    month: str
    year: int
    working_days: int = 30
    loss_of_pay_days: float = 0.0
    auto_calculate_lop: bool = True

class BulkGenerateRequest(BaseModel):
    month: str
    year: int
    working_days: int = 30

def number_to_words(num):
    # Simple placeholder - normally use num2words library
    return f"{num} Rupees Only"

async def calculate_lop_days(employee_id: str, month: str, year: int) -> float:
    """Calculate Loss of Pay days based on attendance records"""
    try:
        month_num = list(calendar.month_name).index(month)
    except ValueError:
        return 0.0
        
    start_date = datetime(year, month_num, 1)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)
        
    # Count absent days
    absent_count = await Attendance.find(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date < end_date,
        Attendance.status == AttendanceStatus.ABSENT
    ).count()
    
    # Count half days
    half_day_count = await Attendance.find(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date < end_date,
        Attendance.status == AttendanceStatus.HALF_DAY
    ).count()
    
    return float(absent_count + (half_day_count * 0.5))

@router.put("/salary/{employee_id}")
async def update_salary_details(
    employee_id: str,
    data: SalaryUpdate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Update employee salary and bank details (HR/Admin only)"""
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    employee = await Employee.find_one(Employee.employee_id == employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    employee.salary_details = data.salary_structure
    employee.bank_details = data.bank_details
    await employee.save()
    
    return {"message": "Salary details updated successfully"}

@router.post("/generate", response_model=Payslip)
async def generate_payslip(
    request: GeneratePayslipRequest,
    current_employee: Employee = Depends(get_current_employee)
):
    """Generate payslip for an employee"""
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    employee = await Employee.find_one(Employee.employee_id == request.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    # Check if payslip already exists
    existing = await Payslip.find_one(
        Payslip.employee_id == request.employee_id,
        Payslip.month == request.month,
        Payslip.year == request.year
    )
    if existing:
        return existing

    # Auto-calculate LOP if requested
    loss_of_pay_days = request.loss_of_pay_days
    if request.auto_calculate_lop:
        loss_of_pay_days = await calculate_lop_days(request.employee_id, request.month, request.year)

    salary = employee.salary_details
    
    # Calculate Attendance Impact
    daily_pay = salary.basic / 30  # Assuming 30 days base
    loss_of_pay = daily_pay * loss_of_pay_days
    
    # Earnings
    earnings = PayslipEarnings(
        basic=salary.basic,
        hra=salary.hra,
        conveyance=salary.conveyance,
        special_allowance=salary.special_allowance,
        professional_allowance=salary.professional_allowance,
        uniform_allowance=salary.uniform_allowance,
        shift_allowance=salary.shift_allowance,
        medical_allowance=salary.medical_allowance,
        total_earnings=(
            salary.basic + salary.hra + salary.conveyance + 
            salary.special_allowance + salary.professional_allowance + 
            salary.uniform_allowance + salary.shift_allowance + 
            salary.medical_allowance
        )
    )
    
    # Deductions
    total_deductions = (
        salary.pf_employee + 
        salary.professional_tax + 
        loss_of_pay
    )
    
    deductions = PayslipDeductions(
        pf_employee=salary.pf_employee,
        pf_employer=salary.pf_employer,
        professional_tax=salary.professional_tax,
        income_tax=0, # Placeholder
        loss_of_pay=loss_of_pay,
        total_deductions=total_deductions
    )
    
    net_salary = earnings.total_earnings - total_deductions
    
    attendance_record = PayslipAttendance(
        total_days=request.working_days,
        working_days=request.working_days - loss_of_pay_days,
        loss_of_pay_days=loss_of_pay_days,
        payable_days=request.working_days - loss_of_pay_days
    )
    
    bank_details_snapshot = PayslipBankDetails(
        account_number=employee.bank_details.account_number,
        bank_name=employee.bank_details.bank_name,
        ifsc_code=employee.bank_details.ifsc_code,
        pan_number=employee.bank_details.pan_number,
        uan_number=employee.bank_details.uan_number,
        pf_number=employee.bank_details.pf_number,
        payment_mode=employee.bank_details.payment_mode
    )
    
    payslip = Payslip(
        employee_id=employee.employee_id,
        employee_name=f"{employee.first_name} {employee.last_name}",
        designation=employee.designation,
        department=employee.department,
        joining_date=employee.joining_date,
        month=request.month,
        year=request.year,
        earnings=earnings,
        deductions=deductions,
        attendance=attendance_record,
        bank_details=bank_details_snapshot,
        net_salary=round(net_salary, 2),
        net_salary_words=number_to_words(round(net_salary))
    )
    
    await payslip.insert()
    return payslip

@router.post("/generate/bulk", response_model=dict)
async def bulk_generate_payslips(
    request: BulkGenerateRequest,
    current_employee: Employee = Depends(get_current_employee)
):
    """Generate payslips for all active employees (HR/Admin only)"""
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    employees = await Employee.find(Employee.is_active == True).to_list()
    generated_count = 0
    
    for emp in employees:
        # Construct per-employee request
        single_req = GeneratePayslipRequest(
            employee_id=emp.employee_id,
            month=request.month,
            year=request.year,
            working_days=request.working_days,
            auto_calculate_lop=True
        )
        
        await generate_payslip(single_req, current_employee)
        generated_count += 1
        
    return {
        "message": f"Successfully processed payslips for {generated_count} employees",
        "month": request.month,
        "year": request.year
    }

@router.get("/my", response_model=List[Payslip])
async def get_my_payslips(
    current_employee: Employee = Depends(get_current_employee)
):
    """Get payslips for current user"""
    return await Payslip.find(Payslip.employee_id == current_employee.employee_id).sort("-year", "-month").to_list()

@router.get("/all", response_model=List[Payslip])
async def get_all_payslips(
    current_employee: Employee = Depends(get_current_employee)
):
    """Get all payslips (HR/Admin)"""
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return await Payslip.find().sort("-generated_at").to_list()

@router.delete("/{id}")
async def delete_payslip(
    id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Delete a payslip"""
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    payslip = await Payslip.get(id)
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
        
    await payslip.delete()
    return {"message": "Payslip deleted"}
