import argparse
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.errors import ConfigurationError

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def get_mongo_client(connection_uri: str) -> MongoClient:
    """Create and return a MongoClient with a short server selection timeout."""
    return MongoClient(connection_uri, serverSelectionTimeoutMS=10000)


def get_database(client: MongoClient, db_name: str) -> Any:
    """Return a database handle.

    If db_name is provided, use it. Otherwise, try to derive the default database
    from the connection string; if not present, fall back to "wellaware".
    """
    if db_name:
        return client[db_name]
    try:
        return client.get_default_database()
    except ConfigurationError:
        return client["wellaware"]


def ensure_indexes(collection: Collection) -> None:
    """Create idempotent indexes required by the application."""
    # Multikey index for UPC lookups
    collection.create_index("details.upc", name="idx_details_upc")
    # Compound index for source + article number merges
    collection.create_index(
        [("source", 1), ("details.articleNumber", 1)],
        name="idx_source_articleNumber",
    )


def _normalize_to_string_list(value: Any) -> List[str]:
    """Normalize a value into a list[str], flattening one level and coercing items to str.

    - None -> []
    - str -> [str]
    - list/tuple -> [str(item) for item in value if item is not None]
    """
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, (list, tuple)):
        result: List[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                s = item.strip()
            else:
                s = str(item)
            if s:
                result.append(s)
        return result
    # Fallback: coerce to str
    s = str(value).strip()
    return [s] if s else []


def normalize_product_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single product document according to the canonical schema.

    Ensures:
    - details.upc is a list[str] (multikey), preserving leading zeros already present
    - category is a list[str]
    - details.ingredients is a list[str]
    - details.articleNumber exists as str if present
    - Removes any existing _id to avoid replacement conflicts
    """
    # Do not carry forward an _id coming from source files
    if "_id" in doc:
        doc.pop("_id", None)

    details = doc.get("details")
    if details is None or not isinstance(details, dict):
        details = {}
        doc["details"] = details

    # Normalize UPCs: keep strings as-is; coerce non-strings to strings
    upc_raw = details.get("upc")
    upc_list = _normalize_to_string_list(upc_raw)
    details["upc"] = upc_list

    # Normalize ingredients under details
    ingredients_raw = details.get("ingredients")
    details["ingredients"] = _normalize_to_string_list(ingredients_raw)

    # Normalize articleNumber to a string when present
    if "articleNumber" in details and details["articleNumber"] is not None:
        if not isinstance(details["articleNumber"], str):
            details["articleNumber"] = str(details["articleNumber"])

    # Normalize top-level arrays
    doc["category"] = _normalize_to_string_list(doc.get("category"))

    return doc


def apply_drop_fields(doc: Dict[str, Any], drop_fields: List[str]) -> None:
    """Remove specified dotted-path fields from the document in-place."""
    for path in drop_fields:
        parts = path.split(".")
        current: Any = doc
        for i, key in enumerate(parts):
            if not isinstance(current, dict) or key not in current:
                break
            if i == len(parts) - 1:
                current.pop(key, None)
            else:
                current = current.get(key)


def derive_upsert_filter(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Derive the upsert filter according to priority rules.

    Priority:
    1) { source, details.articleNumber } when articleNumber exists
    2) { details.upc: first_upc }
    3) { productUrl }
    Returns None if no rule can be applied.
    """
    source = doc.get("source")
    details = doc.get("details") or {}
    article_number = details.get("articleNumber")
    upcs: List[str] = details.get("upc") or []

    if source and article_number:
        return {"source": source, "details.articleNumber": article_number}

    if isinstance(upcs, list) and upcs:
        first_upc = upcs[0]
        if first_upc:
            return {"details.upc": first_upc}

    product_url = doc.get("productUrl")
    if product_url:
        return {"productUrl": product_url}

    return None


def iter_jsonl_records(path: Path) -> Iterable[Dict[str, Any]]:
    """Yield JSON objects from a .jsonl or .jsonl.gz file, one per line."""
    open_func = gzip.open if path.suffix == ".gz" or str(path).endswith(".jsonl.gz") else open
    mode = "rt"
    with open_func(path, mode, encoding="utf-8", errors="ignore") as f:  # type: ignore[arg-type]
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def collect_input_files(data_dir: Path) -> List[Path]:
    """Return all .jsonl and .jsonl.gz files under data_dir recursively."""
    files: List[Path] = []
    files.extend(sorted(data_dir.rglob("*.jsonl")))
    files.extend(sorted(data_dir.rglob("*.jsonl.gz")))
    return files


def process_files(
    files: List[Path],
    collection: Collection,
    batch_size: int,
    progress_every: int,
    drop_fields: List[str],
    prefer_sources: List[str],
) -> Tuple[int, int, int, int]:
    """Process input files and perform unordered bulk upserts.

    Returns a tuple: (processed_docs, upserted_count, modified_count, skipped_count)
    """
    operations: List[ReplaceOne] = []
    processed_docs = 0
    upserted_total = 0
    modified_total = 0
    skipped_total = 0

    def flush_ops() -> Tuple[int, int]:
        nonlocal operations
        if not operations:
            return 0, 0
        result = collection.bulk_write(operations, ordered=False)
        upserted = result.upserted_count or 0
        modified = result.modified_count or 0
        operations = []
        # Progress after each flush
        if progress_every and processed_docs % progress_every != 0:
            try:
                print(
                    json.dumps(
                        {
                            "progress": processed_docs,
                            "upserted_so_far": upserted_total + upserted,
                            "modified_so_far": modified_total + modified,
                            "skipped_so_far": skipped_total,
                            "status": "flushed",
                        }
                    ),
                    flush=True,
                )
            except Exception:
                pass
        return upserted, modified

    for file_path in files:
        for raw_doc in iter_jsonl_records(file_path):
            doc = normalize_product_document(raw_doc)
            if drop_fields:
                apply_drop_fields(doc, drop_fields)
            filt = derive_upsert_filter(doc)
            if not filt:
                skipped_total += 1
                continue

            # If prefer_sources provided, avoid overwriting a preferred source with a non-preferred one
            if prefer_sources:
                existing = collection.find_one(filt, projection={"source": 1})
                if existing and existing.get("source") in prefer_sources and doc.get("source") not in prefer_sources:
                    skipped_total += 1
                    continue

            operations.append(ReplaceOne(filt, doc, upsert=True))
            processed_docs += 1

            if len(operations) >= batch_size:
                up, mod = flush_ops()
                upserted_total += up
                modified_total += mod
            # Periodic progress
            if progress_every and processed_docs % progress_every == 0:
                try:
                    print(
                        json.dumps(
                            {
                                "progress": processed_docs,
                                "upserted_so_far": upserted_total,
                                "modified_so_far": modified_total,
                                "skipped_so_far": skipped_total,
                                "status": "in_progress",
                            }
                        ),
                        flush=True,
                    )
                except Exception:
                    pass

    # Flush remaining operations
    up, mod = flush_ops()
    upserted_total += up
    modified_total += mod

    return processed_docs, upserted_total, modified_total, skipped_total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load product JSONL data into MongoDB with upserts.")
    parser.add_argument("--data-dir", required=True, help="Directory containing .jsonl/.jsonl.gz files (recursive)")
    parser.add_argument("--db", default="wellaware", help="Database name (default: wellaware)")
    parser.add_argument("--collection", default="products", help="Collection name (default: products)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Bulk upsert batch size (default: 1000)")
    parser.add_argument(
        "--uri",
        default=os.environ.get("MONGODB_URI"),
        help="MongoDB connection URI (default: env MONGODB_URI)",
    )
    parser.add_argument(
        "--drop-field",
        action="append",
        default=[],
        help="Field to drop from documents during ingest (dotted path). May be repeated.",
    )
    parser.add_argument(
        "--prefer-sources",
        default=os.environ.get("PREFERRED_SOURCES", ""),
        help="Comma-separated list of preferred sources; prefer these when resolving conflicts.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=5000,
        help="Print JSON progress every N processed records (0 to disable). Default: 5000",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.uri:
        raise SystemExit("MONGODB_URI not provided. Use --uri or set env var MONGODB_URI.")

    data_dir = Path(args.data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"Data directory not found or not a directory: {data_dir}")

    files = collect_input_files(data_dir)
    if not files:
        raise SystemExit(f"No .jsonl or .jsonl.gz files found under {data_dir}")

    client = get_mongo_client(args.uri)
    db = get_database(client, args.db)
    collection: Collection = db[args.collection]

    # Ensure indexes before loading so lookups work immediately
    ensure_indexes(collection)

    prefer_sources: List[str] = [s.strip() for s in (args.prefer_sources or "").split(",") if s.strip()]

    processed_docs, upserted_total, modified_total, skipped_total = process_files(
        files,
        collection,
        args.batch_size,
        args.progress_every,
        args.drop_field,
        prefer_sources,
    )

    # Ensure indexes again in case collection was new
    ensure_indexes(collection)

    print(
        json.dumps(
            {
                "processed": processed_docs,
                "upserted": upserted_total,
                "modified": modified_total,
                "skipped": skipped_total,
                "collection": args.collection,
                "database": db.name,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()


