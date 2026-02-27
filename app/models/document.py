from datetime import datetime
from typing import Optional
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from enum import Enum

class DocumentType(str, Enum):
    OFFER_LETTER = "offer_letter"
    EXPERIENCE_LETTER = "experience_letter"
    SALARY_REVISION = "salary_revision"
    OTHER = "other"

class DocumentTemplate(Document):
    """
    Model for storing reusable document templates (Offer Letter, etc.)
    """
    type: str = Field(..., index=True) # offer_letter, experience_letter
    content: str  # The raw text/html structure
    is_active: bool = True
    
    updated_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "document_templates"

class GeneratedDocument(Document):
    """
    Model for HR-generated official documents/letters
    """
    title: str
    type: DocumentType
    content: str
    
    employee_id: str = Field(..., index=True)
    employee_name: str
    
    created_by: str  # HR Employee ID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "generated_documents"
        indexes = [
            "employee_id",
            "type"
        ]

class DocumentCreate(BaseModel):
    title: str
    type: DocumentType
    content: str
    employee_id: str
    employee_name: str

class DocumentGenerateRequest(BaseModel):
    type: DocumentType
    employee_id: str
    custom_instructions: Optional[str] = None
