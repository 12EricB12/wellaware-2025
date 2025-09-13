import json
import os
import logging
import re
import argparse
from collections import defaultdict

# --- Logging Setup (Consistent with the scraper) ---
log_file = 'algolia_scraper.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'), # Append mode
        logging.StreamHandler()
    ]
)

class DataProcessor:
    """
    Processes and merges product data from multiple .jsonl files.
    Can operate in two modes:
    1. Full process: Merges, creates a master file, and sorts by category.
    2. Keyword-only: Merges and only filters by the provided keywords.
    """
    def __init__(self, keywords_to_filter=None):
        """
        Initializes the processor with keywords.
        """
        self.keywords_to_filter = keywords_to_filter or []
        self.master_products = {}

    def _merge_files(self, input_filenames):
        """
        Reads input files and merges duplicates based on 'articleNumber'.
        """
        logging.info("Starting data processing and merging...")
        for filename in input_filenames:
            if not os.path.exists(filename):
                logging.warning(f"Input file not found: {filename}. Skipping.")
                continue

            logging.info(f"Processing {filename}...")
            with open(filename, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    try:
                        product = json.loads(line)
                        article_number = product.get("details", {}).get("articleNumber")
                        source = product.get("source")

                        if not article_number:
                            logging.warning(f"Skipping product with no articleNumber in {filename} on line {i}")
                            continue

                        if article_number not in self.master_products:
                            product['sources'] = [product.pop('source')]
                            self.master_products[article_number] = product
                        else:
                            if source and source not in self.master_products[article_number]['sources']:
                                self.master_products[article_number]['sources'].append(source)
                    except json.JSONDecodeError:
                        logging.error(f"Could not decode JSON from line {i} in {filename}.")
                        continue
        logging.info(f"Merging complete. Found {len(self.master_products)} unique products.")

    def _write_master_file(self, output_filename):
        """
        Writes the merged product data to a single master .jsonl file.
        """
        logging.info(f"Writing {len(self.master_products)} unique products to {output_filename}...")
        with open(output_filename, 'w', encoding='utf-8') as f:
            for product in self.master_products.values():
                f.write(json.dumps(product) + '\n')
        logging.info(f"Master file saved to {output_filename}.")

    def _sort_by_category(self, output_dir="output_by_category"):
        """
        Sorts products into separate .jsonl files based on their primary category.
        """
        logging.info(f"Sorting products by category into '{output_dir}'...")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        categorized_products = defaultdict(list)
        for product in self.master_products.values():
            categories = product.get('category')
            if categories and isinstance(categories, list) and len(categories) > 0:
                primary_category = categories[0]
                sanitized_name = re.sub(r'[\\/*?:"<>|]', "", primary_category)
                categorized_products[sanitized_name].append(product)
            else:
                categorized_products["Uncategorized"].append(product)

        for category, products in categorized_products.items():
            file_path = os.path.join(output_dir, f"{category}.jsonl")
            with open(file_path, 'w', encoding='utf-8') as f:
                for product in products:
                    f.write(json.dumps(product) + '\n')
        logging.info("Finished sorting by category.")

    def _filter_by_keyword(self, output_dir="output_by_keyword"):
        """
        Filters products based on a list of keywords and saves them to separate files.
        """
        logging.info(f"Filtering products by keywords into '{output_dir}'...")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for keyword in self.keywords_to_filter:
            logging.info(f"Filtering for keyword: '{keyword}'")
            keyword_products = []
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            for product in self.master_products.values():
                search_text = ' '.join(filter(None, [
                    product.get('productName'),
                    product.get('brand'),
                    product.get('details', {}).get('description'),
                    ' '.join(product.get('category', []))
                ]))
                if pattern.search(search_text):
                    keyword_products.append(product)
            
            if keyword_products:
                file_path = os.path.join(output_dir, f"{keyword.replace(' ', '_')}.jsonl")
                with open(file_path, 'w', encoding='utf-8') as f:
                    for product in keyword_products:
                        f.write(json.dumps(product) + '\n')
                logging.info(f"Found {len(keyword_products)} products for '{keyword}'. Saved to {file_path}")
        logging.info("Finished filtering by keyword.")

    def run(self, input_files, master_filename, keyword_only=False):
        """
        Executes the processing pipeline based on the selected mode.
        """
        self._merge_files(input_files)

        if keyword_only:
            # If it's a keyword-only run, just do the filtering.
            self._filter_by_keyword()
        else:
            # Otherwise, run the full pipeline.
            self._write_master_file(master_filename)
            self._sort_by_category()
            # Still run keyword filtering in full mode if keywords were provided.
            if self.keywords_to_filter:
                self._filter_by_keyword()
        
        logging.info("Data processing pipeline complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process and merge scraped product data. Operates in two modes: a full run or a keyword-only search."
    )
    parser.add_argument(
        '-i', '--input',
        nargs='+',
        default=["sobeys_products.jsonl", "safeway_products.jsonl"],
        help="List of input .jsonl files to process."
    )
    parser.add_argument(
        '-o', '--output',
        default="products_master.jsonl",
        help="Name of the master output file (used in full mode)."
    )
    parser.add_argument(
        '-k', '--keywords',
        nargs='*',
        help="A list of keywords to filter by. If provided, the script runs in keyword-only mode."
    )
    args = parser.parse_args()

    # Determine if we are in keyword-only mode
    is_keyword_run = bool(args.keywords)

    # --- Execution ---
    processor = DataProcessor(keywords_to_filter=args.keywords)
    processor.run(
        input_files=args.input, 
        master_filename=args.output, 
        keyword_only=is_keyword_run
    )
