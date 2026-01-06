import asyncio
from datetime import datetime, timedelta
import random
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.employee import Employee, Address, EmergencyContact
from app.models.attendance import Attendance, AttendanceStatus, AttendanceType
from app.models.leave import Leave
from app.models.holiday import Holiday, HolidayType
from app.api.routes.auth import get_password_hash

async def create_sample_data():
    """Populate database with sample employees and attendance records"""
    print("🚀 Starting Sample Data Generation...")
    
    # Initialize Beanie
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[Employee, Attendance, Leave, Holiday]
    )
    
    # Sample Departments and Designations
    depts = ["Engineering", "Product", "Sales", "HR", "Marketing"]
    designations = {
        "Engineering": ["Senior Developer", "Frontend Lead", "DevOps Engineer", "QA Manager"],
        "Product": ["Product Manager", "UX Designer", "Product Owner"],
        "Sales": ["Account Executive", "Sales Manager", "Business Development"],
        "HR": ["HR Manager", "Talent Acquisition", "People Ops"],
        "Marketing": ["Marketing Lead", "SEO Specialist", "Content Writer"]
    }
    
    # Create 8-10 Sample Employees
    names = [
        ("Alice", "Smith"), ("Bob", "Johnson"), ("Charlie", "Davis"), 
        ("Diana", "Prince"), ("Ethan", "Hunt"), ("Fiona", "Gallagher"),
        ("George", "Miller"), ("Hannah", "Baker"), ("Ian", "Somerhalder")
    ]
    
    password_hash = get_password_hash("Employee123!")
    
    employees = []
    for i, (first, last) in enumerate(names):
        emp_id = f"EMP{100 + i}"
        email = f"{first.lower()}.{last.lower()}@company.com"
        dept = random.choice(depts)
        
        # Check if already exists
        existing = await Employee.find_one(Employee.employee_id == emp_id)
        if existing:
            print(f"⏩ {emp_id} already exists, skipping...")
            employees.append(existing)
            continue
            
        emp = Employee(
            employee_id=emp_id,
            first_name=first,
            last_name=last,
            email=email,
            phone=f"+91-9876543{i:03d}",
            date_of_birth=datetime(1990 + random.randint(0, 10), random.randint(1, 12), random.randint(1, 28)),
            gender=random.choice(["Male", "Female"]),
            department=dept,
            designation=random.choice(designations[dept]),
            role="employee",
            joining_date=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
            address=Address(street="Main St", city="Bangalore", state="Karnataka", postal_code="560001"),
            emergency_contact=EmergencyContact(name="Kinsfolk", relationship="Family", phone="9988776655"),
            password_hash=password_hash,
            shift_start_time="09:00",
            shift_end_time="18:00"
        )
        await emp.insert()
        employees.append(emp)
        print(f"✅ Created Employee: {first} {last} ({emp_id})")

    # Generate Attendance for the Last 14 Days
    print("📅 Generating Attendance History (14 Days)...")
    for emp in employees:
        for d in range(14):
            date = datetime.utcnow() - timedelta(days=d)
            # Skip Sundays
            if date.weekday() == 6:
                continue
                
            # Randomly skip some days to simulate absence
            if random.random() < 0.1:
                continue
                
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Simulate shift start 9:00
            # Some late arrivals (after 9:15)
            is_late = random.random() < 0.2
            if is_late:
                check_in = date.replace(hour=9, minute=random.randint(16, 45), second=random.randint(0, 59))
            else:
                check_in = date.replace(hour=8, minute=random.randint(45, 59), second=random.randint(0, 59))
            
            # Simulate shift end 18:00
            # Some early departures (before 17:30)
            is_early = random.random() < 0.1
            if is_early:
                check_out = date.replace(hour=16, minute=random.randint(30, 59), second=random.randint(0, 59))
            else:
                check_out = date.replace(hour=18, minute=random.randint(0, 30), second=random.randint(0, 59))
            
            time_diff = check_out - check_in
            total_hours = round(time_diff.total_seconds() / 3600, 2)
            
            attendance = Attendance(
                employee_id=emp.employee_id,
                employee_name=f"{emp.first_name} {emp.last_name}",
                department=emp.department,
                date=day_start,
                day_of_week=day_start.strftime("%A"),
                check_in_time=check_in,
                check_out_time=check_out,
                total_hours=total_hours,
                status=AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT,
                is_late=is_late,
                is_early_departure=is_early,
                check_in_type=AttendanceType.FINGERPRINT,
                check_out_type=AttendanceType.MANUAL
            )
            await attendance.insert()
            
    # Generate sample holidays
    print("🎊 Generating Holiday Calendar...")
    holidays = [
        {"name": "Republic Day", "date": datetime(2026, 1, 26), "type": HolidayType.PUBLIC},
        {"name": "Holi", "date": datetime(2026, 3, 14), "type": HolidayType.PUBLIC},
        {"name": "Good Friday", "date": datetime(2026, 4, 10), "type": HolidayType.PUBLIC},
        {"name": "Eid al-Fitr", "date": datetime(2026, 3, 20), "type": HolidayType.PUBLIC},
        {"name": "Labour Day", "date": datetime(2026, 5, 1), "type": HolidayType.PUBLIC},
        {"name": "Independence Day", "date": datetime(2026, 8, 15), "type": HolidayType.PUBLIC},
        {"name": "Gandhi Jayanti", "date": datetime(2026, 10, 2), "type": HolidayType.PUBLIC},
        {"name": "Diwali", "date": datetime(2026, 10, 24), "type": HolidayType.PUBLIC},
        {"name": "Christmas", "date": datetime(2026, 12, 25), "type": HolidayType.PUBLIC},
        {"name": "Founder's Day", "date": datetime(2026, 6, 15), "type": HolidayType.COMPANY},
    ]
    
    for h_data in holidays:
        existing_h = await Holiday.find_one(Holiday.name == h_data["name"])
        if not existing_h:
            holiday = Holiday(**h_data)
            await holiday.insert()
            
    print("✨ Sample Data Generation Complete!")

if __name__ == "__main__":
    asyncio.run(create_sample_data())
