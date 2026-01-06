"""
Main FastAPI Application
Entry point for the backend server
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.holiday import Holiday
from app.models.notification import Notification
from app.models.announcement import Announcement
from app.models.payslip import Payslip
from app.models.request import Request
from app.models.meal import Meal, DailyMenu
from app.models.company import CompanySettings

# Import routers
from app.api.routes import auth, employees, attendance, leaves, chatbot, dashboard, holidays, notifications, announcements, payroll, requests, meals, company

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Enterprise Attendance System...")
    
    # Initialize MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.MONGODB_DB_NAME]
    
    # Initialize Beanie with document models
    await init_beanie(
        database=database,
        document_models=[Employee, Attendance, Leave, Holiday, Notification, Announcement, Payslip, Request, Meal, DailyMenu, CompanySettings]
    )
    
    print(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    
    # Auto-create first admin if DB is empty
    admin_count = await Employee.find(Employee.role == "admin").count()
    if admin_count == 0:
        print("🆕 No admin users found. Creating default admin...")
        from app.api.routes.auth import get_password_hash
        
        # Import models needed for nested fields
        from app.models.employee import Address, EmergencyContact
        
        admin = Employee(
            employee_id="ADMIN001",
            first_name="System",
            last_name="Admin",
            email="admin@company.com",
            phone="+91-0000000000",
            date_of_birth=datetime(1990, 1, 1),
            gender="Other",
            password_hash=get_password_hash("admin123"),
            department="Management",
            designation="Administrator",
            role="admin",
            is_active=True,
            joining_date=datetime.utcnow(),
            address=Address(
                street="123 Admin Lane",
                city="System City",
                state="Digital",
                postal_code="000000",
                country="India"
            ),
            emergency_contact=EmergencyContact(
                name="Guardian",
                relationship="System",
                phone="+91-0000000000"
            ),
            casual_leave_balance=12,
            sick_leave_balance=10,
            annual_leave_balance=20
        )
        await admin.insert()
        print("✅ Default admin created (admin@company.com / admin123)")
    
    print(f"✅ Server running on {settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")
    client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade attendance management system with AI chatbot",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(leaves.router, prefix="/api/leaves", tags=["Leaves"])
app.include_router(requests.router, prefix="/api/requests", tags=["Requests"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["AI Chatbot"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(holidays.router, prefix="/api/holidays", tags=["Holidays"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["Announcements"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(meals.router, prefix="/api/meals", tags=["Meals"])
app.include_router(company.router, prefix="/api/company", tags=["Company Settings"])

# Mount static files (for uploads)
import os
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Enterprise Attendance Management System API",
        "version": settings.APP_VERSION,
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2026-01-03T00:26:02+05:30"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
