import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext
from datetime import datetime

# Import models
import sys
import os
sys.path.append(os.getcwd())
from app.config import settings
from app.models.employee import Employee, Address, EmergencyContact

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def create_admin():
    print("🚀 Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.MONGODB_DB_NAME]
    
    await init_beanie(
        database=database,
        document_models=[Employee]
    )
    
    # Check if admin already exists
    admin_email = "admin@company.com"
    existing_admin = await Employee.find_one(Employee.email == admin_email)
    
    if existing_admin:
        print(f"ℹ️ Admin user '{admin_email}' already exists.")
    else:
        print(f"🆕 Creating admin user: {admin_email}")
        admin = Employee(
            employee_id="ADMIN001",
            first_name="System",
            last_name="Admin",
            email=admin_email,
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
        print("✅ Admin user created successfully!")

if __name__ == "__main__":
    asyncio.run(create_admin())
