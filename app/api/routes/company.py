"""
Company Settings Routes
Manage global organization settings
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from app.models.company import CompanySettings
from app.models.employee import Employee
from app.api.routes.auth import get_current_employee
from datetime import datetime
import shutil
import os
import uuid

router = APIRouter()

@router.get("/", response_model=CompanySettings)
async def get_company_settings():
    """Get company settings (Public/Authenticated)"""
    settings = await CompanySettings.find_one()
    if not settings:
        # Return defaults if not set
        return CompanySettings()
    return settings

@router.put("/", response_model=CompanySettings)
async def update_company_settings(
    name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    website: str = Form(None),
    logo: UploadFile = File(None),
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Update company settings (Admin/HR only)
    """
    if current_employee.role not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins or HR can update company settings"
        )
    
    existing = await CompanySettings.find_one()
    if not existing:
        existing = CompanySettings()

    existing.name = name
    existing.address = address
    existing.phone = phone
    existing.email = email
    existing.website = website
    
    if logo:
        # Create uploads dir if not likely present (handled in main but good for safety)
        os.makedirs("uploads", exist_ok=True)
        
        # specific file name
        file_extension = logo.filename.split(".")[-1]
        file_name = f"company_logo_{uuid.uuid4()}.{file_extension}"
        file_location = f"uploads/{file_name}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)
            
        # Update URL (assuming served from /uploads)
        from app.config import settings
        # We'll construct a relative or absolute URL. Ideally usage of settings.BASE_URL if available
        # For now, relative path that frontend can use
        existing.logo_url = f"{settings.HOST_URL}/uploads/{file_name}" if hasattr(settings, 'HOST_URL') else f"http://localhost:8000/uploads/{file_name}"

    existing.updated_at = datetime.utcnow()
    existing.updated_by = current_employee.employee_id
    
    if existing.id:
        await existing.save()
    else:
        await existing.insert()
        
    return existing
