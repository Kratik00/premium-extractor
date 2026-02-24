from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_URL

mongo = MongoCli(MONGO_URL)
db = mongo.appxusers
users = db.token_db

async def save_user_token(userid, token):
    await users.update_one(
        {"_id": str(userid)},
        {"$set": {"token": token}},
        upsert = True
    )


