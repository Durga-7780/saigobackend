"""
Announcement Routes
Endpoints for managing company announcements
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime

from app.models.announcement import Announcement, AnnouncementCreate
from app.models.employee import Employee
from app.api.routes.auth import get_current_employee

router = APIRouter()

@router.get("/", response_model=List[Announcement])
async def get_announcements():
    """Get all active announcements"""
    return await Announcement.find(Announcement.is_active == True).sort("-created_at").to_list()

@router.post("/", response_model=Announcement)
async def create_announcement(
    data: AnnouncementCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Create a new announcement (Admin/HR only)"""
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    announcement = Announcement(
        **data.dict(),
        posted_by=f"{current_employee.first_name} {current_employee.last_name}"
    )
    await announcement.insert()
    return announcement

@router.delete("/{id}")
async def delete_announcement(
    id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Deactivate an announcement"""
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    ann = await Announcement.get(id)
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
        
    ann.is_active = False
    await ann.save()
    return {"message": "Announcement removed"}
