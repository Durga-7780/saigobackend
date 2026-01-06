"""
Notification Routes
User-specific alerts and read-tracking
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime

from app.models.notification import Notification, NotificationType
from app.models.employee import Employee
from app.api.routes.auth import get_current_employee

router = APIRouter()

@router.get("/", response_model=List[Notification])
async def get_my_notifications(
    current_employee: Employee = Depends(get_current_employee),
    unread_only: bool = False
):
    """Get notifications for current user"""
    query = {"recipient_id": current_employee.employee_id}
    if unread_only:
        query["is_read"] = False
        
    return await Notification.find(query).sort("-created_at").limit(20).to_list()

@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Mark a notification as read"""
    notif = await Notification.get(notification_id)
    if not notif or notif.recipient_id != current_employee.employee_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notif.is_read = True
    await notif.save()
    return {"message": "Notification marked as read"}

@router.put("/read-all")
async def mark_all_as_read(
    current_employee: Employee = Depends(get_current_employee)
):
    """Mark all notifications as read"""
    await Notification.find(
        Notification.recipient_id == current_employee.employee_id,
        Notification.is_read == False
    ).update({"$set": {"is_read": True}})
    
    return {"message": "All notifications marked as read"}

@router.delete("/clear-all")
async def clear_all_notifications(
    current_employee: Employee = Depends(get_current_employee)
):
    """Delete all notifications for the current user"""
    await Notification.find(
        Notification.recipient_id == current_employee.employee_id
    ).delete()
    
    return {"message": "All notifications cleared"}
