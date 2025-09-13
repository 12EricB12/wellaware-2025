import argparse
import os
from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Drop index(es) from the products collection to free space.")
    p.add_argument("--name", action="append", required=True, help="Index name to drop (repeatable)")
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

    for name in args.name:
        try:
            col.drop_index(name)
            print(f"dropped_index={name}")
        except Exception as exc:
            print(f"drop_failed name={name} error={exc}")


if __name__ == "__main__":
    main()


