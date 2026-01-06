"""
Meal Model
Database schema for Meal Booking
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from beanie import Document, PydanticObjectId

class Meal(Document):
    """
    Meal model for handling employee meal bookings
    """
    employee_id: str
    employee_name: str
    booking_date: str # YYYY-MM-DD
    meal_type: str # 'lunch' or 'dinner'
    category: str = "veg" # 'veg', 'non-veg'
    items: Optional[str] = None # 'Rice, Dal'
    special_request: Optional[str] = None
    status: str = "booked"  # booked, cancelled, consumed
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "meals"
        indexes = [
            "employee_id",
            "booking_date",
            "status",
            "meal_type"
        ]

class MealCreate(BaseModel):
    booking_date: str # YYYY-MM-DD
    meal_type: str # 'lunch', 'dinner'
    category: str # 'veg', 'non-veg'
    items: str
    special_request: Optional[str] = None

class MealUpdate(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    items: Optional[str] = None
    special_request: Optional[str] = None

class DailyMenu(Document):
    """
    Daily Menu configured by Admin
    """
    date: str  # YYYY-MM-DD
    options: List[str]  # ["Veg Box Meal", "Non-Veg Box Meal"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "daily_menus"
        indexes = ["date"]

class DailyMenuCreate(BaseModel):
    date: str
    options: List[str]

