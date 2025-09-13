## WellAware backend (dev)

### Prereqs
- Python 3.9+
- MongoDB Atlas cluster (dev): `wellaware-dev-m0`
- A connection string in env `MONGODB_URI` (SRV; include default db path `/wellaware`)

Example (redacted):
```
export MONGODB_URI="mongodb+srv://wa-app-dev:<password>@wellaware-dev-m0.<hash>.mongodb.net/wellaware?retryWrites=true&w=majority&appName=wellaware-dev-m0"
```
On Windows PowerShell:
```
$Env:MONGODB_URI="..."
```

Alternatively, create a `.env` file in the repo root or `backend/` and add:
```
MONGODB_URI=mongodb+srv://wa-app-dev:<password>@<host>.mongodb.net/wellaware?retryWrites=true&w=majority&appName=wellaware-dev-m0
```
Both the loader and API will read it automatically.

### Install
```bash
python -m pip install -r backend/requirements.txt
```

Or minimal:
```bash
python -m pip install "pymongo[srv]" fastapi "uvicorn[standard]" python-dotenv
```

### Data loader
Loads `.jsonl` and `.jsonl.gz` recursively and upserts into MongoDB.

Normalization:
- `details.upc`: array of strings (leading zeros preserved)
- `category`, `details.ingredients`: arrays of strings

Upsert key priority:
1. `{ source, "details.articleNumber" }` if `articleNumber` exists
2. First UPC in `details.upc`
3. `productUrl`

Indexes (idempotent):
- `details.upc` (multikey)
- Compound `{ source: 1, "details.articleNumber": 1 }`

Run:
```bash
python backend/load_data.py --data-dir /path/to/jsonl \
  --db wellaware --collection products --batch-size 1000 \
  --progress-every 5000 \
  --drop-field details.description \
  --prefer-sources "Open Beauty API,Open Food Facts API"
```

Windows note: if `python` is not recognized, use `py.exe` instead.

Flags:
- `--data-dir` (required)
- `--db` default `wellaware`
- `--collection` default `products`
- `--batch-size` default `1000`
- `--uri` defaults to env `MONGODB_URI`
- `--progress-every` default `5000`; set to `0` to disable periodic progress logs
- `--drop-field` repeatable; removes dotted-path fields at ingest (e.g., `details.description`)
- `--prefer-sources` comma-separated list; avoids overwriting preferred sources with non-preferred during ingest

Source precedence (ingest):
- If `--prefer-sources` is set and an existing document matches the upsert key with a preferred `source`, a new non-preferred document will NOT overwrite it.
- If the incoming document's `source` is preferred and the existing one is not, the loader will overwrite the existing document (normal upsert replace).

Example:
```bash
python backend/load_data.py --data-dir ./data
```

Progress output example (periodic):
```json
{"progress": 5000, "upserted_so_far": 4800, "modified_so_far": 150, "skipped_so_far": 50, "status": "in_progress"}
```
Final summary:
```json
{"processed":1234,"upserted":1200,"modified":30,"skipped":4,"collection":"products","database":"wellaware"}
```

### API (FastAPI)
Endpoints:
- `GET /health` → `{ "status": "ok" }`
- `GET /api/products/upc/{upc}` → full product JSON (no `_id`); `404` if not found

Startup:
- Reads `MONGODB_URI`; derives default DB or falls back to `wellaware`
- Ensures indexes; pings DB
- CORS: allow `GET` from all origins (dev)

Run:
```bash
uvicorn backend.app:app --reload --port 8000
```

Test:
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/products/upc/012345678912
```

Prefer sources at query time (API):
```bash
# Highest priority first
$Env:PREFERRED_SOURCES="Open Beauty API,Open Food Facts API"
uvicorn backend.app:app --reload --port 8000
```
When set, the UPC endpoint returns the best match based on preferred source order and most-recent `scrapedAt`.

Source precedence (API):
- Sorts by preferred `source` order first, then by `scrapedAt` descending.

### Get a sample UPC quickly
```bash
python backend/tools/sample_upc.py
```
Copy the `details.upc[0]` value and query via the API.

### Verify indexes exist
```bash
python -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database() or c['wellaware']; print([i['name'] for i in db['products'].list_indexes()])"
```
Expected: `['_id_', 'idx_details_upc', 'idx_source_articleNumber']`

### DB inspection & storage usage
- DB stats (PowerShell):
```powershell
py.exe -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database(); db = db if db is not None else c['wellaware']; print(db.command('dbStats'))"
```

- Collection stats (PowerShell):
```powershell
py.exe -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database(); db = db if db is not None else c['wellaware']; print(db.command({'collStats':'products'}))"
```
Explains counts and sizes for `products` (logical BSON size vs on-disk storage with compression, index sizes, avg object size).

- List indexes (PowerShell):
```powershell
py.exe -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database(); db = db if db is not None else c['wellaware']; print([i['name'] for i in db['products'].list_indexes()])"
```

- Count docs containing a field:
```powershell
py.exe -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database(); db = db if db is not None else c['wellaware']; print(db['products'].count_documents({'details.description': {'$exists': True}}))"
```

- Count docs where `sources` exists:
```powershell
py.exe -c "import os; from pymongo import MongoClient; c=MongoClient(os.environ['MONGODB_URI']); db=c.get_default_database(); db = db if db is not None else c['wellaware']; print(db['products'].count_documents({'sources': {'$exists': True}}))"
```

- Group remaining docs by source (PowerShell quoting tip: prefer single quotes for `-c` to avoid `$` expansion):
```powershell
py.exe -c 'import os; from pymongo import MongoClient; c=MongoClient(os.environ["MONGODB_URI"]); db=c.get_default_database(); db = db if db is not None else c["wellaware"]; print(list(db["products"].aggregate([{"$match":{"details.description":{"$exists":True}}},{"$group":{"_id":"$source","n":{"$sum":1}}},{"$sort":{"n":-1}},{"$limit":10}])))'
```

### Troubleshooting
- If DNS/SRV issues occur on your network, use Atlas’s non-SRV URI variant.
- Ensure your IP is allowlisted in Atlas.
- URL-encode special characters in the password.
- Dropping indexes does not delete data. On M0, indexes count against the 512 MB quota; drop large indexes temporarily to free space, perform cleanup, then recreate them.

### Source breakdown (size and count)
Summarize sources by total data size and by document count:
```powershell
py.exe backend/tools/source_sizes.py --limit 20
```
Returns JSON with `by_size` and `by_count` arrays including `source`, `count`, `totalMB`, and `avgKB`.

### Categorize by productUrl substrings
Among docs where `sources` exists, count matches for substrings (case-insensitive) and show top domains:
```powershell
py.exe backend/tools/product_url_categories.py --contains openfoodfacts,openbeauty --limit 15
```
Output includes `total_with_sources`, `by_substring` counts, and `top_domains`.

### Cleanup utility (unset fields)
Drop space-heavy fields (e.g., description) across all docs or selected sources to save M0 space:
```bash
python backend/tools/unset_field.py --field details.description --dry-run
python backend/tools/unset_field.py --field details.description
```
Restrict to sources:
```bash
python backend/tools/unset_field.py --field details.description --source-in "Open Beauty API,Open Food Facts API"
```

Dry run:
- `--dry-run` performs no changes; it only counts how many documents match the filter so you can validate impact before applying.

M0 quota tip:
- Use the cleanup utility to remove large, non-essential fields (e.g., `details.description`).
- Re-run the loader with `--drop-field details.description` to keep future ingests lean.

### Delete docs where a field exists (dangerous)
Delete whole documents in chunks where a field exists (e.g., `sources`). Dry-run first:
```powershell
py.exe backend/tools/delete_by_exists.py --exists sources --dry-run
py.exe backend/tools/delete_by_exists.py --exists sources --batch-size 5000
```
If on M0 and near quota, free space temporarily by dropping indexes, then restore:
```powershell
py.exe backend/tools/drop_index.py --name idx_details_upc --name idx_source_articleNumber
py.exe backend/tools/ensure_indexes.py
```

What does --dry-run do?
- It simulates only. No documents are modified; it just counts how many would be affected.
- Example output:
```json
{"matched": 53210, "modified": 0, "dry_run": true}
```
- When you remove --dry-run, it applies the update and prints something like:
```json
{"matched": 53210, "modified": 51980, "dry_run": false}
```

### Acceptance checklist
- Loader is idempotent and upserts
- Indexes exist: `details.upc`, `{source, details.articleNumber}`
- UPC lookup returns quickly (uses index)
- Health check ok; 404s handled cleanly

# WellAware Backend API

A comprehensive food data API that integrates multiple data sources including USDA FoodData Central and Open Food Facts.

## Features

### 🔗 **Multi-Source API Integration**
- **USDA FoodData Central**: Government nutritional database
- **Open Food Facts**: Community-driven food database
- **Combined Search**: Search across both databases simultaneously

### 🕷️ **Data Scraping**
- **Automated Scraping**: Collect large datasets from Open Food Facts
- **Scheduled Updates**: Keep data fresh with periodic scraping
- **Data Validation**: Ensure quality and completeness

### 📊 **Data Management**
- **Centralized Storage**: JSON-based data storage
- **Metadata Tracking**: Track scraping sessions and data quality
- **API Access**: RESTful endpoints for all data sources

## Installation

### Prerequisites
- Node.js (v14 or higher)
- Python 3.x
- npm or yarn

### Setup
1. **Install Node.js Dependencies**:
   ```bash
   npm install
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Server**:
   ```bash
   node server.js
   ```

## API Endpoints

### 🏠 **Base URL**: `http://localhost:3000`

### 🔍 **Search Endpoints**

#### Get API Information
```
GET /
```
Returns API overview and available endpoints.

#### Search USDA Database
```
GET /api/food/usda?q=query
```
Search the USDA FoodData Central database.

**Parameters:**
- `q` (required): Search query

**Example:**
```bash
curl "http://localhost:3000/api/food/usda?q=apple"
```

#### Search Open Food Facts
```
GET /api/food/openfoodfacts?q=query
```
Search the Open Food Facts database.

**Parameters:**
- `q` (required): Search query

**Example:**
```bash
curl "http://localhost:3000/api/food/openfoodfacts?q=coca%20cola"
```

#### Combined Search
```
GET /api/food/search?q=query&sources=usda,openfoodfacts
```
Search both databases simultaneously.

**Parameters:**
- `q` (required): Search query
- `sources` (optional): Comma-separated list of sources (default: "usda,openfoodfacts")

**Example:**
```bash
curl "http://localhost:3000/api/food/search?q=banana&sources=usda,openfoodfacts"
```

### 🕷️ **Scraper Endpoints**

#### Run Scraper
```
POST /api/scraper/run
```
Execute the Open Food Facts scraper.

**Body:**
```json
{
  "max_pages": 10
}
```

**Example:**
```bash
curl -X POST "http://localhost:3000/api/scraper/run" \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 5}'
```

#### Get Scraper Status
```
GET /api/scraper/status
```
Get scraper status, logs, and last run information.

**Example:**
```bash
curl "http://localhost:3000/api/scraper/status"
```

### 📊 **Data Endpoints**

#### Get Latest Scraped Data
```
GET /api/data/latest
```
Retrieve the most recent scraped data with preview.

**Example:**
```bash
curl "http://localhost:3000/api/data/latest"
```

## Data Sources

### 🏛️ **USDA FoodData Central**
- **Official government database**
- **Comprehensive nutritional data**
- **Standardized food descriptions**
- **Laboratory-tested values**

### 🌍 **Open Food Facts**
- **Community-driven database**
- **Global product coverage**
- **Barcode integration**
- **Ingredient lists and allergen information**

## Data Structure

### USDA Response Format
```json
{
  "source": "USDA",
  "query": "apple",
  "data": {
    "foods": [
      {
        "fdcId": 123456,
        "description": "Apple, raw",
        "foodNutrients": [...]
      }
    ]
  }
}
```

### Open Food Facts Response Format
```json
{
  "source": "Open Food Facts",
  "query": "coca cola",
  "count": 50,
  "products": [
    {
      "code": "123456789",
      "product_name": "Coca-Cola",
      "brands": "Coca-Cola",
      "categories": "Carbonated drinks",
      "nutriments": {...},
      "ingredients_text": "..."
    }
  ]
}
```

## Configuration

### Environment Variables
- `USDA_API_KEY`: Your USDA API key (default: "DEMO_KEY")
- `PORT`: Server port (default: 3000)
- `SCRAPER_DELAY`: Delay between scraper requests (default: 1000ms)

### Scraper Configuration
Modify `open_food_facts_scraper.py` to adjust:
- `max_pages`: Number of pages to scrape
- `request_delay`: Delay between API requests
- `output_dir`: Directory for scraped data

## File Structure

```
backend/
├── server.js                    # Main API server
├── usda.js                      # Original USDA integration
├── open_food_facts_scraper.py   # Python scraper
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── data/
    └── food/
        ├── open_food_facts_products_*.json
        └── scrape_summary.json
```

## Development

### Running in Development Mode
```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Start server
node server.js

# Or with nodemon for auto-reload
npx nodemon server.js
```

### Testing Endpoints
```bash
# Test USDA search
curl "http://localhost:3000/api/food/usda?q=apple"

# Test Open Food Facts search
curl "http://localhost:3000/api/food/openfoodfacts?q=coca%20cola"

# Test combined search
curl "http://localhost:3000/api/food/search?q=banana"

# Run scraper
curl -X POST "http://localhost:3000/api/scraper/run" \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 2}'
```

## Error Handling

The API includes comprehensive error handling:
- **400 Bad Request**: Missing or invalid parameters
- **404 Not Found**: No data found
- **500 Internal Server Error**: Server or database errors

All errors return JSON format:
```json
{
  "error": "Error description",
  "details": "Additional error details"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Part of the WellAware project. See main project LICENSE file. 