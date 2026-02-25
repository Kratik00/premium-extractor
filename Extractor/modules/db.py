from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_URL
import json
from bson import ObjectId
from datetime import datetime

mongo = MongoCli(MONGO_URL)
db = mongo.appxusers
users = db.token_db


async def save_user_token(userid, token, api_base):
    await users.update_one(
        {"_id": str(userid)},   # filter
        {
            "$set": {
                "token": token,
                "api_base": api_base
            }
        },
        upsert=True
    )


# 🔥 universal converter (handles nested data too)
def convert_special_types(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [convert_special_types(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_special_types(v) for k, v in obj.items()}
    return obj


async def dump_database_to_json(filename="dump.json"):
    full_dump = {}

    database = mongo["appxusers"]
    collections = await database.list_collection_names()

    full_dump["appxusers"] = {}

    for col in collections:
        collection = database[col]
        docs = await collection.find().to_list(length=None)
        full_dump["appxusers"][col] = [convert_special_types(doc) for doc in docs]

    with open(filename, "w") as f:
        json.dump(full_dump, f, indent=4)

    print(f"✅ appxusers database dumped into {filename}")
