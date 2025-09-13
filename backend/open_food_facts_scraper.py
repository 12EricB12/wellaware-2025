#!/usr/bin/env python3
"""
Open Food Facts API Scraper
A robust Python script to extract food product data from the Open Food Facts API.

Author: Abdallah
Project: WellAware
Branch: abdallah-scraper
"""

import requests
import json
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class OpenFoodFactsScraper:
    """
    A comprehensive scraper for the Open Food Facts API.
    Handles pagination, data extraction, validation, and structured output.
    """
    
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/cgi/search.pl"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WellAware-Food-Scraper/1.0 (https://github.com/Wellawareapp/wellaware)'
        })
        
        # Create output directories
        self.output_dir = "data/food"
        self.ensure_directories()
        
        # Rate limiting
        self.request_delay = 1.0  # seconds between requests
        
    def ensure_directories(self):
        """Create necessary output directories."""
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info(f"Output directory ensured: {self.output_dir}")
    
    def make_request(self, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Make a request to the Open Food Facts API with error handling.
        
        Args:
            params: Dictionary of request parameters
            
        Returns:
            Dictionary containing API response or None if failed
        """
        try:
            # Add default parameters
            default_params = {
                'action': 'process',
                'json': 1,
                'page_size': 100,  # Maximum allowed by API
                'sort_by': 'unique_scans_n',  # Sort by popularity
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains',
                'tag_0': 'food',  # Focus on food products
            }
            
            # Merge with provided parameters
            request_params = {**default_params, **params}
            
            logging.info(f"Making request with params: {request_params}")
            
            response = self.session.get(self.base_url, params=request_params, timeout=30)
            response.raise_for_status()
            
            # Add rate limiting
            time.sleep(self.request_delay)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return None
    
    def validate_product(self, product: Dict) -> bool:
        """
        Validate if a product has essential information.
        
        Args:
            product: Product dictionary from API
            
        Returns:
            Boolean indicating if product is valid
        """
        required_fields = ['code', 'product_name']
        
        for field in required_fields:
            if not product.get(field):
                return False
        
        # Additional validation: ensure it's actually a food product
        categories = product.get('categories', '').lower()
        if not categories:
            return False
            
        # Check if it contains food-related categories
        food_keywords = ['food', 'beverage', 'snack', 'meal', 'drink', 'dairy', 'meat', 'vegetable', 'fruit']
        has_food_category = any(keyword in categories for keyword in food_keywords)
        
        return has_food_category
    
    def extract_product_data(self, product: Dict) -> Dict:
        """
        Extract and structure relevant data from a product.
        
        Args:
            product: Raw product data from API
            
        Returns:
            Cleaned and structured product data
        """
        # Extract basic product information
        extracted_data = {
            'code': product.get('code', ''),
            'product_name': product.get('product_name', ''),
            'brands': product.get('brands', ''),
            'categories': product.get('categories', ''),
            'ingredients_text': product.get('ingredients_text', ''),
            'quantity': product.get('quantity', ''),
            'image_url': product.get('image_url', ''),
            'image_front_url': product.get('image_front_url', ''),
            'countries': product.get('countries', ''),
            'stores': product.get('stores', ''),
            'packaging': product.get('packaging', ''),
            'labels': product.get('labels', ''),
            'origins': product.get('origins', ''),
            'manufacturing_places': product.get('manufacturing_places', ''),
            'allergens': product.get('allergens', ''),
            'traces': product.get('traces', ''),
            'serving_size': product.get('serving_size', ''),
            'serving_quantity': product.get('serving_quantity', ''),
            'nova_group': product.get('nova_group', ''),
            'nutrition_grade': product.get('nutrition_grade_fr', ''),
            'ecoscore_grade': product.get('ecoscore_grade', ''),
            'created_datetime': product.get('created_datetime', ''),
            'last_modified_datetime': product.get('last_modified_datetime', ''),
        }
        
        # Extract nutriments as a separate grouped object
        nutriments = product.get('nutriments', {})
        if nutriments:
            extracted_data['nutriments'] = {
                'energy_kcal': nutriments.get('energy-kcal_100g', ''),
                'energy_kj': nutriments.get('energy-kj_100g', ''),
                'fat': nutriments.get('fat_100g', ''),
                'saturated_fat': nutriments.get('saturated-fat_100g', ''),
                'carbohydrates': nutriments.get('carbohydrates_100g', ''),
                'sugars': nutriments.get('sugars_100g', ''),
                'fiber': nutriments.get('fiber_100g', ''),
                'proteins': nutriments.get('proteins_100g', ''),
                'salt': nutriments.get('salt_100g', ''),
                'sodium': nutriments.get('sodium_100g', ''),
                'calcium': nutriments.get('calcium_100g', ''),
                'iron': nutriments.get('iron_100g', ''),
                'vitamin_c': nutriments.get('vitamin-c_100g', ''),
                'vitamin_a': nutriments.get('vitamin-a_100g', ''),
            }
        
        return extracted_data
    
    def scrape_products(self, max_pages: int = 50) -> List[Dict]:
        """
        Scrape food products from Open Food Facts API with pagination.
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of validated and cleaned product data
        """
        all_products = []
        page = 1
        
        logging.info(f"Starting scrape - targeting {max_pages} pages")
        
        while page <= max_pages:
            logging.info(f"Fetching page {page} of food products...")
            
            params = {
                'page': page
            }
            
            response_data = self.make_request(params)
            
            if not response_data:
                logging.error(f"Failed to fetch page {page}")
                break
            
            products = response_data.get('products', [])
            
            if not products:
                logging.info(f"No products found on page {page}. Stopping.")
                break
            
            valid_products = 0
            
            for product in products:
                if self.validate_product(product):
                    extracted_product = self.extract_product_data(product)
                    all_products.append(extracted_product)
                    valid_products += 1
            
            logging.info(f"Page {page}: Found {valid_products} valid products out of {len(products)} total")
            
            # Check if we've reached the end
            if len(products) < 100:  # Less than page_size indicates last page
                logging.info("Reached last page of results")
                break
            
            page += 1
        
        logging.info(f"Scraping complete! Total valid products collected: {len(all_products)}")
        return all_products
    
    def save_products(self, products: List[Dict], filename: str = None) -> str:
        """
        Save products to a JSON file.
        
        Args:
            products: List of product dictionaries
            filename: Optional custom filename
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"open_food_facts_products_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Create metadata
        metadata = {
            'scrape_date': datetime.now().isoformat(),
            'total_products': len(products),
            'source': 'Open Food Facts API',
            'scraper_version': '1.0',
            'data_schema': {
                'code': 'Product barcode',
                'product_name': 'Product name',
                'brands': 'Brand names',
                'categories': 'Product categories',
                'ingredients_text': 'Ingredients list',
                'quantity': 'Product quantity',
                'image_url': 'Product image URL',
                'nutriments': 'Nutritional information per 100g'
            }
        }
        
        output_data = {
            'metadata': metadata,
            'products': products
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Successfully saved {len(products)} products to {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Failed to save products: {e}")
            return None
    
    def generate_summary_report(self, products: List[Dict]) -> Dict:
        """
        Generate a summary report of the scraped data.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            Summary statistics dictionary
        """
        if not products:
            return {}
        
        # Basic statistics
        total_products = len(products)
        products_with_images = sum(1 for p in products if p.get('image_url'))
        products_with_nutrition = sum(1 for p in products if p.get('nutriments'))
        
        # Category analysis
        categories = {}
        for product in products:
            product_categories = product.get('categories', '').split(',')
            for cat in product_categories:
                cat = cat.strip()
                if cat:
                    categories[cat] = categories.get(cat, 0) + 1
        
        # Brand analysis
        brands = {}
        for product in products:
            product_brands = product.get('brands', '').split(',')
            for brand in product_brands:
                brand = brand.strip()
                if brand:
                    brands[brand] = brands.get(brand, 0) + 1
        
        summary = {
            'total_products': total_products,
            'products_with_images': products_with_images,
            'products_with_nutrition': products_with_nutrition,
            'image_coverage': f"{(products_with_images/total_products)*100:.1f}%",
            'nutrition_coverage': f"{(products_with_nutrition/total_products)*100:.1f}%",
            'top_categories': sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10],
            'top_brands': sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10],
            'countries_covered': len(set(p.get('countries', '') for p in products if p.get('countries')))
        }
        
        return summary

def main():
    """Main execution function."""
    logging.info("Starting Open Food Facts scraper...")
    
    scraper = OpenFoodFactsScraper()
    
    # Scrape products (adjust max_pages as needed)
    products = scraper.scrape_products(max_pages=10)  # Start with 10 pages for testing
    
    if products:
        # Save products to JSON
        filepath = scraper.save_products(products)
        
        if filepath:
            # Generate and save summary report
            summary = scraper.generate_summary_report(products)
            
            summary_path = os.path.join(scraper.output_dir, "scrape_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Summary report saved to {summary_path}")
            
            # Print summary to console
            print("\n" + "="*50)
            print("SCRAPING SUMMARY")
            print("="*50)
            print(f"Total products scraped: {summary['total_products']}")
            print(f"Products with images: {summary['products_with_images']} ({summary['image_coverage']})")
            print(f"Products with nutrition: {summary['products_with_nutrition']} ({summary['nutrition_coverage']})")
            print(f"Countries covered: {summary['countries_covered']}")
            print(f"Data saved to: {filepath}")
            print("="*50)
    
    logging.info("Scraper execution completed!")

if __name__ == "__main__":
    main() 