"""
Attendance Routes
Handles attendance check-in, check-out, and queries
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.models.attendance import (
    Attendance,
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceResponse,
    AttendanceListResponse,
    TodayAttendanceResponse,
    AttendanceStatus,
    AttendanceType,
    PydanticObjectId
)
from app.models.employee import Employee
from app.api.routes.auth import get_current_employee
from app.services.email import email_service
from app.config import settings

router = APIRouter()


class AttendanceQuery(BaseModel):
    """Query parameters for attendance"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    employee_id: Optional[str] = None
    status: Optional[AttendanceStatus] = None


@router.post("/check-in")
async def check_in(
    request: AttendanceCheckIn,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Check-in attendance
    """
    # Verify employee
    if request.employee_id != current_employee.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot check-in for another employee"
        )
    
    # Define today's date for the record
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if there is an active session (checked in but not checked out)
    active_session = await Attendance.find_one(
        Attendance.employee_id == request.employee_id,
        Attendance.check_out_time == None
    )
    
    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already checked in. Please check out before checking in again."
        )
    
    # Calculate if late (Only for the FIRST check-in of the day)
    check_in_time = datetime.utcnow()
    
    # See if this is the first check-in today
    first_today = await Attendance.find_one(
        Attendance.employee_id == request.employee_id,
        Attendance.date >= today
    )
    
    is_late = False
    if not first_today:
        shift_start = datetime.strptime(current_employee.shift_start_time, "%H:%M").time()
        is_late = check_in_time.time() > (
            datetime.combine(datetime.today(), shift_start) + 
            timedelta(minutes=settings.LATE_ARRIVAL_THRESHOLD_MINUTES)
        ).time()
    
    # Create new attendance record (since we support multiple sessions/toggle)
    attendance = Attendance(
        employee_id=current_employee.employee_id,
        employee_name=f"{current_employee.first_name} {current_employee.last_name}",
        department=current_employee.department,
        date=today,
        day_of_week=today.strftime("%A"),
        check_in_time=check_in_time,
        check_in_type=request.check_in_type,
        check_in_location=request.location,
        check_in_device=request.device_info,
        is_late=is_late,
        status=AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT,
        remarks=request.remarks,
    )
    await attendance.insert()
    
    # Trigger late arrival email if applicable
    if is_late:
        try:
            await email_service.send_late_arrival_alert(current_employee, check_in_time)
        except Exception as e:
            print(f"Failed to trigger late arrival email: {e}")
    
    return {
        "message": "Checked in successfully",
        "attendance_id": str(attendance.id),
        "check_in_time": check_in_time,
        "is_late": is_late,
        "status": attendance.status
    }


@router.post("/check-out")
async def check_out(
    request: AttendanceCheckOut,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Check-out attendance
    """
    # Verify employee
    if request.employee_id != current_employee.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot check-out for another employee"
        )
    
    # Find the most recent active session (no checkout)
    attendance = await Attendance.find(
        Attendance.employee_id == request.employee_id,
        Attendance.check_out_time == None
    ).sort("-check_in_time").first_or_none()
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active check-in found. Please check in first."
        )
    
    # Update attendance
    check_out_time = datetime.utcnow()
    attendance.check_out_time = check_out_time
    attendance.check_out_type = request.check_out_type
    attendance.check_out_location = request.location
    attendance.check_out_device = request.device_info
    
    # Calculate total hours
    time_diff = check_out_time - attendance.check_in_time
    total_hours = time_diff.total_seconds() / 3600
    attendance.total_hours = round(total_hours, 2)
    
    # Check for early departure
    shift_end = datetime.strptime(current_employee.shift_end_time, "%H:%M").time()
    is_early = check_out_time.time() < (
        datetime.combine(datetime.today(), shift_end) - 
        timedelta(minutes=settings.EARLY_DEPARTURE_THRESHOLD_MINUTES)
    ).time()
    attendance.is_early_departure = is_early
    
    # Update remarks
    if request.remarks:
        attendance.remarks = f"{attendance.remarks or ''}\nCheckout: {request.remarks}"
    
    await attendance.save()
    
    # Calculate Total Daily Hours so far
    daily_records = await Attendance.find(
        Attendance.employee_id == request.employee_id,
        Attendance.date >= attendance.date # Today's date
    ).to_list()
    
    total_daily_hours = sum(r.total_hours or 0 for r in daily_records)
    
    # Check 8-hour rule
    under_hours = total_daily_hours < 8.0
    
    # Trigger short hours email if they are checking out near or after shift end
    # and they haven't completed 8 hours.
    if under_hours:
        # If checkout is within 60 mins of shift end or later
        shift_end_dt = datetime.combine(datetime.today(), shift_end)
        if check_out_time >= (shift_end_dt - timedelta(minutes=60)):
            try:
                await email_service.send_short_hours_alert(
                    current_employee, 
                    round(total_daily_hours, 2), 
                    attendance.date
                )
            except Exception as e:
                print(f"Failed to trigger short hours email: {e}")
    
    return {
        "message": "Checked out successfully",
        "attendance_id": str(attendance.id),
        "check_out_time": check_out_time,
        "session_hours": attendance.total_hours,
        "total_daily_hours": round(total_daily_hours, 2),
        "is_early_departure": is_early,
        "under_target_hours": under_hours,
        "remarks": "Please work at least 8 hours today to avoid alert emails." if under_hours else "Good job! Target hours reached."
    }


@router.get("/my-attendance", response_model=AttendanceListResponse)
async def get_my_attendance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get attendance records for current employee
    """
    query = {"employee_id": current_employee.employee_id}
    
    if start_date:
        query["date"] = {"$gte": datetime.fromisoformat(start_date)}
    
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = datetime.fromisoformat(end_date)
        else:
            query["date"] = {"$lte": datetime.fromisoformat(end_date)}
    
    records = await Attendance.find(query).sort("-date").to_list()
    
    return {
        "total": len(records),
        "records": records
    }


@router.get("/today", response_model=TodayAttendanceResponse)
async def get_today_attendance(
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get today's attendance status
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # First, look for an active session (checked in but not checked out)
    attendance = await Attendance.find_one(
        Attendance.employee_id == current_employee.employee_id,
        Attendance.check_out_time == None
    )
    
    # If no active session, look for the most recent completed session today
    if not attendance:
        attendance = await Attendance.find(
            Attendance.employee_id == current_employee.employee_id,
            Attendance.date >= today
        ).sort("-check_in_time").first_or_none()
    
    if not attendance:
        return {
            "status": "not_marked",
            "message": "No attendance marked today"
        }
    
    return {
        "status": "marked",
        "attendance": attendance,
        "checked_in": attendance.check_in_time is not None,
        "checked_out": attendance.check_out_time is not None
    }


@router.get("/stats")
async def get_attendance_stats(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get attendance statistics
    """
    # Default to current month
    if not month or not year:
        now = datetime.utcnow()
        month = now.month
        year = now.year
    
    # Get records for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    records = await Attendance.find(
        Attendance.employee_id == current_employee.employee_id,
        Attendance.date >= start_date,
        Attendance.date < end_date
    ).to_list()
    
    # Calculate statistics
    total_days = len(records)
    present_days = sum(1 for r in records if r.status == AttendanceStatus.PRESENT or r.status == AttendanceStatus.LATE)
    late_days = sum(1 for r in records if r.is_late)
    leave_days = sum(1 for r in records if r.status == AttendanceStatus.ON_LEAVE)
    wfh_days = sum(1 for r in records if r.status == AttendanceStatus.WORK_FROM_HOME)
    half_days = sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY)
    absent_days = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    
    total_hours = sum(r.total_hours or 0 for r in records)
    
    return {
        "month": month,
        "year": year,
        "total_days": total_days,
        "present_days": present_days,
        "late_days": late_days,
        "leave_days": leave_days,
        "wfh_days": wfh_days,
        "half_days": half_days,
        "absent_days": absent_days,
        "attendance_percentage": round((present_days / total_days * 100) if total_days > 0 else 0, 2),
        "total_hours": round(total_hours, 2),
        "average_hours": round(total_hours / total_days if total_days > 0 else 0, 2)
    }
