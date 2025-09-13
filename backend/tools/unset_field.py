import argparse
import json
import os
from typing import Any, Dict, List, Optional

from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unset one or more fields across all matching documents.")
    p.add_argument("--field", action="append", required=True, help="Field to unset (dotted path). May be repeated.")
    p.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    p.add_argument("--collection", default="products", help="Collection name (default: products)")
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"), help="MongoDB URI (default: env MONGODB_URI)")
    p.add_argument("--source-in", dest="source_in", default=None, help="Comma-separated list of sources to restrict the update.")
    p.add_argument("--dry-run", action="store_true", help="Only count matching documents; do not modify.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    client = MongoClient(args.uri)
    db = client[args.db]
    col = db[args.collection]

    filter_query: Dict[str, Any] = {"$or": [{f: {"$exists": True}} for f in args.field]}
    if args.source_in:
        sources = [s.strip() for s in args.source_in.split(",") if s.strip()]
        if sources:
            filter_query["source"] = {"$in": sources}

    match_count = col.count_documents(filter_query)

    if args.dry_run:
        print(json.dumps({"matched": match_count, "modified": 0, "dry_run": True}))
        return

    unset_spec = {f: "" for f in args.field}
    res = col.update_many(filter_query, {"$unset": unset_spec})
    print(json.dumps({"matched": res.matched_count, "modified": res.modified_count, "dry_run": False}))


if __name__ == "__main__":
    main()


