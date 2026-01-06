import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

# Fix paths
sys.path.append(os.getcwd())
from app.config import settings
from app.models.employee import Employee

async def diagnose():
    print(f"🔍 Diagnostic start...")
    print(f"🌐 Target URL: {settings.MONGODB_URL[:30]}...")
    print(f"📦 Database: {settings.MONGODB_DB_NAME}")
    
    try:
        # Check connection with timeout
        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB Ping Successful!")
        
        database = client[settings.MONGODB_DB_NAME]
        await init_beanie(
            database=database,
            document_models=[Employee]
        )
        
        # Count employees
        count = await Employee.find().count()
        print(f"📊 Total employees in DB: {count}")
        
        if count > 0:
            all_emp = await Employee.find().to_list()
            print("👥 Employee emails found:")
            for emp in all_emp:
                print(f"   - {emp.email} (Role: {emp.role})")
        else:
            print("⚠️ No employees found in the database.")
            
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
        print("\nPossible reasons:")
        print("1. IP Whitelist: Ensure your current IP is allowed in MongoDB Atlas.")
        print("2. Credentials: Check if the username/password in the URL are correct.")
        print("3. Firewall: Your network might be blocking port 27017 or the Atlas connection.")

if __name__ == "__main__":
    asyncio.run(diagnose())
