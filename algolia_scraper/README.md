# Wellaware Algolia Scraper for Sobeys & Safeway

This directory contains a Python-based web scraping solution for extracting product data from the Sobeys and Safeway websites. Both retailers use the same underlying Algolia search API, which allows this single scraper to handle both sources.

The project is designed as a two-phase data pipeline:
1.  **Scraping**: `algolia_scraper.py` connects to the API and downloads the raw product data for each specified store into separate `.jsonl` files.
2.  **Processing**: `process_data.py` reads the output from the scraper and can operate in two modes:
    - **Full Mode**: Merges data, creates a master file, and sorts all products by category.
    - **Keyword-Only Mode**: Merges data and only performs a search for the specified keywords, skipping all other output.

## Features

- **Robust Scraping**: Mimics browser requests to avoid being blocked by the API.
- **Flexible Data Processing**: The processing script accepts command-line arguments for custom input files and features a dynamic "keyword-only" search mode.
- **Data Deduplication**: Intelligently merges product data from multiple sources into a single record.
- **Detailed Logging**: All operations are logged to `algolia_scraper.log` for easy tracking and debugging.
- **Containerized**: Includes a `Dockerfile` and `entrypoint.sh` for easy, consistent, and flexible execution.
- **Advanced Output Sorting**:
    - **By Category**: In full mode, automatically sorts all products into individual `.jsonl` files based on their primary category.
    - **By Keyword**: In keyword-only mode, filters and saves products into `.jsonl` files based on keywords provided at runtime.

## Setup and Installation

### Prerequisites

- Python 3.7+
- Docker (optional, for containerized execution)

### Installation

1.  **Clone the repository.**
2.  **Navigate to the project root directory.**
3.  **Install the required Python packages:**
    ```bash
    pip install -r algolia_scraper/requirements.txt
    ```

## Usage

### Running the Scraper Locally

You can run the entire pipeline from the command line.

1.  **Run the scraper for each store:**
    *This will create `sobeys_products.jsonl` and `safeway_products.jsonl` in the project root.*
    ```bash
    python algolia_scraper/algolia_scraper.py sobeys
    python algolia_scraper/algolia_scraper.py safeway
    ```

2.  **Run the data processing script:**
    The processing script is highly configurable via command-line arguments.

    *   **Full Run (creates master file and category outputs):**
        ```bash
        python algolia_scraper/process_data.py
        ```
    *   **Keyword-Only Run (only creates keyword outputs):**
        ```bash
        python algolia_scraper/process_data.py --keywords organic "gluten free" baby
        ```
    *   **Specifying custom input and output files (in full mode):**
        ```bash
        python algolia_scraper/process_data.py --input file1.jsonl file2.jsonl --output custom_master.jsonl
        ```
    Use `python algolia_scraper/process_data.py --help` to see all available options.

### Running with Docker

The included `Dockerfile` and `entrypoint.sh` simplify execution by running the entire pipeline in a container.

1.  **Build the Docker image** from the project root:
    ```bash
    docker build -t algolia-scraper -f algolia_scraper/Dockerfile .
    ```

2.  **Run the container:**
    You can pass arguments to the `process_data.py` script at the end of the `docker run` command.

    *   **Run with default settings (full mode):**
        ```bash
        docker run --name algolia-scraper-instance algolia-scraper
        ```
    *   **Run with keyword filtering (keyword-only mode):**
        ```bash
        docker run --name algolia-scraper-instance algolia-scraper --keywords organic baby
        ```

3.  **Copy the output:**
    After the container finishes, copy the generated files to your local machine.
    ```bash
    # Example for a full run
    docker cp algolia-scraper-instance:/app/products_master.jsonl .
    docker cp algolia-scraper-instance:/app/output_by_category .
    # Example for a keyword run
    docker cp algolia-scraper-instance:/app/output_by_keyword .
    # Always copy the log file
    docker cp algolia-scraper-instance:/app/algolia_scraper.log .
    docker rm algolia-scraper-instance
    ```

## Schema

The final output in `products_master.jsonl` and the sorted files follows this JSON schema for each line:

```json
{
  "productName": "Product Name",
  "brand": "Product Brand",
  "sources": ["sobeys", "safeway"],
  "productUrl": "https://www.example.com/product-link",
  "imageUrl": "https://www.example.com/image-link.jpg",
  "category": [
    "Main Category",
    "Sub Category"
  ],
  "scrapedAt": "2025-08-01T18:00:00Z",
  "details": {
    "articleNumber": "123456",
    "description": "Product description text.",
    "size": "1.5 kg",
    "upc": ["012345678912"],
    "ingredients": ["Ingredient 1", "Ingredient 2"],
    "nutritionFacts": {
      "servingSize": "100g",
      "calories": 100
    }
  }
}
```
