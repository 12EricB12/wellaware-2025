import argparse
import json
import os
from typing import Any, Dict, List

from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Delete documents where specific field(s) exist, in chunks.")
    p.add_argument("--exists", action="append", required=True, help="Field to check with $exists: true (repeatable)")
    p.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    p.add_argument("--collection", default="products", help="Collection name (default: products)")
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"), help="MongoDB URI (default: env MONGODB_URI)")
    p.add_argument("--batch-size", type=int, default=5000, help="Delete batch size (default: 5000)")
    p.add_argument("--dry-run", action="store_true", help="Only count matches; do not delete.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    client = MongoClient(args.uri)
    col = client[args.db][args.collection]

    filter_query: Dict[str, Any] = {"$or": [{f: {"$exists": True}} for f in args.exists]}

    total_matches = col.count_documents(filter_query)
    if args.dry_run:
        print(json.dumps({"matched": total_matches, "deleted": 0, "dry_run": True}))
        return

    deleted_total = 0
    ids: List[Any] = []
    cursor = col.find(filter_query, projection={"_id": 1}, batch_size=1000)
    for doc in cursor:
        ids.append(doc["_id"])
        if len(ids) >= args.batch_size:
            res = col.delete_many({"_id": {"$in": ids}})
            deleted_total += res.deleted_count or 0
            print(json.dumps({"deleted_so_far": deleted_total, "progress": True}), flush=True)
            ids = []

    if ids:
        res = col.delete_many({"_id": {"$in": ids}})
        deleted_total += res.deleted_count or 0

    print(json.dumps({"matched": total_matches, "deleted": deleted_total, "dry_run": False}))


if __name__ == "__main__":
    main()


