import os
import json
from pymongo import MongoClient


def main() -> None:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise SystemExit("MONGODB_URI not set")
    client = MongoClient(uri)
    db = client.get_default_database()
    if db is None:
        db = client["wellaware"]
    doc = db["products"].find_one(
        {"details.upc": {"$exists": True, "$ne": []}},
        {"_id": 0, "details.upc": 1, "productName": 1},
    )
    print(json.dumps(doc, ensure_ascii=False))


if __name__ == "__main__":
    main()


