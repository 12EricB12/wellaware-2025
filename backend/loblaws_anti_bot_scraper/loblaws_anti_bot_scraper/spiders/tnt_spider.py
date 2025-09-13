from tracemalloc import start
import scrapy
import re
import time
import json
import os
import undetected_chromedriver as uc
import threading

from datetime import datetime
from selenium import webdriver
from scrapy.selector import Selector
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import MoveTargetOutOfBoundsException, TimeoutException
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.window import WindowTypes
from selenium.webdriver.common.keys import Keys

# FOR TNT: Implement endless scroll.
# Keep going until this is found: #main > article > div > div > div.category-categoryContent-Ixm > div.category-contentBox-df6 > div > div > p, text=Oops! you've reached my bottom line
class TntSpider(scrapy.Spider):
    name = 'tnt'

    # PRODUCT INFORMATION FIELDS
    data = []
    urls_to_scrape = []
    product_links = []
    products_to_scrape = []

    # PRODUCT SCRAPING PROGRESS FIELDS
    current_product_index = 0
    current_url_index = 0

    def __init__(self, urls_to_scrape=[
        'https://www.tntsupermarket.com/eng/product-categories/t-t-kitchen.html',
        'https://www.tntsupermarket.com/eng/product-categories/t-t-bakery.html',
        'https://www.tntsupermarket.com/eng/product-categories/fruits.html',
        'https://www.tntsupermarket.com/eng/product-categories/vegetables.html',
        'https://www.tntsupermarket.com/eng/product-categories/meat.html',
        'https://www.tntsupermarket.com/eng/product-categories/seafood.html',
        'https://www.tntsupermarket.com/eng/product-categories/dairy-soy.html',
        'https://www.tntsupermarket.com/eng/product-categories/ice-cream.html',
        'https://www.tntsupermarket.com/eng/product-categories/dim-sum-noodles.html',
        'https://www.tntsupermarket.com/eng/product-categories/frozen-meals.html',
        'https://www.tntsupermarket.com/eng/product-categories/instant.html',
        'https://www.tntsupermarket.com/eng/product-categories/snacks.html',
        'https://www.tntsupermarket.com/eng/product-categories/pantry.html',
        'https://www.tntsupermarket.com/eng/product-categories/sauces-pickles.html',
        'https://www.tntsupermarket.com/eng/product-categories/beverage.html',
        'https://www.tntsupermarket.com/eng/product-categories/health-beauty.html'
    ]):
        super().__init__()
        self.urls_to_scrape = urls_to_scrape
        self.base_url = self.urls_to_scrape[self.current_url_index]

    def start_requests(self):
        yield SeleniumRequest(
            wait_time=15,
            url=self.base_url,
            callback=self.parse
        )

    # Removes any non alphanumeric characters and reformats the string to follow camel casing convention for JSON
    def format_json(self, text):
        text_alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', (text))
        return (text_alphanumeric[0].lower() + text_alphanumeric[1:]).replace(" ", "")

    def save_by_item(self, data, base_path=None):
        # Save each page
        if base_path is None:
            base_path = fr'./{self.name}/{self.base_url.split("/")[-1].replace('.html', '')}'

        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        filename = fr"{base_path}/data.jsonl"
        with open(filename, "a", encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')

    def get_details(self, response):
        print("GOING NOW!")
        base_path = 'main > div.main-page-hXb > form'
        driver = response.request.meta['driver']

        # Attempt to wait for category and the product to load
        try:
            wait = WebDriverWait(driver, timeout=15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'main > div.main-page-hXb > div.breadcrumbs-root-jbs > a')))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'{base_path}')))
        except:
            base_path = fr'./{self.name}/{self.base_url.split("/")[-1].replace('.html', '')}'
            product_links_file = os.path.join(base_path, 'product_links.json')
            with open(product_links_file, 'w') as f:
                json.dump({'product_links': self.product_links, 'current_product_index': self.current_product_index}, f)

        # Note: Selectors are used when we are unsure if a value exists or not.
        # Selenium methods are better for when you want to wait for rendered content.
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)

        # Get html
        description = sel.css(f'{base_path} > div.productFullDetail-shortDescription-DMa > div').get()
        category = sel.css('main > div.main-page-hXb > div.breadcrumbs-root-jbs > a').getall()
        productNum = sel.css(f'{base_path} > section > div > div.productFullDetail-sku-zcN').get()

        category_list = [Selector(text=c).xpath('//text()').extract() for c in category] if len(category) > 0 else []
        category_list = [c[0] for c in category_list if c[0] not in ['Home', 'Product Categories']]

        description = None if description == None else Selector(text=description).xpath('//text()').extract()
        productNum = None if productNum == None else Selector(text=productNum).xpath('//text()').extract()
        description = None if description is None or len(description) == 0 else ''.join(description)
        productNum = None if productNum is None or len(productNum) == 0 else "".join(re.findall(r'\d', productNum[0]))

        # No nutrition facts available for T&T (大统华)
        final_data = {
                **response.meta['product_data'],
                "category": category_list,
                'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                **{"details": {
                "description": description,
                "sku": productNum 
                }
            }
        }
        
        # Remove any fields that may be None to save space
        final_data['details'] = {k: v for k, v in final_data['details'].items() if v != None and v != ''}
        # Save to JSONL
        self.save_by_item(final_data)
        yield from self.visit_next_product()

    def parse(self, response):
        print(f'RESPONSE: {response.url}')
        driver = response.request.meta['driver']
        base_path = 'article > div > div > div.category-categoryContent-Ixm'
        
        wait = WebDriverWait(driver, timeout=300)
        # Interact with the page so it doesn't think we're idle
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_path)))

        # Get html
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)
        driver.implicitly_wait(0)

        # Save all the links that haven't been transversed to yet
        base_path = fr'./{self.name}/{self.base_url.split("/")[-1].replace('.html', '')}'
        product_links_file = os.path.join(base_path, 'product_links.json')

        # Keep scrolling until the bottom is reached
        while True:
            # If we have already saved the links, don't scroll
            if os.path.exists(product_links_file):
                break

            try:
                w = WebDriverWait(driver, 3)
                w.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.category-noData-O4b")))
                break
            except:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)

        items = driver.find_elements(By.CSS_SELECTOR, f'article > div > div > div.category-categoryContent-Ixm > div.category-contentBox-df6 > div > div > div.item-root-NyK')

        # Processing & Cleanup
        product_links = []
        for item in items:
            sel = Selector(text=item.get_attribute("innerHTML"))

            # Go to the next page and grab other fields (description, nutrition, etc.)
            productURL = 'https://www.tntsupermarket.com' + sel.css('div.item-itemImages-A3X > a::attr(href)').get()
            product_data = {
                'productName': item.find_element(By.CSS_SELECTOR, 'div.item-itemDetails--qp > a.item-name-suo > span').text,
                'source': self.name,
                'productUrl': productURL,
                'imageUrl': sel.css('div.item-itemImages-A3X > a > img::attr(src)').get(),
            }

            product_links.append((productURL, product_data))

        
        if not os.path.exists(product_links_file):
            if not os.path.exists(base_path):
                os.makedirs(base_path)

            with open(product_links_file, 'a') as f:
                json.dump({'product_links': product_links, 'current_product_index': 0}, f)
        
        with open(product_links_file, 'r') as f:
            data = json.load(f)
            self.current_product_index = data['current_product_index']
            self.product_links = data['product_links'][self.current_product_index:]

        yield from self.visit_next_product()

    # Saves by category ONLY
    def visit_next_product(self):
        if self.current_product_index < len(self.product_links):
            url, data = self.product_links[self.current_product_index]
            self.current_product_index += 1

            yield SeleniumRequest(
                url=url,
                callback=self.get_details,
                wait_time=10,
                dont_filter=True,
                meta={
                    'product_data': data
                }
            )
        # Reached the end
        else:
            self.current_url_index += 1
            self.base_url = self.urls_to_scrape[self.current_url_index]
            yield SeleniumRequest(
                url=f'{self.base_url}',
                callback=self.parse,
                wait_time=5
            )

class ShoppersSpider(scrapy.Spider):
    name = 'shoppers'

    # PRODUCT SCRAPING INFO FIELDS
    data = []
    urls_to_scrape = []
    products_to_scrape = []
    product_links = []

    # PRODUCT SCRAPING PROGRESS FIELDS
    current_url_index = 0
    current_page = 0
    current_product_index = 0
    current_category = ''

    # LOADING INFORMATION FIELDS
    initalizing = True
    retries = 0
    retry_thresh = 5

    # Note: Recommended sections to scrape for shoppers, however this is overwriteable if you run it in a loop
    def __init__(self, urls_to_scrape=[
        'https://www.shoppersdrugmart.ca/shop/categories/beauty/c/57124',
        'https://www.shoppersdrugmart.ca/shop/collections/luxury-skin-care/c/LuxurySkinCare',
        'https://www.shoppersdrugmart.ca/shop/collections/luxury-fragrance/c/LuxuryFragrance',
        'https://www.shoppersdrugmart.ca/shop/collections/luxury-makeup/c/LuxuryMakeup',
        'https://www.shoppersdrugmart.ca/shop/collections/luxury-hair-care/c/LuxuryHairCare',
        'https://www.shoppersdrugmart.ca/shop/categories/personal-care/c/57128',
        'https://www.shoppersdrugmart.ca/shop/categories/health/vitamins-&-supplements/c/57140',
        'https://www.shoppersdrugmart.ca/shop/categories/health/medicine-and-treatments/c/57139',
        'https://www.shoppersdrugmart.ca/shop/categories/health/sexual-wellness-and-family-planning/c/57143',
        'https://www.shoppersdrugmart.ca/shop/categories/Health/Eye%252C-Ear-%2526-Foot-Care/c/57141',
        'https://www.shoppersdrugmart.ca/shop/categories/baby-and-child/baby-and-child-care/c/57136',
        'https://www.shoppersdrugmart.ca/shop/categories/baby-and-child/feeding-and-formula/c/57137'
    ],
    pages_to_scrape='all', current_page=0, start_x=0, start_y=0):
        super().__init__()
        if type(urls_to_scrape) is str:
            self.urls_to_scrape = urls_to_scrape.split(',')
        else:
            self.urls_to_scrape = urls_to_scrape
        
        self.base_url = self.urls_to_scrape[self.current_url_index]
        self.pages_to_scrape = pages_to_scrape
        self.current_page = int(current_page)
        self.driver = None
        self.start_x = int(start_x)
        self.start_y = int(start_y)

    def start_requests(self):
        print("BASE2:", self.base_url)
        file_path = fr'./{self.name}'
        self.current_page = self.get_current_page(file_path)
        if self.current_page is None:
            self.current_page = 0
        else:
            self.initalizing = False

        self.current_page += 1
        yield SeleniumRequest(
            wait_time=15,
            url=f'{self.base_url}?page={self.current_page}',
            callback=self.parse,
            meta={'page': 1}
        )

    # Removes any non alphanumeric characters and reformats the string to follow camel casing convention for JSON
    def format_json(self, text):
        text_alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', (text))
        return (text_alphanumeric[0].lower() + text_alphanumeric[1:]).replace(" ", "")

    # Save each item's data to a jsonl file per page
    def save_by_item(self, data, page, base_path=None):
        # Save each page
        if base_path is None:
            base_path = fr'./{self.name}/{self.current_category}'

        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        filename = fr"{base_path}/page_{page}.jsonl"
        print(filename)
        with open(filename, "a", encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')

    # Get the details (ingredients, description, etc.) from each item's page
    def get_details(self, response):
        driver = response.request.meta['driver']
        base_path = 'div[id="__next"] > div > div'
        driver.execute_script("document.body.style.zoom='50%'")

        try:
            wait = WebDriverWait(driver, timeout=15)

            # Switch tabs to keep windows loading
            all_handles = driver.window_handles
            previous_tab_handle = all_handles[0]
            driver.switch_to.window(previous_tab_handle)
            time.sleep(1)

            # Close the previous tab
            driver.switch_to.window(all_handles[-1])

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{base_path}")))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.plp__container__2JOqx")))
        except:
            print(f"Timeout exception for {response.meta["product_data"]['productUrl']}")
            # Since Walmart blocks your browser frequently, keep where you left off and restart if a certain number of retries are exceeded.
            if self.retries == self.retry_thresh:
                with open(fr'./{self.name}/{self.current_category}/progress.json', 'w+') as f:
                    json.dump({"product_links": self.product_links, "index": self.current_product_index - self.retry_thresh}, f)
                raise Exception("Retries exceeded, browser blocked. Restarting chrome...")
            self.retries += 1
            yield from self.visit_next_product()

        # Note: Selectors are used when we are unsure if a value exists or not.
        # Selenium methods are better for when you want to wait for rendered content.
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)

        # Get html
        category = driver.find_elements(By.CSS_SELECTOR, 'div[id="__next"] > div > div > div > div > nav[data-testid="breadcrumbs"] > ul > li > a')
        description = sel.css('div.plp__description__2M_zG').get()
        productNum = sel.css(f'{base_path} > div > div > div > div > div.plp__descriptionContainer__mQOMf > p.plp__body__3TvTa').get()

        category_list = [c.text for c in category if c.text != 'Home'] if len(category) != 0 else [self.current_category]
        description = None if description == None else Selector(text=description).xpath('//text()').extract()
        productNum = None if productNum == None else Selector(text=productNum).xpath('//text()').extract()
        description = None if description is None or len(description) == 0 else description[0]
        productNum = None if productNum is None or len(productNum) == 0 else "".join(re.findall(r'\d', productNum[0]))

        # Expand the nutrition facts section, if possible
        # If nutrition facts do not exist, discard ingredients and nutrition
        # This is mostly to ensure compatibaility with non food items (like hygiene products)
        final_data = {}
        ingredients_path = f'{base_path} > div > div > div > div.plp__container__2JOqx > div[data-testid="accordionSection"] > div:nth-child(3)'
        ingredients_button = sel.css(ingredients_path).get()
        if ingredients_button is None:
            final_data = {
                    **response.meta["product_data"],
                    "category": category_list,
                    'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                    **{"details": {
                    "description": description,
                    "productNumber": productNum 
                    }
                }
            }
        else: 
            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'{ingredients_path} > div.lds__accordion__header-container > div')))
            driver.execute_script("arguments[0].click();", button)

            # Only ingredients are available, no nutrition facts
            ingredients = sel.css(f'{ingredients_path} > div > div > div.plp__body__3TvTa').get()
            ingredients = Selector(text=ingredients).xpath('//text()').extract()[0]
            # Merge the product data gotten from the initial homepage scrape with the product data.
            final_data = {
                        **response.meta["product_data"],
                        "category": category_list,
                        'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                        **{"details": {
                        "description": description,
                        "productNumber": productNum,
                        "ingredients": [] if ingredients is None else re.split(r', (?![^()]*\))', ingredients), # Splits according to commas that aren't in brackets, empty list is there for redundancy
                    }
                }
            }
        
        # Remove any fields that may be None to save space
        final_data['details'] = {k: v for k, v in final_data['details'].items() if v != None and v != ''}
        # Save to JSONL file
        self.save_by_item(final_data, response.meta['page'])
        yield from self.visit_next_product()

    def parse(self, response):
        print(f'RESPONSE: {response.url}')
        driver = response.request.meta['driver']
        wait = WebDriverWait(driver, timeout=45)

        # Switch to the new window and open new URL
        # Switch back to the new tab (if you need to continue working there)
        driver.switch_to.new_window(WindowTypes.TAB)
        driver.get(response.url)
        EC.number_of_windows_to_be(2)
        all_handles = driver.window_handles

        # Assuming the previous tab is the first handle in the list
        previous_tab_handle = all_handles[0]

        # Switch to the previous tab
        driver.switch_to.window(previous_tab_handle)
        time.sleep(1)

        # Close the previous tab
        driver.close()
        driver.switch_to.window(all_handles[-1])

        # Zoom out
        driver.execute_script("document.body.style.zoom='25%'")
        driver.set_window_size(350, 350)
        driver.set_window_position(self.start_x, self.start_y)
        time.sleep(0.25)

        base_path = 'div > div[data-testid="listing-page-container"] > div.css-0'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_path)))

        # Get html
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)
        if self.pages_to_scrape == 'all':
            all_pages = sel.css(f'{base_path} > div.chakra-stack > div > a.chakra-link').getall()
            for page in all_pages:
                print("PAGE")
                print(Selector(text=page).xpath('//text()').extract())
            all_pages = [Selector(text=page_num).xpath('//text()').extract()[0] for page_num in all_pages if len(extracted := Selector(text=page_num).xpath('//text()').extract()) != 0 and extracted[0].isdigit()]

            self.pages_to_scrape = 1 if len(all_pages) == 0 else max([int(page_num) for page_num in all_pages])
            print(f"PAGES TO SCRAPE: {self.pages_to_scrape}")

        # category_base_path = f"{base_path} > div.css-0 > div.css-j27rq7 > div[data-testid='section'] > div > nav > ol > li"
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'{base_path} > div.css-2wmcey > div.chakra-container')))
        self.current_category = driver.find_element(By.CSS_SELECTOR, 'h1.chakra-heading').text
        
        # Add what the maximum pages are for this category
        max_pages_path = fr'./{self.name}/{self.current_category}/max_pages.json'
        if not os.path.exists(max_pages_path):
            print(f"CREATING NEW max_pages.json FILE AT: {max_pages_path}")
            os.makedirs(fr'./{self.name}/{self.current_category}')
            with open(max_pages_path, 'a') as f:
                json.dump({"max_pages": self.pages_to_scrape, "url": self.base_url}, f)
        
        file_path = fr'./{self.name}'
        if self.initalizing is True:
            self.current_page = self.get_current_page(file_path)
        if self.current_page is None:
            yield from self.visit_next_product()
        else:
            self.initalizing = False

        # current_category = driver.find_elements(By.CSS_SELECTOR, f'{category_base_path} > span[aria-current="page"]')
        items = driver.find_elements(By.CSS_SELECTOR, f'{base_path} > div[data-testid="product-grid"] > div.css-0')

        if len(self.product_links) == 0:
            # Processing & Cleanup
            product_links = []
            for item in items:
                #main-content > div > div.css-1qfugr1 > div:nth-child(2) > div.css-1afb91u > div:nth-child(1) > div > div > div.css-wbarzq > a > div > p
                food = item.find_element(By.CSS_SELECTOR, 'div.css-1sunozq > div.chakra-linkbox > div > a > div.css-0')
                sel = Selector(text=item.get_attribute("innerHTML"))

                # Go to the next page and grab other fields (description, nutrition, etc.)
                productURL = sel.css('div.css-1sunozq > div.chakra-linkbox > div.css-wbarzq > a::attr(href)').get()
                product_data = {
                    'productName': food.find_element(By.CSS_SELECTOR, 'h3').text,
                    'brand': Selector(text=food.get_attribute("innerHTML")).css('p::text').get(),
                    'source': self.name,
                    'productUrl': productURL,
                    'imageUrl': sel.css('div.css-1sunozq > div.chakra-linkbox > div[data-testid="product-image"] > img::attr(src)').get(),
                }
                product_links.append((productURL, product_data))

            self.retries = 0
            self.product_links = [(url, data) for url, data in product_links]

        yield from self.visit_next_product()

    # Keep visiting either the next product, or the next page until all pages are done scraping
    def visit_next_product(self):
        if self.current_product_index < len(self.product_links):
            url, data = self.product_links[self.current_product_index]
            self.current_product_index += 1

            yield SeleniumRequest(
                url=url,
                callback=self.get_details,
                wait_time=10,
                dont_filter=True,
                meta={
                    'product_data': data,
                    'page': self.current_page
                }
            )
        elif (self.pages_to_scrape == 'all' or self.current_page < self.pages_to_scrape) and self.initalizing is False:
            self.current_product_index = 0
            self.current_page += 1
            self.product_links = []
            yield SeleniumRequest(
                url=f'{self.base_url}?page={self.current_page}',
                callback=self.parse,
                wait_time=5,
                meta={'page': self.current_page}
            )
        # Reached the end
        else:
            self.pages_to_scrape = 'all'
            self.current_url_index += 1
            # Terminate the program
            if self.current_url_index == len(self.urls_to_scrape):
                print("Finished scraping all links")
                return

            self.urls_to_scrape.remove(self.base_url)
            self.base_url = self.urls_to_scrape[self.current_url_index]
            self.current_page = 0
            yield from self.start_requests()

    # Shoppers blocks you on two criteria: one browser kept open for too long, and the same IP address.
    # This solves the issue of the browser being kept open for too long. For IP address switching, consider proxies or VPNs.
    # Automatically selects the page number of the program before we get blocked and counts if all the files from that page have been scraped
    def get_current_page(self, path, items_per_page=36):
        for root, _, curdirs in os.walk(path):
            curdirs = [i.split("_")[1] for i in curdirs if i not in ["max_pages.json", "progress.json"]]
            curdirs = [int(i.replace('.jsonl', '')) for i in curdirs]
            curdirs.sort()

            if len(curdirs) == 0:
                continue

            curdirs_sorted = curdirs
            curdirs_sorted = ["page_" + str(i) + ".jsonl" for i in curdirs_sorted]

            print(curdirs_sorted)
            if os.path.exists(os.path.join(root, "max_pages.json")):
                with open(os.path.join(root, "max_pages.json"), 'r') as f:
                    data = json.load(f)
                    print(curdirs)
                    if self.base_url == data["url"] and (len(curdirs) > 0 and curdirs[-1] >= data["max_pages"]):
                        self.urls_to_scrape.remove(self.base_url)
                        self.base_url = self.urls_to_scrape[self.current_url_index]
                        continue
            else:
                return None
            # The last completed scraped page is the previous page, so check that as a baseline
            if len(curdirs_sorted) > 1:
                with open(os.path.join(root, curdirs_sorted[-2]), 'r') as f:
                    num_items_per_page = len(f.readlines())
                with open(os.path.join(root, curdirs_sorted[-1]), 'r') as f:
                    num_current_items = len(f.readlines())

                # If the last page wasn't scraped completely, delete and set the last current page as the last completed page
                print(f'{curdirs_sorted[-1]} {num_current_items}')
                print(f'{curdirs_sorted[-2]} {num_items_per_page}')
                
                print("CURRENT ITEMS:", num_current_items)
                print("ITEMS PER PAGE:", num_items_per_page)
                if num_current_items <= num_items_per_page - self.retry_thresh:
                    if os.path.exists(os.path.join(root, 'progress.json')):
                        with open(os.path.join(root, 'progress.json'), 'r') as f:
                            data = json.load(f)

            # If only one page was scraped, assume the number of items per page (as specified by the parameter)
            elif len(curdirs) == 1:
                if os.path.exists(os.path.join(root, 'progress.json')):
                    with open(os.path.join(root, 'progress.json'), 'r') as f:
                        data = json.load(f)

            # See if the current category is already complete
            with open(os.path.join(root, 'max_pages.json')) as f:
                data = json.load(f)
            if data['url'] not in self.urls_to_scrape:
                continue

            # Check if we've reached the end - sometimes the item # don't match completely
            if data["max_pages"] == curdirs[-1]:
                self.urls_to_scrape.remove(self.base_url)
                self.base_url = self.urls_to_scrape[self.current_url_index]
                continue
            
            if len(curdirs) > 1:
                pages_covered = max(curdirs[:-1])
            elif len(curdirs) == 1:
                pages_covered = 1
            else:
                pages_covered = 0

            if pages_covered < data["max_pages"] and data["url"] in self.urls_to_scrape:
                if os.path.exists(os.path.join(root, 'progress.json')):
                    with open(os.path.join(root, 'progress.json'), 'r') as f:
                        product_data = json.load(f)
                        self.product_links = product_data['product_links']
                        self.current_product_index = product_data['index']

                print(f"PAGES COVERED: {pages_covered} FOR ROOT {root}")
                self.base_url = data["url"]
                return pages_covered
            else:
                print(f"URL TO REMOVE: {self.base_url}")
                print(self.urls_to_scrape)
                self.base_url = self.urls_to_scrape[self.current_url_index]
                self.urls_to_scrape.remove(self.base_url)

        # If the loop terminated, it means that all active directories have been searched through
        return None

# Go through the category to correct and scrape missing content
class ShoppersCorrectSpider(scrapy.Spider):
    name = 'shoppers_correct'
    data = []
    urls_to_scrape = []
    products_to_scrape = []
    product_links = []
    all_sublinks = []
    current_url_index = 0
    current_page = 0
    current_product_index = 0
    current_sublink_index = 0
    current_category = ''
    retries = 0
    retry_thresh = 5

    def __init__(self, path_to_correct="Beauty", pages_to_scrape='all', current_page=0, start_x=0, start_y=0):
        super().__init__()
        self.pages_to_scrape = pages_to_scrape
        self.path_to_correct = path_to_correct
        self.current_page = int(current_page)
        self.driver = None
        self.start_x = int(start_x)
        self.start_y = int(start_y)

    def start_requests(self):
        self.current_page += 1
        yield from self.correct_file(path=self.path_to_correct)

    # Replace with saving directly to firebase
    def save_by_item(self, data, page=None, overwrite_file=False, base_path=None):
        # Save each page
        print(base_path)
        if base_path is None and self.current_category is not None:
            base_path = fr'./{self.store}/{self.current_category}'
        if page is None:
            filename = fr"{base_path}"
        else:
            filename = fr"{base_path}/page_{page}.jsonl"

        print(base_path)
        with open(filename, "a", encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')

    def get_details(self, response):
        driver = response.request.meta['driver']
        base_path = 'div[id="__next"] > div > div'
        driver.execute_script("document.body.style.zoom='50%'")

        try:
            wait = WebDriverWait(driver, timeout=15)
            # Move the mouse like a human
            # action = ActionChains(driver)
            # x_i, y_i = b_spline_mouse()
            # for mouse_x, mouse_y in zip(x_i, y_i):
            #     action =  ActionChains(driver)
            #     action.move_by_offset(mouse_x,mouse_y);
            #     action.perform();
            #     print(mouse_x, mouse_y)
            current_handles = driver.window_handles
            # driver.switch_to.window(current_handles[0])

            all_handles = driver.window_handles

            # Assuming the previous tab is the first handle in the list
            previous_tab_handle = all_handles[0]

            # Switch to the previous tab
            driver.switch_to.window(previous_tab_handle)
            time.sleep(1)

            # Close the previous tab
            driver.switch_to.window(all_handles[-1])

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{base_path}")))  #> ")))
            print("BASE")
            # Get html
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[id="__next"] > div > div > div > div > nav[data-testid="breadcrumbs"] > ul > li > a')))
            print("CAT")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.plp__container__2JOqx")))
            print("DESC")
        except:
            print(f"Timeout exception for {response.meta["product_data"]['productUrl']}")
            if self.retries == self.retry_thresh:
                with open(os.path.join(self.path_to_correct, 'correct_links.json'), "w+", encoding='utf-8') as f:
                    json.dump({"all_sublinks": self.all_sublinks, "index": self.current_product_index - self.retry_thresh}, f)
                raise Exception("Retries exceeded, browser blocked. Restarting chrome...")
            yield self.visit_next_product()

        # Note: Selectors are used when we are unsure if a value exists or not.
        # Selenium methods are better for when you want to wait for rendered content.
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)
        # Get html
        category = driver.find_elements(By.CSS_SELECTOR, 'div[id="__next"] > div > div > div > div > nav[data-testid="breadcrumbs"] > ul > li > a')
        description = sel.css(f'{base_path} > div > div > div > div > div > div.plp__description__2M_zG').get()
        productNum = sel.css(f'{base_path} > div > div > div > div > div.plp__descriptionContainer__mQOMf > p.plp__body__3TvTa').get()

        category_list = [c.text for c in category if c.text != 'Home']

        description = None if description == None else Selector(text=description).xpath('//text()').extract()
        productNum = None if productNum == None else Selector(text=productNum).xpath('//text()').extract()
        description = None if description is None or len(description) == 0 else description[0]
        productNum = None if productNum is None or len(productNum) == 0 else "".join(re.findall(r'\d', productNum[0]))

        # Expand the nutrition facts section, if possible
        # If nutrition facts do not exist, discard ingredients and nutrition
        # This is mostly to ensure compatibaility with non food items (like hygiene products)
        final_data = {}
        ingredients_path = f'{base_path} > div > div > div > div.plp__container__2JOqx > div[data-testid="accordionSection"] > div:nth-child(3)'
        ingredients_button = sel.css(ingredients_path).get()
        if ingredients_button is None:
            final_data = {
                    **response.meta["product_data"],
                    "category": category_list,
                    'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                    **{"details": {
                    "description": description,
                    "productNumber": productNum 
                    }
                }
            }
        else: 
            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'{ingredients_path} > div.lds__accordion__header-container > div')))
            driver.execute_script("arguments[0].click();", button)

            # Only ingredients are available, no nutrition facts
            ingredients = sel.css(f'{ingredients_path} > div > div > div.plp__body__3TvTa').get()
            ingredients = Selector(text=ingredients).xpath('//text()').extract()[0]
            # Merge the product data gotten from the initial homepage scrape with the product data.
            final_data = {
                        **response.meta["product_data"],
                        "category": category_list,
                        'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                        **{"details": {
                        "description": description,
                        "productNumber": productNum,
                        "ingredients": [] if ingredients is None else re.split(r', (?![^()]*\))', ingredients), # Splits according to commas that aren't in brackets, empty list is there for redundancy
                    }
                }
            }
        
        # Remove any fields that may be None to save space
        final_data['details'] = {k: v for k, v in final_data['details'].items() if v != None and v != ''}
        # Save to JSON. In the future, this will either be removed completely, or modified to write to a database.
        self.save_by_item(final_data, page=None, base_path=response.meta.get('path'))
        yield from self.visit_next_product()

    def correct_file(self, path):
        print("CORRECTING")
        # Rough ballpark estimate of how many files were corrupted
        max_pages = 120
        c = 0

        for root, _, curdir in os.walk(path):
            curdir = [i for i in curdir if i != 'correct_links.json']
            if len(curdir) == 0:
                continue
            print("FILES:", root, curdir)
            for file in curdir:
                if c >= max_pages:
                    break
                with open(os.path.join(root, file), 'r') as f:
                    lines_to_correct = []
                    lines = f.readlines()

                    for i, line in enumerate(lines):
                        print(i)
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as e:
                            print("JSON PARSE ERROR:")
                            print("Line:", i)
                            print("Error:", e)
                            print("Problematic line:", line)
                            if len(line) > 1550:
                                print("Characters around position 1550:")
                                start = max(0, 1545)
                                end = min(len(line), 1555)
                                print("Context:", line[start:end])
                            # Skip this malformed line
                            continue
                        except Exception as e:
                            print("UNEXPECTED ERROR:")
                            print("Line:", i)
                            print("Error:", e)
                            print("Line content:", line)
                            continue
                        
                        print(data.get("category"))
                        if data["details"].get("ingredients") is None or data.get("category") == []:
                            print("AAAAA")
                            lines_to_correct.append(line)

                c += 1   
                if len(lines_to_correct) > 0:
                    file_to_correct = os.path.join(root, file)
                    self.all_sublinks.append((file_to_correct, lines_to_correct))

        print("ALL SUBLINKS:", self.all_sublinks)
        if not os.path.exists(os.path.join(self.path_to_correct, 'correct_links.json')):
            with open(os.path.join(self.path_to_correct, 'correct_links.json'), 'w+') as f:
                json.dump({"all_sublinks": self.all_sublinks, "index": 0}, f)

        with open(os.path.join(self.path_to_correct, 'correct_links.json'), 'r') as f:
            data = json.load(f)
            self.all_sublinks = data["all_sublinks"]
            self.current_sublink_index = data["index"]

        with open(os.path.join(self.path_to_correct, 'correct_links.json'), 'w+') as f:
            json.dump({"all_sublinks": self.all_sublinks, "index": self.current_sublink_index}, f)

        yield from self.visit_page_to_correct()
    
    def visit_page_to_correct(self):
        if self.current_sublink_index >= len(self.all_sublinks):
            print("No more files to correct")
            return
            
        file_to_correct, lines_to_correct = self.all_sublinks[self.current_sublink_index]
        self.lines_to_correct = lines_to_correct
        self.file_to_correct = file_to_correct
        self.current_nested_correct_index = 0
        with open(file_to_correct, 'r') as f:
            lines = f.readlines()
        
        os.remove(file_to_correct)

        self.current_sublink_index += 1
        for line in lines_to_correct:
            if line in lines:
                lines.remove(line)

        with open(file_to_correct, 'a') as f:
            for line in lines:
                try:
                    data = json.loads(line)
                    json.dump(data, f)
                    f.write('\n')
                except json.JSONDecodeError as e:
                    print(f"Skipping malformed line when rewriting: {e}")
                    continue

        yield from self.visit_next_product()

    def visit_next_product(self):
        if self.current_nested_correct_index < len(self.lines_to_correct):
            line = self.lines_to_correct[self.current_nested_correct_index]
            try:
                data = json.loads(line)
                product_data = {
                            'productName': data["productName"],
                            'source': data["source"],
                            'productUrl': data["productUrl"],
                            'imageUrl': data["imageUrl"]}
                self.current_nested_correct_index += 1
                yield SeleniumRequest(
                    url=data["productUrl"],  # Fixed: was undefined 'url'
                    callback=self.get_details,
                    wait_time=10,
                    dont_filter=True,
                    meta={
                        'product_data': product_data,
                        'overwrite': True,
                        'path': self.file_to_correct
                    })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing line for correction: {e}")
                self.current_nested_correct_index += 1
                # Continue with next line
                yield from self.visit_next_product(file_to_correct=self.file_to_correct)
        else:
            # Move to next file if available
            if self.current_sublink_index < len(self.all_sublinks):
                yield from self.visit_page_to_correct()
            else:
                print("Finished correcting all files")
                return
