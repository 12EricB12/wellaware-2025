# Loblaws scraper for websites with no anti-bot protection
Use for websites with a similar layout to:
- Loblaws (https://www.loblaws.ca/en)
- Real Canadian Superstore
- Zehrs
- etc...

Other websites may require the creation of a different spider and modifications to the CSS selectors, although the logic should remain largely unchanged.  

Use for websites from the Loblaws Group only.

## How to use
1. Create a virtual environment (If not created already)
(Using Bash)
```
cd backend
python -m venv myenv
```
(Navigate to the backend however is required from your OS)
2. Activate venv
```
source myenv/scripts/activate
```
3. Install Scrapy-Selenium
```
pip install scrapy-selenium
```
4. Run the spider
```
scrapy crawl loblaws -a store=store -a [other fields] ...
```
Mandatory fields:
- store: the base name of the website (ex. loblaws for https://www.loblaws.ca/en)

Other fields:
- current_page (int): Resume execution from a certain page if it was halted
- non_food_categories (str, path): A JSON file of what non-food categories you would like to be scraped (baby products, cleaning, etc.), in the following format:
```
{
  "category_to_scrape":
    {
      "pages_to_scrape": "all",
      "url_to_scrape": "url_to_scrape"
    }
}
```
Example using the category Baby
```
{
  "Baby":
    {
      "pages_to_scrape": ["Diapers, Wipes & Training Pants", "Nursing & Feeding Accessories"],
      "url_to_scrape": "/en/baby/c/27987?navid=flyout-L2-Baby"
    }
}
```
  The non_food_categories file should be placed in the same folder as the project and passed as: -a non_food_categories="non_food.json".
- scrape_non_food_only (bool): Whether non-food scraping should be activated (True) or not (False). Default to False
- pages_to_scrape (int/str): How many pages to scrape before stopping the program. Default to 'all' (ie. all pages are scraped per category)
- correct_mode (bool): Activate (True) correct mode to fill out corrupted or missing fields. Default to False
- path_to_correct (str): The path to the jsonl to be corrected.

Notes:
- Each field passed should be specified with -a
- Data is saved to the same folder as the project
