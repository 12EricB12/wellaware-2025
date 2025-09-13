from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["obf"]

# Example: remove all fields except some
def keep_only_fields(collection, fields_to_keep):
    sample_doc = collection.find_one()
    if not sample_doc:
        print("No documents found.")
        return

    all_fields = set(sample_doc.keys())
    fields_to_remove = all_fields - set(fields_to_keep) - {"_id"}
    
    if fields_to_remove:
        unset_fields = {field: "" for field in fields_to_remove}
        result = collection.update_many({}, {"$unset": unset_fields})
        print(f"Removed fields from {result.modified_count} documents.")
    else:
        print("No fields to remove.")

print(db.products.find_one())
