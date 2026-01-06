import asyncio
import sys
import os

# Add the current directory to sys.path so 'app' module can be found
sys.path.append(os.getcwd())

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
from app.models.meal import Meal
from app.ai.chatbot import chatbot_service

async def main():
    try:
        print(f"Connecting to DB at {settings.MONGODB_URL}...")
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        # Timeout to fail fast if DB is down
        await client.server_info()
        
        database = client[settings.MONGODB_DB_NAME]
        await init_beanie(
            database=database,
            document_models=[Employee, Attendance, Leave, Holiday, Notification, Announcement, Payslip, Request, Meal] 
        )
        print("Connected to DB.")

        print("Testing Chatbot with ADMIN001...")
        # We need to ensure ADMIN001 exists or use an existing one
        admin = await Employee.find_one(Employee.employee_id == "ADMIN001")
        if not admin:
            # Create a dummy one if needed, or just fail
            print("ADMIN001 not found, trying to find any employee...")
            admin = await Employee.find_one({})
            if not admin:
                print("No employees found in DB.")
                return
        
        print(f"Using employee: {admin.employee_id}")

        response = await chatbot_service.get_response(
            query="Hello",
            employee_id=admin.employee_id, 
            context={}
        )
        print("Response:", response)

    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
