import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

async def check():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    emp_count = await db.employees.count_documents({})
    att_count = await db.attendance.count_documents({})
    print(f"COUNT_STATUS: Employees={emp_count}, Attendance={att_count}")

if __name__ == "__main__":
    asyncio.run(check())
