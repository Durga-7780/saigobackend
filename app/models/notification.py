from beanie import Document
from datetime import datetime
from typing import Optional
from enum import Enum

class NotificationType(str, Enum):
    LEAVE_APPLIED = "leave_applied"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    HOLIDAY_ADDED = "holiday_added"
    GENERAL = "general"

class Notification(Document):
    recipient_id: str
    recipient_email: str
    title: str
    message: str
    type: NotificationType
    is_read: bool = False
    created_at: datetime = datetime.utcnow()
    link: Optional[str] = None

    class Settings:
        name = "notifications"
