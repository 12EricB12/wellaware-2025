import requests
from datetime import datetime

def search_open_beauty(product_name: str, max_results: int = 5):
    """
    Search Open Beauty Facts for a product.
    """
    url = "https://world.openbeautyfacts.org/cgi/search.pl"
    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
    }

    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json().get("products", [])[:max_results]
        product = data[0]
        return {
        "productName": product.get("product_name", product_name),
        "brand": product.get("brands", "Unknown"),
        "source": "openbeautyfacts",
        "productUrl": product.get("url"),
        "imageUrl": product.get("image_url"),
        "category": product.get("categories_hierarchy", []),
        "scrapedAt": datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
        "details": {
            "description": product.get("generic_name", ""),
            "size": product.get("quantity"),
            "upc": product.get("code"),
            "ingredients": product.get("ingredients_text", "").split(", "),
        }
        }
    except Exception as e:
        return {"error": str(e)}
    
# food_results = search_cnf("banana")
# print("Banana CNF Search Results:")
# for r in food_results:
#     print(r)

# Beauty Facts Example
beauty_results = search_open_beauty("shampoo")
print("\nSearch Results:")
print(beauty_results)
