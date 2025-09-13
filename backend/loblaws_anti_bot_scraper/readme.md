# Loblaws scraper for websites with anti-bot protection
Only implemented for Shoppers and T&T. Other websites may require the creation of a different spider and modifications to the CSS selectors, 
although the logic should remain largely unchanged.  

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
3. Install Scrapy-Selenium & undetected chromedriver
```
pip install scrapy-selenium
pip install undetected-chromedriver
```
4. Run the spider
```
cd loblaws_anti_bot_scraper
scrapy crawl STORE -a [other fields] ...
```
Mandatory fields:
- STORE: the name of the store (shoppers, tnt)

Other fields:
- current_page (int): Resume execution from a certain page if it was halted. Not really necessary to set here as it will be automatically decided
- urls_to_scrape (list[str]): All the complete URLs from each category of the website to be scraped.
- start_x (int): Where to place the minimized window, in x coordinates
- start_y (int): Where to place the minimized window, in y coordinates

Notes:
- Each field passed should be specified with -a
- Data is saved to the same folder as the project
- start_x and start_y fields are useful for keeping many tabs open at once to speed up scraping. Tabs must be kept in focus to load all content
- The current page is decided automatically due to cutoffs because of anti bot prevention
