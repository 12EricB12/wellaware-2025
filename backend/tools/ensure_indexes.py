import argparse
import os
from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ensure required indexes exist on products collection.")
    p.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    p.add_argument("--collection", default="products", help="Collection name (default: products)")
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"), help="MongoDB URI (default: env MONGODB_URI)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    client = MongoClient(args.uri)
    col = client[args.db][args.collection]

    col.create_index("details.upc", name="idx_details_upc")
    col.create_index([("source", 1), ("details.articleNumber", 1)], name="idx_source_articleNumber")
    print("indexes_ensured=true")


if __name__ == "__main__":
    main()


