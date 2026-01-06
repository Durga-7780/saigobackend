"""
Announcement Model
Database schema for company announcements
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from beanie import Document

class Announcement(Document):
    """Announcement document model"""
    title: str
    content: str
    priority: str = "normal"  # normal, high, urgent
    category: str = "general" # general, policy, holiday, news
    posted_by: str  # Admin name
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "announcements"
        indexes = ["priority", "category", "created_at"]

class AnnouncementCreate(BaseModel):
    """Schema for creating an announcement"""
    title: str
    content: str
    priority: str = "normal"
    category: str = "general"
    expires_at: Optional[datetime] = None
