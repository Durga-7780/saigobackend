"""
Requests Routes
Endpoints for handling internal requests (e.g. Profile updates)
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.employee import Employee
from app.models.request import Request, RequestCreate, RequestUpdate
from app.api.routes.auth import get_current_employee

router = APIRouter()

@router.post("/", response_model=Request)
async def create_request(
    request_data: RequestCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Create a new request"""
    # Check for duplicate pending request
    existing = await Request.find_one(
        Request.employee_id == current_employee.employee_id,
        Request.request_type == request_data.request_type,
        Request.status == "pending"
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending request of this type."
        )

    new_req = Request(
        employee_id=current_employee.employee_id,
        employee_name=f"{current_employee.first_name} {current_employee.last_name}",
        request_type=request_data.request_type,
        reason=request_data.reason,
        approver_id=request_data.approver_id,
        status="pending"
    )
    await new_req.insert()
    return new_req

@router.get("/", response_model=List[Request])
async def get_requests(
    status: str = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """Get all requests (Admin/HR), my requests (Employee), or requests assigned to me for approval"""
    if current_employee.role in ["admin", "hr"]:
        query = {}
        if status:
            query["status"] = status
        return await Request.find(query).sort("-created_at").to_list()
    else:
        # Employee sees their own OR requests where they are the approver
        # Using $or operator from MongoDB syntax which Beanie supports
        query = {
            "$or": [
                {"employee_id": current_employee.employee_id},
                {"approver_id": current_employee.employee_id}
            ]
        }
        if status:
            query["status"] = status
        return await Request.find(query).sort("-created_at").to_list()

@router.patch("/{request_id}", response_model=Request)
async def update_request_status(
    request_id: str,
    update_data: RequestUpdate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Approve or Reject a request (Admin/HR or Designated Approver)"""
    req = await Request.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check authorization: Admin/HR OR the designated approver
    is_authorized = (
        current_employee.role in ["admin", "hr"] or 
        (req.approver_id and req.approver_id == current_employee.employee_id)
    )
    
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    req.status = update_data.status
    if update_data.admin_comment:
        req.admin_comment = update_data.admin_comment
    req.updated_at = datetime.utcnow()
    
    await req.save()
    
    # If approved and type is 'bank_details_update', unlock the employee profile
    if req.status == 'approved' and req.request_type == 'bank_details_update':
        emp = await Employee.find_one(Employee.employee_id == req.employee_id)
        if emp:
            emp.is_bank_details_locked = False
            await emp.save()
            
    return req
