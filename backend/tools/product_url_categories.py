import argparse
import json
import os
from typing import Any, Dict, List

from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Counts docs with sources and categorizes by productUrl substrings.")
    p.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    p.add_argument("--collection", default="products", help="Collection name (default: products)")
    p.add_argument("--uri", default=os.environ.get("MONGODB_URI"), help="MongoDB URI (default: env MONGODB_URI)")
    p.add_argument(
        "--contains",
        default="openfoodfacts",
        help="Comma-separated substrings to categorize by (case-insensitive). Default: openfoodfacts",
    )
    p.add_argument("--limit", type=int, default=20, help="Top N domains to show (default: 20)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    substrings: List[str] = [s.strip().lower() for s in (args.contains or "").split(",") if s.strip()]
    client = MongoClient(args.uri)
    col = client[args.db][args.collection]

    match_stage: Dict[str, Any] = {"$match": {"sources": {"$exists": True}}}

    # Build projections for each substring
    add_fields: Dict[str, Any] = {"urlLower": {"$toLower": {"$ifNull": ["$productUrl", ""]}}}
    for idx, sub in enumerate(substrings):
        add_fields[f"m_{idx}"] = {"$regexMatch": {"input": "$urlLower", "regex": sub}}

    group_fields: Dict[str, Any] = {"_id": None, "total": {"$sum": 1}}
    sum_matches = []
    for idx, sub in enumerate(substrings):
        key = sub
        group_fields[key] = {"$sum": {"$cond": [f"$m_{idx}", 1, 0]}}
        sum_matches.append(f"${key}")

    pipeline_counts: List[Dict[str, Any]] = [
        match_stage,
        {"$addFields": add_fields},
        {"$group": group_fields},
    ]

    doc = next(iter(col.aggregate(pipeline_counts)), None)
    if not doc:
        doc = {"total": 0}
        for sub in substrings:
            doc[sub] = 0
    # Compute other = total - sum(matches)
    other = int(doc.get("total", 0)) - sum(int(doc.get(sub, 0)) for sub in substrings)
    doc["other"] = other

    # Domains breakdown
    pipeline_domains: List[Dict[str, Any]] = [
        match_stage,
        {"$set": {"m": {"$regexFind": {"input": {"$ifNull": ["$productUrl", ""]}, "regex": "^https?://([^/]+)"}}}},
        {"$project": {"domain": {"$ifNull": [{"$arrayElemAt": ["$m.captures", 0]}, "unknown"]}}},
        {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": args.limit},
        {"$project": {"_id": 0, "domain": "$_id", "count": 1}},
    ]
    domains: List[Dict[str, Any]] = list(col.aggregate(pipeline_domains))

    print(
        json.dumps(
            {
                "total_with_sources": int(doc.get("total", 0)),
                "by_substring": {sub: int(doc.get(sub, 0)) for sub in substrings} | {"other": other},
                "top_domains": domains,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


