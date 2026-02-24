from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_URL
import json
from bson import ObjectId

mongo = MongoCli(MONGO_URL)
db = mongo.appxusers
users = db.token_db

async def save_user_token(userid, token):
    await users.update_one(
        {"_id": str(userid)},
        {"$set": {"token": token}},
        upsert = True
    )

def serialize_doc(doc):
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def dump_database_to_json(filename="dump.json"):
    dbs = await mongo.list_database_names()
    full_dump = {}

    for db_name in dbs:
        if db_name in ("admin", "local", "config"):
            continue  # skip system dbs

        db = mongo[db_name]
        collections = await db.list_collection_names()

        full_dump[db_name] = {}

        for col in collections:
            collection = db[col]
            docs = await collection.find().to_list(length=None)
            full_dump[db_name][col] = [serialize_doc(doc) for doc in docs]

    with open(filename, "w") as f:
        json.dump(full_dump, f, indent=4)

    print(f"✅ Database dumped into {filename}")
