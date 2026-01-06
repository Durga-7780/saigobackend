"""
Employee Routes
Employee management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional

from app.models.employee import Employee, EmployeeUpdate, EmployeeResponse, EmployeeCreate
from app.api.routes.auth import get_current_employee, get_password_hash


router = APIRouter()


@router.post("/", response_model=EmployeeResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Create a new employee (Admin only)
    """
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and HR can create employees"
        )
    
    # Check if employee already exists
    existing = await Employee.find_one(Employee.email == employee_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    # Hash password
    password_hash = get_password_hash(employee_data.password)
    
    # Create employee
    employee_dict = employee_data.dict(exclude={"password"})
    
    # Remove None values for nested models to allow defaults to trigger
    if employee_dict.get("bank_details") is None:
        employee_dict.pop("bank_details", None)
    if employee_dict.get("salary_details") is None:
        employee_dict.pop("salary_details", None)
        
    employee = Employee(**employee_dict, password_hash=password_hash)
    
    await employee.insert()
    
    return employee


@router.get("/me", response_model=EmployeeResponse)
async def get_my_profile(current_employee: Employee = Depends(get_current_employee)):
    """Get current employee profile"""
    return current_employee


@router.put("/me")
async def update_my_profile(
    update_data: EmployeeUpdate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Update current employee profile"""
    update_dict = update_data.dict(exclude_unset=True)
    
    # Check if attempting to update bank details
    # Check if attempting to update bank details
    if "bank_details" in update_dict:
        # Check if bank details are locked (default is True)
        is_locked = getattr(current_employee, "is_bank_details_locked", True)
        
        # If user has locked bank details and trying to update, verify if they are allowed
        # We allow update if:
        # 1. is_bank_details_locked is False (HR unlocked it)
        # 2. OR account_number is currently empty (first time setup)
        
        has_existing_account = current_employee.bank_details and current_employee.bank_details.account_number
        
        if has_existing_account and is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bank details are locked. Please request HR to unlock them for editing."
            )
        
        # Handle nested update for bank details
        bd_data = update_dict.pop("bank_details")
        if not current_employee.bank_details:
             from app.models.employee import BankDetails
             current_employee.bank_details = BankDetails()
             
        for field, value in bd_data.items():
             if value is not None:
                 setattr(current_employee.bank_details, field, value)

    for field, value in update_dict.items():
        if field == "salary_details": 
             continue # Employees cannot update their own salary
        if field == "is_bank_details_locked":
             continue # Employees cannot unlock themselves
        setattr(current_employee, field, value)
    
    await current_employee.save()
    
    return {
        "message": "Profile updated successfully",
        "employee": current_employee
    }


@router.post("/{employee_id}/unlock-bank-details")
async def unlock_bank_details(
    employee_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Unlock bank details for an employee to allow them to edit (HR/Admin only)
    """
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and HR can unlock bank details"
        )
    
    employee = await Employee.find_one(Employee.employee_id == employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
        
    employee.is_bank_details_locked = False
    await employee.save()
    
    return {"message": f"Bank details unlocked for employee {employee_id}"}


@router.post("/{employee_id}/lock-bank-details")
async def lock_bank_details(
    employee_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Lock bank details for an employee (HR/Admin only)
    """
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and HR can lock bank details"
        )
    
    employee = await Employee.find_one(Employee.employee_id == employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
        
    employee.is_bank_details_locked = True
    await employee.save()
    
    return {"message": f"Bank details locked for employee {employee_id}"}





@router.get("/all")
async def get_all_employees(
    department: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get all employees (for managers/HR)
    """
    # Allow all authenticated employees to view the list (needed for directory/search)
    # The response is already filtered to show only public info
    pass
    
    query = {}
    if department:
        query["department"] = department
    
    employees = await Employee.find(query).to_list()
    
    return {
        "total": len(employees),
        "employees": [
            {
                "employee_id": emp.employee_id,
                "name": f"{emp.first_name} {emp.last_name}",
                "email": emp.email,
                "department": emp.department,
                "designation": emp.designation,
                "role": emp.role,
                "is_active": emp.is_active,
                "shift_start_time": emp.shift_start_time,
                "shift_end_time": emp.shift_end_time,
                "working_days": emp.working_days
            }
            for emp in employees
        ]
    }


@router.get("/{employee_id}")
async def get_employee(
    employee_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Get employee by ID"""
    # Check permissions
    if (current_employee.role not in ["manager", "hr", "admin"] and
        current_employee.employee_id != employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other employee's details"
        )
    
    employee = await Employee.find_one(Employee.employee_id == employee_id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee


@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    update_data: EmployeeUpdate,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Update an employee's profile (Admin/HR only)
    """
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and HR can update other employee profiles"
        )
    
    employee = await Employee.find_one(Employee.employee_id == employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    update_dict = update_data.dict(exclude_unset=True)
    
    # Nested address update
    if "address" in update_dict and update_dict["address"]:
        addr_data = update_dict.pop("address")
        for field, value in addr_data.items():
            if value is not None:
                setattr(employee.address, field, value)
                
    # Nested emergency contact update
    if "emergency_contact" in update_dict and update_dict["emergency_contact"]:
        ec_data = update_dict.pop("emergency_contact")
        for field, value in ec_data.items():
            if value is not None:
                setattr(employee.emergency_contact, field, value)

    for field, value in update_dict.items():
        if value is not None:
            setattr(employee, field, value)
    
    employee.updated_at = datetime.utcnow()
    await employee.save()
    
    return {
        "message": "Employee updated successfully",
        "employee_id": employee.employee_id
    }
