import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "hackathon_db")

client = AsyncIOMotorClient(MONGODB_URL) if MONGODB_URL else None
database = client[DATABASE_NAME] if client else None


async def close_database():
    if client:
        client.close()
