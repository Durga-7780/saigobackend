"""
Company Settings Model
Stores organization details like name, address, logo, etc.
"""
from typing import Optional
from pydantic import BaseModel, HttpUrl
from beanie import Document
from datetime import datetime

class CompanySettings(Document):
    name: str = "My Company"
    address: str = "Company Address, City, State, Zip"
    logo_url: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Currency settings could go here too
    currency_symbol: str = "₹"
    
    updated_at: datetime = datetime.utcnow()
    updated_by: Optional[str] = None

    class Settings:
        name = "company_settings"

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corp",
                "address": "123 Tech Park, Hyderabad, 500081",
                "phone": "+91 40 1234 5678"
            }
        }
