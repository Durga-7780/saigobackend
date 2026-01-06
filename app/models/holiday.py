from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional
from enum import Enum

class HolidayType(str, Enum):
    PUBLIC = "public"
    OPTIONAL = "optional"
    COMPANY = "company"

class Holiday(Document):
    name: str
    date: datetime
    type: HolidayType = HolidayType.PUBLIC
    description: Optional[str] = None
    is_recurring: bool = True

    class Settings:
        name = "holidays"

class HolidayResponse(Holiday):
    pass
