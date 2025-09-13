import requests
import json
import datetime
import argparse
import logging
from urllib.parse import urlencode

# --- Logging Setup ---
log_file = 'algolia_scraper.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class AlgoliaScraper:
    """
    A class to scrape product data from an Algolia API endpoint for different grocery stores.
    This scraper is designed to mimic a browser's network request to avoid being blocked.
    """
    ALGOLIA_BASE_URL = "https://acsyshf8au-dsn.algolia.net/1/indexes/*/queries"
    ALGOLIA_API_KEY = "fe555974f588b3e76ad0f1c548113b22"
    ALGOLIA_APP_ID = "ACSYSHF8AU"

    def __init__(self, store_id, source_name, base_url, index_name):
        """
        Initializes the scraper with store-specific details.
        """
        self.store_id = store_id
        self.source_name = source_name
        self.base_url = base_url
        self.index_name = index_name
        self.session = requests.Session()

        # The API key is restricted to this referer, so we must always use it
        self.api_referer = "https://www.sobeys.com/"

        # Update headers to mimic a browser, based on captured request
        self.session.headers.update({
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "text/plain",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "Referer": self.api_referer,
            "Origin": self.base_url,
        })

        # Construct the full URL with Algolia credentials as query parameters, like the browser does
        params = {
            'x-algolia-agent': 'Algolia for JavaScript (5.35.0); Search (5.35.0); Browser',
            'x-algolia-api-key': self.ALGOLIA_API_KEY,
            'x-algolia-application-id': self.ALGOLIA_APP_ID
        }
        self.algolia_url = f"{self.ALGOLIA_BASE_URL}?{urlencode(params)}"


    def fetch_all_products(self):
        """
        Fetches all products from the Algolia API using pagination.
        """
        page = 0
        total_pages = 1

        while page < total_pages:
            # This payload structure is based on the captured network request from the browser
            payload = {
                "requests": [
                    {
                        "indexName": self.index_name,
                        "analyticsTags": ["A", "website"],
                        "clickAnalytics": True,
                        "facets": ["brand", "hierarchicalCategories.lvl0", "price"],
                        "filters": f"storeId:{self.store_id} AND isVisible:true AND isMassOffers:false",
                        "highlightPostTag": "__/ais-highlight__",
                        "highlightPreTag": "__ais-highlight__",
                        "hitsPerPage": 1000,
                        "maxValuesPerFacet": 1000,
                        "page": page,
                        "userToken": "anonymous-b13abc22-0b15-400a-9916-b56e23f68068" # from captured request
                    }
                ]
            }

            try:
                logging.info(f"Scraping page {page + 1}/{total_pages} for {self.source_name}...")
                
                # The body is sent as a JSON string, mimicking the captured 'fetch' call
                response = self.session.post(self.algolia_url, data=json.dumps(payload))
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])[0]
                hits = results.get("hits", [])
                
                if not hits:
                    logging.info("No more products found. Exiting.")
                    break
                
                if page == 0:
                    total_pages = results.get("nbPages", 1)

                for hit in hits:
                    yield hit
                
                page += 1

            except requests.exceptions.RequestException as e:
                logging.error(f"An error occurred during the request: {e}")
                logging.error(f"Response content: {response.text if 'response' in locals() else 'N/A'}")
                break
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                logging.error(f"Error parsing response JSON: {e}")
                logging.error(f"Response content: {response.text if 'response' in locals() else 'N/A'}")
                break

    def _transform_hit(self, hit):
        """
        Transforms a raw Algolia product hit into the desired schema.
        """
        image_url = None
        images = hit.get("images")
        if images and isinstance(images, list) and len(images) > 0:
            if isinstance(images[0], str): # The new response has image URLs as strings
                image_url = images[0]
            elif isinstance(images[0], dict) and "url" in images[0]:
                image_url = images[0].get("url")

        nutritional_info = hit.get("nutritionalInformation", {}) or {}

        upc_string = hit.get("upc")
        upc_list = upc_string.split(',') if upc_string else []

        return {
            "productName": hit.get("name"),
            "brand": hit.get("brand"),
            "source": self.source_name,
            "productUrl": f"{self.base_url}/products/{hit.get('pageSlug', '')}",
            "imageUrl": image_url,
            "category": hit.get("categories"),
            "scrapedAt": datetime.datetime.now(datetime.UTC).isoformat(),
            "details": {
                "articleNumber": hit.get("articleNumber"),
                "description": hit.get("description"),
                "size": hit.get("weight"),
                "upc": upc_list,
                "ingredients": nutritional_info.get("ingredients"),
                "nutritionFacts": nutritional_info,
            }
        }

    def run(self, output_filename):
        """
        Runs the scraper and saves the transformed data to a .jsonl file.
        """
        logging.info(f"Starting scrape for {self.source_name}...")
        product_count = 0
        with open(output_filename, "w", encoding="utf-8") as f:
            for hit in self.fetch_all_products():
                transformed_data = self._transform_hit(hit)
                f.write(json.dumps(transformed_data) + "\n")
                product_count += 1
        logging.info(f"Scraping finished. Found {product_count} products. Data saved to {output_filename}")


if __name__ == "__main__":
    STORES = {
        "sobeys": {
            "store_id": "0637",
            "base_url": "https://www.sobeys.com",
            "index_name": "dxp_product_en"
        },
        "safeway": {
            "store_id": "4811",
            "base_url": "https://www.safeway.ca",
            "index_name": "dxp_product_en"
        }
        # FreshCo is intentionally omitted as it does not have a product catalog API.
    }

    parser = argparse.ArgumentParser(description="Scrape product data from Sobeys or Safeway.")
    parser.add_argument("store", choices=STORES.keys(), help="The store to scrape.")
    args = parser.parse_args()

    store_name = args.store
    config = STORES[store_name]
    
    logging.info(f"Configuring scraper for {store_name.title()}...")
    
    scraper = AlgoliaScraper(
        store_id=config["store_id"],
        source_name=store_name,
        base_url=config["base_url"],
        index_name=config["index_name"]
    )
    
    output_file = f"{store_name}_products.jsonl"
    scraper.run(output_file)
