"""
Dashboard Routes
Analytics and reporting endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from typing import Optional

from app.models.employee import Employee
from app.models.attendance import Attendance, AttendanceStatus
from app.models.leave import Leave, LeaveStatus
from app.models.holiday import Holiday
from app.models.meal import Meal
from app.api.routes.auth import get_current_employee


router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get dashboard overview for current employee
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Today's attendance
    today_attendance = await Attendance.find_one(
        Attendance.employee_id == current_employee.employee_id,
        Attendance.date >= today
    )
    
    # This month's stats
    month_start = today.replace(day=1)
    month_attendance = await Attendance.find(
        Attendance.employee_id == current_employee.employee_id,
        Attendance.date >= month_start
    ).to_list()
    
    # Pending leaves
    pending_leaves = await Leave.find(
        Leave.employee_id == current_employee.employee_id,
        Leave.status == LeaveStatus.PENDING
    ).to_list()
    
    # Calculate stats
    present_days = sum(1 for a in month_attendance if a.status == AttendanceStatus.PRESENT)
    late_days = sum(1 for a in month_attendance if a.is_late)
    total_hours = sum(a.total_hours or 0 for a in month_attendance)
    
    # Upcoming Holidays (Next 5)
    upcoming_holidays = await Holiday.find(
        Holiday.date >= today
    ).sort("date").limit(5).to_list()

    # Upcoming Meals
    upcoming_meals = await Meal.find(
        Meal.employee_id == current_employee.employee_id,
        Meal.booking_date >= str(today.date()),
        Meal.status == "booked"
    ).count()
    
    return {
        "today": {
            "checked_in": today_attendance.check_in_time if today_attendance else None,
            "checked_out": today_attendance.check_out_time if today_attendance else None,
            "status": today_attendance.status if today_attendance else "not_marked"
        },
        "this_month": {
            "total_days": len(month_attendance),
            "present_days": present_days,
            "late_days": late_days,
            "total_hours": round(total_hours, 2),
            "attendance_percentage": round((present_days / len(month_attendance) * 100) if month_attendance else 0, 2)
        },
        "leave_balance": {
            "casual": current_employee.casual_leave_balance,
            "sick": current_employee.sick_leave_balance,
            "annual": current_employee.annual_leave_balance
        },
        "pending_leaves": len(pending_leaves),
        "pending_leaves": len(pending_leaves),
        "upcoming_holidays": upcoming_holidays,
        "booked_meals": upcoming_meals
    }


@router.get("/admin/stats")
async def get_admin_stats(
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get admin dashboard statistics
    """
    if current_employee.role not in ["hr", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only HR and Admin can access this endpoint"
        )
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total employees
    total_employees = await Employee.find().count()
    active_employees = await Employee.find(Employee.is_active == True).count()
    
    # Today's attendance
    today_attendance = await Attendance.find(
        Attendance.date >= today
    ).to_list()
    
    present_today = sum(1 for a in today_attendance if a.check_in_time)
    late_today = sum(1 for a in today_attendance if a.is_late)
    
    # Pending leaves
    pending_leaves = await Leave.find(
        Leave.status == LeaveStatus.PENDING
    ).count()
    
    # Department-wise breakdown
    departments = {}
    all_employees = await Employee.find().to_list()
    
    for emp in all_employees:
        dept = emp.department
        if dept not in departments:
            departments[dept] = {"total": 0, "present": 0}
        departments[dept]["total"] += 1
    
    for att in today_attendance:
        dept = att.department
        if dept in departments and att.check_in_time:
            departments[dept]["present"] += 1
    
    # Attendance Trends (Last 7 Days)
    attendance_trends = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_att = await Attendance.find(
            Attendance.date == date
        ).to_list()
        
        attendance_trends.append({
            "date": date.strftime("%d %b"),
            "present": sum(1 for a in day_att if a.check_in_time),
            "late": sum(1 for a in day_att if a.is_late)
        })

    # Leave Stats
    all_leaves = await Leave.find().to_list()
    leave_stats = {
        "pending": sum(1 for l in all_leaves if l.status == LeaveStatus.PENDING),
        "approved": sum(1 for l in all_leaves if l.status == LeaveStatus.APPROVED),
        "rejected": sum(1 for l in all_leaves if l.status == LeaveStatus.REJECTED)
    }

    return {
        "employees": {
            "total": total_employees,
            "active": active_employees,
            "inactive": total_employees - active_employees
        },
        "today_attendance": {
            "total": len(today_attendance),
            "present": present_today,
            "absent": active_employees - present_today,
            "late": late_today,
            "percentage": round((present_today / active_employees * 100) if active_employees > 0 else 0, 2)
        },
        "pending_leaves": pending_leaves,
        "departments": departments,
        "attendance_trends": attendance_trends,
        "leave_stats": leave_stats
    }
