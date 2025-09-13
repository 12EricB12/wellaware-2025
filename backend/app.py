import os
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConfigurationError

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def get_mongo_client(connection_uri: str) -> MongoClient:
    return MongoClient(connection_uri, serverSelectionTimeoutMS=10000)


def get_database(client: MongoClient, desired_db_name: Optional[str]) -> Any:
    if desired_db_name:
        return client[desired_db_name]
    try:
        db = client.get_default_database()
        if db is not None:
            return db
    except ConfigurationError:
        pass
    return client["wellaware"]


def ensure_indexes(collection: Collection) -> None:
    collection.create_index("details.upc", name="idx_details_upc")
    collection.create_index(
        [("source", 1), ("details.articleNumber", 1)],
        name="idx_source_articleNumber",
    )


def parse_preferred_sources() -> List[str]:
    raw = os.environ.get("PREFERRED_SOURCES", "")
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def init_db(app: FastAPI) -> None:
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError("MONGODB_URI environment variable is required")

    client = get_mongo_client(mongo_uri)

    # Derive DB name from URI if present; otherwise default to wellaware
    db = get_database(client, None)

    products: Collection = db["products"]

    # Ensure required indexes and ping
    ensure_indexes(products)
    client.admin.command("ping")

    app.state.mongo_client = client
    app.state.db = db
    app.state.products = products
    app.state.preferred_sources = parse_preferred_sources()


app = FastAPI(title="WellAware API", version="0.1.0")

# Allow GET requests from all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)


@app.on_event("startup")
def on_startup() -> None:
    init_db(app)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/products/upc/{upc_code}")
def get_product_by_upc(upc_code: str) -> Dict[str, Any]:
    products: Collection = app.state.products
    preferred: List[str] = getattr(app.state, "preferred_sources", [])

    if not preferred:
        # Simple fast path
        doc = products.find_one({"details.upc": upc_code}, projection={"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return jsonable_encoder(doc)

    pipeline = [
        {"$match": {"details.upc": upc_code}},
        {
            "$addFields": {
                "__rank": {
                    "$indexOfArray": [preferred, "$source"],
                }
            }
        },
        {
            "$addFields": {
                "__rank": {"$cond": [{"$eq": ["$__rank", -1]}, 9999, "$__rank"]}
            }
        },
        {"$sort": {"__rank": 1, "scrapedAt": -1}},
        {"$limit": 1},
        {"$project": {"_id": 0, "__rank": 0}},
    ]

    results = list(products.aggregate(pipeline))
    if not results:
        raise HTTPException(status_code=404, detail="Product not found")
    return jsonable_encoder(results[0])


