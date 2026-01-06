"""
Holiday Routes
Admin management and public listing
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from app.models.holiday import Holiday, HolidayResponse, HolidayType
from app.models.employee import Employee
from app.api.routes.auth import get_current_employee

router = APIRouter()

@router.get("/", response_model=List[HolidayResponse])
async def get_all_holidays():
    """Get all holidays sorted by date"""
    return await Holiday.find().sort("date").to_list()

@router.post("/", response_model=HolidayResponse)
async def create_holiday(
    holiday: Holiday,
    current_employee: Employee = Depends(get_current_employee)
):
    """Create a new holiday (Admin/HR only)"""
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await holiday.insert()
    return holiday

@router.put("/{holiday_id}", response_model=HolidayResponse)
async def update_holiday(
    holiday_id: str,
    holiday_update: Holiday,
    current_employee: Employee = Depends(get_current_employee)
):
    """Update a holiday (Admin/HR only)"""
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing = await Holiday.get(holiday_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    await existing.update({"$set": holiday_update.model_dump(exclude={"id"})})
    return existing

@router.delete("/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Delete a holiday (Admin/HR only)"""
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    holiday = await Holiday.get(holiday_id)
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    await holiday.delete()
    return {"message": "Holiday deleted successfully"}
