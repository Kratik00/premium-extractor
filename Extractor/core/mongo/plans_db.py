from datetime import datetime, timezone
from config import MONGO_URL
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli

mongo = MongoCli(MONGO_URL)
db = mongo.premium.premium_db


# ---------------- ADD / REMOVE ---------------- #

async def add_premium(user_id: int, expire_date: datetime):
    await db.update_one(
        {"_id": user_id},
        {"$set": {"expire_date": expire_date}},
        upsert=True
    )


async def remove_premium(user_id: int):
    await db.delete_one({"_id": user_id})


# ---------------- CHECK ---------------- #

async def check_premium(user_id: int):
    return await db.find_one({"_id": user_id})


async def is_premium(user_id: int) -> bool:
    data = await db.find_one({"_id": user_id})
    if not data:
        return False

    return data["expire_date"] > datetime.now(timezone.utc)


# ---------------- CLEANUP ---------------- #

async def clean_expired_premium():
    await db.delete_many({
        "expire_date": {"$lt": datetime.now(timezone.utc)}
    })


# ---------------- LIST ---------------- #

async def premium_users():
    return [u["_id"] async for u in db.find({}, {"_id": 1})]
