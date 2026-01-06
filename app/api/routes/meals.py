"""
Meal Routes
Endpoints for booking and managing meals
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.employee import Employee
from app.models.meal import Meal, MealCreate, MealUpdate, DailyMenu, DailyMenuCreate
from app.models.holiday import Holiday
from app.models.leave import Leave, LeaveStatus
from app.models.notification import Notification
from app.api.routes.auth import get_current_employee

router = APIRouter()

@router.get("/stats")
async def get_meal_stats(
    date: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """Get meal statistics for a specific date (Admin only)"""
    if current_employee.role not in ["admin", "hr", "manager"]:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    target_date = date or str(datetime.utcnow().date())
    
    meals = await Meal.find(
        Meal.booking_date == target_date,
        Meal.status == "booked"
    ).to_list()
    
    veg_count = sum(1 for m in meals if m.category == "veg")
    non_veg_count = sum(1 for m in meals if m.category == "non-veg")
    
    return {
        "date": target_date,
        "total": len(meals),
        "veg": veg_count,
        "non_veg": non_veg_count,
        "details": meals
    }

@router.post("/menu", response_model=DailyMenu)
async def create_daily_menu(
    menu: DailyMenuCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Create or update daily menu (Admin only)
    """
    if current_employee.role not in ["admin", "hr", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to manage menu")
    
    # Check if menu exists for date
    existing_menu = await DailyMenu.find_one(DailyMenu.date == menu.date)
    
    if existing_menu:
        existing_menu.options = menu.options
        existing_menu.updated_at = datetime.utcnow()
        await existing_menu.save()
        return existing_menu
    
    new_menu = DailyMenu(
        date=menu.date,
        options=menu.options
    )
    await new_menu.insert()
    return new_menu

@router.get("/menu/{date}", response_model=DailyMenu)
async def get_daily_menu(
    date: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Get daily menu for a specific date
    """
    menu = await DailyMenu.find_one(DailyMenu.date == date)
    if not menu:
        # Return empty default if not found, or 404
        raise HTTPException(status_code=404, detail="No menu available for this date")
    return menu

@router.post("/", response_model=Meal)
async def book_meal(
    request: MealCreate,
    current_employee: Employee = Depends(get_current_employee)
):
    """Book a meal"""
    # 0. Check if Menu exists and selection is valid
    menu = await DailyMenu.find_one(DailyMenu.date == request.booking_date)
    if not menu:
        raise HTTPException(
            status_code=400, 
            detail="Menu not yet decided for this date. Please contact admin."
        )
    
    # We treat 'items' or 'category' as the selection. 
    # Let's assume the user selects one of the options and sends it as 'items' or 'category'
    # For now, let's assume 'items' holds the selected option name from the list.
    if request.items not in menu.options:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid selection. Available options: {', '.join(menu.options)}"
        )

    # Check if already booked OR CONSUMED for same date and type
    # We block re-booking if status is 'booked' or 'consumed'
    existing = await Meal.find_one(
        Meal.employee_id == current_employee.employee_id,
        Meal.booking_date == request.booking_date,
        Meal.meal_type == request.meal_type,
        {"status": {"$in": ["booked", "consumed"]}}
    )
    
    if existing:
        status_msg = existing.status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have already {status_msg} a meal for {request.booking_date}"
        )

    # Validate Date
    try:
        booking_dt = datetime.strptime(request.booking_date, "%Y-%m-%d")
    except ValueError:
         raise HTTPException(status_code=400, detail="Invalid date format")

    # 1. Check for Weekend
    if booking_dt.weekday() >= 5: # 5=Sat, 6=Sun
        raise HTTPException(status_code=400, detail="Cannot book meals on weekends")

    # 2. Check for Holiday
    # Checking range to cover the day regardless of time
    next_day = booking_dt + timedelta(days=1)
    holiday = await Holiday.find_one(
        Holiday.date >= booking_dt,
        Holiday.date < next_day
    )
    if holiday:
        raise HTTPException(status_code=400, detail=f"Cannot book meal on holiday: {holiday.name}")

    # 3. Check for Leave
    leave = await Leave.find_one(
        Leave.employee_id == current_employee.employee_id,
        Leave.status == LeaveStatus.APPROVED,
        Leave.start_date <= booking_dt,
        Leave.end_date >= booking_dt
    )
    if leave:
        raise HTTPException(status_code=400, detail="Cannot book meal while on leave")

    meal = Meal(
        employee_id=current_employee.employee_id,
        employee_name=f"{current_employee.first_name} {current_employee.last_name}",
        booking_date=request.booking_date,
        meal_type=request.meal_type,
        category=request.category, # Keep as is, or infer from selection
        items=request.items,
        special_request=request.special_request,
        status="booked"
    )
    await meal.insert()

    # Notify Admins
    admins = await Employee.find(Employee.role == "admin").to_list()
    for admin in admins:
        notification = Notification(
            recipient_id=admin.employee_id,
            recipient_email=admin.email,
            title="New Meal Booking",
            message=f"{current_employee.first_name} booked {request.items} for {request.booking_date}",
            type="general",
            link="/admin"
        )
        await notification.insert()

    return meal

@router.get("/my", response_model=List[Meal])
async def get_my_meals(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_employee: Employee = Depends(get_current_employee)
):
    """Get current employee's meal bookings"""
    query = {
        "employee_id": current_employee.employee_id,
        "status": {"$ne": "cancelled"}
    }
    
    if start_date and end_date:
        query["booking_date"] = {"$gte": start_date, "$lte": end_date}
        
    return await Meal.find(query).sort("-booking_date").to_list()

@router.get("/all", response_model=List[Meal])
async def get_all_meals(
    date: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Get all meals for a specific date (Admin/Canteen)"""
    if current_employee.role not in ["admin", "hr", "manager"]:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    return await Meal.find(
        Meal.booking_date == date,
        Meal.status == "booked"
    ).to_list()

@router.delete("/{meal_id}")
async def cancel_meal(
    meal_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    """Cancel a meal booking"""
    meal = await Meal.get(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal booking not found")
        
    if meal.employee_id != current_employee.employee_id and current_employee.role not in ["admin", "hr"]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
        
    meal.status = "cancelled"
    meal.updated_at = datetime.utcnow()
    await meal.save()
    
    return {"message": "Meal booking cancelled"}

class MealScanRequest(BaseModel):
    meal_id: str

@router.post("/scan")
async def scan_meal(
    request: MealScanRequest,
    current_employee: Employee = Depends(get_current_employee)
):
    """Scan and redeem a meal (Admin only)"""
    if current_employee.role not in ["admin", "hr", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to scan meals")

    try:
        meal = await Meal.get(request.meal_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid meal ID format")
        
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
        
    if meal.status == "consumed":
        raise HTTPException(status_code=400, detail="Meal already scanned/consumed")
        
    if meal.status == "cancelled":
        raise HTTPException(status_code=400, detail="Meal was cancelled")

    if meal.status != "booked":
         raise HTTPException(status_code=400, detail=f"Invalid meal status: {meal.status}")

    # Verify date - Optional logic: ensure scanning only on the day of?
    # For now, allowing scanning anytime if booked.

    meal.status = "consumed"
    meal.updated_at = datetime.utcnow()
    await meal.save()

    return {"message": "Meal scanned successfully", "meal": meal}
