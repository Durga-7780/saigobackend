"""
Leave Routes
Leave application and management
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime

from app.models.leave import (
    Leave,
    LeaveCreate,
    LeaveUpdate,
    LeaveApprovalRequest,
    LeaveResponse,
    LeaveListResponse,
    LeaveStatus,
    LeaveType,
    LeaveApproval,
    PydanticObjectId
)
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.notification import Notification, NotificationType
from app.api.routes.auth import get_current_employee
from app.services.email import email_service
from app.config import settings


router = APIRouter()


@router.post("/apply")
async def apply_leave(
    request: LeaveCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Apply for leave
    """
    # Verify employee
    if request.employee_id != current_employee.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot apply leave for another employee"
        )
    
    # Check for holidays
    holiday_start = await Holiday.find_one(Holiday.date == request.start_date)
    holiday_end = await Holiday.find_one(Holiday.date == request.end_date)
    
    holiday_warning = None
    if holiday_start:
        holiday_warning = f"Note: {request.start_date.strftime('%d %b')} is a holiday ({holiday_start.name})"
    elif holiday_end:
        holiday_warning = f"Note: {request.end_date.strftime('%d %b')} is a holiday ({holiday_end.name})"
    
    # Calculate total days
    total_days = (request.end_date - request.start_date).days + 1
    if request.is_half_day:
        total_days = 0.5
    
    # Check leave balance
    leave_balance = {
        LeaveType.CASUAL: current_employee.casual_leave_balance,
        LeaveType.SICK: current_employee.sick_leave_balance,
        LeaveType.ANNUAL: current_employee.annual_leave_balance
    }
    
    if request.leave_type in leave_balance:
        if leave_balance[request.leave_type] < total_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {request.leave_type} leave balance"
            )
    
    # Create leave application
    leave = Leave(
        employee_id=current_employee.employee_id,
        employee_name=f"{current_employee.first_name} {current_employee.last_name}",
        department=current_employee.department,
        reporting_manager=current_employee.reporting_manager,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=total_days,
        is_half_day=request.is_half_day,
        half_day_session=request.half_day_session,
        reason=request.reason,
        attachments=request.attachments,
        current_approver=current_employee.reporting_manager
    )
    
    await leave.insert()
    
    # Notify Managers/HR
    managers = await Employee.find({"role": {"$in": ["hr", "admin"]}}).to_list()
    for m in managers:
        notif = Notification(
            recipient_id=m.employee_id,
            recipient_email=m.email,
            title="New Leave Application",
            message=f"{current_employee.first_name} applied for {leave.leave_type} leave.",
            type=NotificationType.LEAVE_APPLIED,
            link="/admin"
        )
        await notif.insert()
        await email_service.send_leave_application_notification(m.email, f"{current_employee.first_name} {current_employee.last_name}", leave)
    
    return {
        "message": "Leave application submitted successfully",
        "leave_id": str(leave.id),
        "status": leave.status,
        "total_days": total_days,
        "warning": holiday_warning
    }


@router.get("/all", response_model=LeaveListResponse)
async def get_all_leaves(
    status: Optional[LeaveStatus] = None,
    department: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get all leave applications (for managers/HR/Admin)
    """
    if current_employee.role not in ["manager", "hr", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers, HR, and Admin can view all leaves"
        )
    
    query = {}
    if status:
        query["status"] = status
    if department:
        query["department"] = department
    
    # RULE: HR cannot view/manage leaves for their own department
    if current_employee.role == 'hr':
        # Apply filter to exclude own department
        # If specific department requested, ensure it's not their own
        if department and department == current_employee.department:
             return { "total": 0, "leaves": [] } # Trying to access restricted department
        
        # If no specific dept or different dept, FORCE exclusion of own dept
        if not department:
            query["department"] = {"$ne": current_employee.department}
        
    leaves = await Leave.find(query).sort("-applied_at").to_list()
    
    return {
        "total": len(leaves),
        "leaves": leaves
    }


@router.get("/my-leaves", response_model=LeaveListResponse)
async def get_my_leaves(
    status: Optional[LeaveStatus] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get leave applications for current employee
    """
    query = {"employee_id": current_employee.employee_id}
    
    if status:
        query["status"] = status
    
    leaves = await Leave.find(query).sort("-applied_at").to_list()
    
    return {
        "total": len(leaves),
        "leaves": leaves
    }


@router.get("/balance")
async def get_leave_balance(
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get leave balance for current employee
    """
    return {
        "employee_id": current_employee.employee_id,
        "casual_leave": current_employee.casual_leave_balance,
        "sick_leave": current_employee.sick_leave_balance,
        "annual_leave": current_employee.annual_leave_balance,
        "total_available": (
            current_employee.casual_leave_balance +
            current_employee.sick_leave_balance +
            current_employee.annual_leave_balance
        )
    }


@router.post("/approve")
async def approve_leave(
    request: LeaveApprovalRequest,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Approve or reject leave application
    """
    # Check if user is manager or HR
    if current_employee.role not in ["manager", "hr", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers and HR can approve leaves"
        )
    
    # Get leave application
    try:
        leave = await Leave.get(PydanticObjectId(request.leave_id))
    except Exception as e:
        print(f"Error finding leave {request.leave_id}: {e}")
        leave = None
    
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Leave application with ID {request.leave_id} not found"
        )
    
    
    # 1. Fetch requester to validate rules
    requester = await Employee.find_one(Employee.employee_id == leave.employee_id)
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee (requester) not found"
        )

    # RULE: HR leave requests can only be approved by Admin or Manager
    if requester.role == "hr" and current_employee.role == "hr":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR leave requests must be approved by Admin or Manager"
        )
    
    # RULE: HRs cannot approve leaves defined for their own department (conflict of interest)
    if current_employee.role == "hr" and requester.department == current_employee.department:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR cannot approve leaves for their own department"
        )

    # Update leave status
    approval = LeaveApproval(
        approver_id=current_employee.employee_id,
        approver_name=f"{current_employee.first_name} {current_employee.last_name}",
        status=request.status,
        comments=request.comments or f"Processed by {current_employee.role}"
    )
    
    leave.approvals.append(approval)
    leave.status = request.status
    leave.updated_at = datetime.utcnow()
    
    await leave.save()
    
    # If approved, deduct from leave balance
    if request.status == LeaveStatus.APPROVED:
        try:
            employee = await Employee.find_one(Employee.employee_id == leave.employee_id)
            
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Employee with ID {leave.employee_id} not found"
                )
            
            if leave.leave_type == LeaveType.CASUAL:
                employee.casual_leave_balance -= leave.total_days
            elif leave.leave_type == LeaveType.SICK:
                employee.sick_leave_balance -= leave.total_days
            elif leave.leave_type == LeaveType.ANNUAL:
                employee.annual_leave_balance -= leave.total_days
            
            await employee.save()
        except Exception as e:
            print(f"Error deducting leave balance: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating leave balance: {str(e)}"
            )
    
    await leave.save()
    
    # Notify Employee
    employee = await Employee.find_one(Employee.employee_id == leave.employee_id)
    if employee:
        notif = Notification(
            recipient_id=employee.employee_id,
            recipient_email=employee.email,
            title=f"Leave Request {request.status.capitalize()}",
            message=f"Your {leave.leave_type} leave request has been {request.status}.",
            type=NotificationType.LEAVE_APPROVED if request.status == LeaveStatus.APPROVED else NotificationType.LEAVE_REJECTED,
            link="/leaves"
        )
        await notif.insert()
        await email_service.send_leave_status_notification(employee, leave, request.status)
    
    return {
        "message": f"Leave {request.status}",
        "leave_id": str(leave.id)
    }


@router.delete("/{leave_id}")
async def cancel_leave(
    leave_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Cancel leave application
    """
    leave = await Leave.get(leave_id)
    
    if not leave:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave application not found"
        )
    
    # Verify ownership
    if leave.employee_id != current_employee.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another employee's leave"
        )
    
    # Can only cancel pending leaves
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending leave applications"
        )
    
    leave.status = LeaveStatus.CANCELLED
    leave.updated_at = datetime.utcnow()
    await leave.save()
    
    return {
        "message": "Leave application cancelled",
        "leave_id": str(leave.id)
    }
