import argparse
import json
import os
from typing import Any, Dict, List

from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="List sources by total size and count.")
    p.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    p.add_argument("--collection", default="products", help="Collection name (default: products)")
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"), help="MongoDB URI (default: env MONGODB_URI)")
    p.add_argument("--limit", type=int, default=20, help="Max rows per list (default: 20)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    client = MongoClient(args.uri)
    col = client[args.db][args.collection]

    pipeline = [
        {
            "$group": {
                "_id": "$source",
                "count": {"$sum": 1},
                "totalBytes": {"$sum": {"$bsonSize": "$$ROOT"}},
            }
        },
        {"$project": {"_id": 0, "source": "$_id", "count": 1, "totalBytes": 1}},
    ]

    rows: List[Dict[str, Any]] = list(col.aggregate(pipeline))
    # Compute derived fields
    for r in rows:
        tb = float(r.get("totalBytes", 0) or 0)
        cnt = int(r.get("count", 0) or 0)
        r["totalMB"] = round(tb / 1048576.0, 2)
        r["avgKB"] = round((tb / cnt) / 1024.0, 2) if cnt else 0.0

    by_size = sorted(rows, key=lambda x: x.get("totalBytes", 0), reverse=True)[: args.limit]
    by_count = sorted(rows, key=lambda x: x.get("count", 0), reverse=True)[: args.limit]

    print(
        json.dumps(
            {
                "by_size": by_size,
                "by_count": by_count,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


