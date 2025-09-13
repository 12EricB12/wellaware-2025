from numpy.ma import product
import scrapy
import re
import time
import json
import os

from datetime import datetime
from selenium import webdriver
from scrapy.selector import Selector
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from scrapy_selenium import SeleniumRequest

class LoblawsSpider(scrapy.Spider):
    name = 'loblaws'

    # GLOBAL DATA FIELDS FOR VISITING PRODUCTS WHEN SCRAPING
    data = []
    product_links = []
    all_sublinks = []
    all_non_food_tabs = []

    # GLOBAL COUNTER/NAME FIELDS
    current_product_index = 0
    current_sublink_index = 0
    current_category_index = 0
    current_category = None
    current_sublink = None
    header = None
    
    # NON FOOD SCRAPING
    nested_page = False
    current_nested_correct_index = 0

    # CORRECT MODE
    lines_to_correct = []

    def __init__(self, store, current_page=0, non_food_categories={}, scrape_non_food_only=False, pages_to_scrape='all', correct_mode=False, path_to_correct=""):
        super().__init__()
        self.store = store
        self.baseURL = f'https://www.{store}.ca'
        self.pages_to_scrape = pages_to_scrape
        self.scrape_non_food_only = bool(scrape_non_food_only)
        self.current_page = int(current_page)
        self.correct_mode = bool(correct_mode)
        self.path_to_correct = path_to_correct

        if len(non_food_categories) != 0:
            with open(non_food_categories, 'r') as f:
                self.non_food_categories = json.load(f)
        else:
            self.non_food_categories = non_food_categories
        self.non_food_categories_keys = list(self.non_food_categories.keys())

    def start_requests(self):
        if self.correct_mode is True:
            print("CORRECTING START")
            yield from self.correct_file(path=self.path_to_correct)
        else:
            if self.scrape_non_food_only is False:
                self.current_page += 1
                yield SeleniumRequest(
                    wait_time=15,
                    url=f'{self.baseURL}/en/food/c/27985?page={self.current_page}',
                    callback=self.parse,
                    meta={'page': 1}
                )
            else:
                yield SeleniumRequest(
                    wait_time=15,
                    url=self.baseURL,
                    callback=self.parse_non_food,
                    meta={'nested': False}
                )

    # Removes any non alphanumeric characters and reformats the string to follow camel casing convention for JSON
    def format_json(self, text):
        text_alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', (text))
        return (text_alphanumeric[0].lower() + text_alphanumeric[1:]).replace(" ", "")

    # Replace with saving directly to firebase
    def save_by_item(self, data, page=None, overwrite_file=False, base_path=None):
        # Save each page
        
        if base_path is None and self.current_category is None:
            base_path = fr'./{self.store}/Food'
        if base_path is None and self.current_category is not None:
            base_path = fr'./{self.store}/{self.header}/{self.current_category}'

        if not os.path.exists(base_path):
            os.makedirs(base_path)
        
        if page is None:
            filename = fr"{base_path}"
        else:
            filename = fr"{base_path}/page_{page}.jsonl"

        with open(filename, "a", encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')

    # Get the details (ingredients, nutrition, product number/upc/item number, etc.) from each item's page
    def get_details(self, response):
        driver = response.request.meta['driver']
        base_path = 'main[class="site-content"] > div > div > div.product-details-accordion'

        # Wait for the page to load. Due to location, the item may not load. This is to ensure the entire program doesn't crash.
        try:
            wait = WebDriverWait(driver, timeout=20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{base_path}")))  #> ")))
            # Get html
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'main[class="site-content"] > div > div > div.breadcrumbs > ul > li > a')))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{base_path} > div.product-details-accordion__item")))
        except TimeoutException:
            print(f"TimeoutException for {response.meta["product_data"]['productUrl']}")

        # Note: Selectors are used when we are unsure if a value exists or not.
        # Selenium methods are better for when you want to wait for rendered content.
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)
        description = sel.css(f'{base_path} > div.product-details-accordion__item > div.product-details-page-description > div.product-details-page-description__body > div > div > div').get()
        productNum = sel.css(f'{base_path} > div > div.product-details-page-description > div > div > p.product-number').get()
        category = sel.css('main[class="site-content"] > div > div > div.breadcrumbs > ul > li > a').getall()

        category_list = [Selector(text=c).xpath('//text()').extract() for c in category] if len(category) > 0 else []
        category_list = [c[0] for c in category_list if c[0] != 'Home']
        description = None if description == None else Selector(text=description).xpath('//text()').extract()
        productNum = None if productNum == None else Selector(text=productNum).xpath('//span//text()').extract()
        description = None if description is None or len(description) == 0 else description[0]
        productNum = None if productNum is None or len(productNum) == 0 else productNum[0]

        # Expand the nutrition facts section, if possible
        # If nutrition facts do not exist, discard ingredients and nutrition
        # This is mostly to ensure compatibaility with non food items (like hygiene products)
        final_data = {}
        nutrition_button = sel.css(f'{base_path} > div > div.product-details-page-nutrition-info > button').get()
        if nutrition_button is None:
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
            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'{base_path} > div > div.product-details-page-nutrition-info > button ')))
            driver.execute_script("arguments[0].click();", button)

            ingredients = sel.css(f'{base_path} > div > div.product-details-page-nutrition-info > div > div > div.product-details-page-info-layout.product-details-page-info-layout--ingredients > div::text').get()
            nutrition_base_path = f'{base_path} > div > div.product-details-page-nutrition-info > div > div > div.product-details-page-info-layout.product-details-page-info-layout--nutrition > div'
            
            nutrition_facts = sel.css(f'{nutrition_base_path} > div.product-nutrition > div.product-nutrition__nutrients-per-serving-table > div.product-nutrition__nutrients-per-serving-column > div').getall()
            serving_size = sel.css(f'{nutrition_base_path} > div.product-nutrition > div.product-nutrition__food-labels > ul > li > span').get()
            nutrients = {}

            # Go through every one of the nutrition facts and get their data
            for item in nutrition_facts:
                s = Selector(text=item)
                parent_elem = s.css('div > div.nutrient-per-serving__label').get()
                if parent_elem is None:
                    continue
                
                # Get all the nutrition facts texts
                parent = Selector(text=parent_elem).xpath('//span//text()').extract()
                nested = {}
                current_level = 2
                prev_level = s.css(f'div.nutrient-per-serving--level-{current_level - 1} > div.nutrient-per-serving__label').get()
                next_level = s.css(f'div.nutrient-per-serving--level-{current_level}').getall()

                # Nutrition facts may have "levels" depending on what it is (ex. fats -> saturated + trans)
                # This loop handles finding all the nested nutrients
                while len(next_level) != 0:
                    for level in next_level:
                        child = Selector(text=level).xpath('//text()').extract()
                        if len(child) < 2:
                            continue
                        nested[self.format_json(child[0])] = ", ".join(child[1:])

                    current_level += 1
                    total = Selector(text=prev_level).xpath('//text()').extract()
                    nested["total"] = ", ".join(total[1:])
                    prev_level = s.css(f'div.nutrient-per-serving--level-{current_level - 1} > div.nutrient-per-serving__label').get()
                    next_level = s.css(f'div.nutrient-per-serving--level-{current_level}').getall()
                if len(nested) == 0:
                    nutrients[self.format_json(parent[0])] = ", ".join(parent[1:])
                else:
                    nutrients[self.format_json(parent[0])] = nested

            # Merge the product data gotten from the initial homepage scrape with the product data.
            final_data = {
                        **response.meta["product_data"],
                        "category": category_list,
                        'scrapedAt': datetime.now().strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + "Z"),
                        **{"details": {
                        "description": description,
                        "productNumber": productNum,
                        "ingredients": [] if ingredients is None else re.split(r', (?![^()]*\))', ingredients), # Splits according to commas that aren't in brackets, empty list is there for redundancy
                        "nutritionFacts": {
                            "servingSize": "".join(Selector(text=serving_size).xpath('//text()').extract()),
                            "nutrition": nutrients # [Selector(text=item.get_attribute("innerHTML")).xpath('//text()').extract() for item in nutrition_facts] # TO IMPLEMENT
                        }
                    }
                }
            }
        
        # Remove any fields that may be None to save space
        final_data['details'] = {k: v for k, v in final_data['details'].items() if v != None and v != ''}
        # Save to JSON. In the future, this will either be removed completely, or modified to write to a database.
        overwrite_file = response.meta['overwrite']
        self.save_by_item(final_data, response.meta.get('page'), overwrite_file=overwrite_file, base_path=response.meta.get('path'))
        yield from self.visit_next_product()

    # Sometimes, the non food categories have extra sections after clicking "see all". This is to navigate those sections
    def visit_nested_category(self):
        print("Detected Indiana scroll container - switching to non-food parsing")
        # Set up the state for non-food parsing
        self.scrape_non_food_only = True
        self.current_page = 0
        self.current_product_index = 0
        # Get the current URL to use as the base for non-food parsing
        _, current_url = self.all_sublinks[self.current_sublink_index]
        yield SeleniumRequest(
            wait_time=15,
            url=current_url,
            callback=self.parse_non_food_page,
            meta={'nested': True}
        )
        
    # Normal food page parsing
    def parse(self, response):
        driver = response.request.meta['driver']
        base_path = 'div[data-testid="listing-page-container"]'
        
        wait = WebDriverWait(driver, timeout=30)
        
        # Sometimes displays a "no items are available" page -- strange error
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_path)))
        except Exception as e:
            print(e)
            yield self.visit_next_product()

        # Get html
        sel = Selector(text=driver.page_source) # Used for html attributes (like src, alt, etc.)
        if self.pages_to_scrape == 'all':
            all_pages = sel.css(f'{base_path} > div.css-0 > div.chakra-stack > nav > a.chakra-link').getall()
            all_pages = [Selector(text=page_num).xpath('//text()').extract()[0] for page_num in all_pages if len(extracted := Selector(text=page_num).xpath('//text()').extract()) != 0 and extracted[0].isdigit()]

            self.pages_to_scrape = 1 if len(all_pages) == 0 else max([int(page_num) for page_num in all_pages])
            print(f"PAGES TO SCRAPE: {self.pages_to_scrape}")

        # Some non food pages have extra nested layouts, this part of the code takes care of it
        if sel.css('div.indiana-scroll-container').get() is not None and self.scrape_non_food_only is True:
            yield from self.visit_nested_category()

        items = driver.find_elements(By.CSS_SELECTOR, f'{base_path} > div.css-0 > div[data-testid="product-grid-component"] > div.css-0')

        # Processing & Cleanup
        product_links = []
        for item in items:
            try:
                food = item.find_element(By.CSS_SELECTOR, 'div.css-yyn1h > div > div.css-qoklea > a > div.css-0')
            except Exception as e:
                print(f"Error in parsing function: \n {e}")
                print(item.get_attribute('innerHTML'))
                print(item.get_attribute('outerHTML'))
                continue

            sel = Selector(text=item.get_attribute("innerHTML"))

            # Go to the next page and grab other fields (description, nutrition, etc.)
            productURL = self.baseURL + sel.css('div.css-yyn1h > div > div.css-qoklea > a::attr(href)').get()
            product_data = {
                'productName': food.find_element(By.CSS_SELECTOR, 'h3').text,
                'source': self.store,
                'productUrl': productURL,
                'imageUrl': sel.css('div.css-yyn1h > div > div[data-testid="product-image"] > img::attr(src)').get(),
            }
            product_links.append((productURL, product_data))

        self.product_links = [(url, data) for url, data in product_links]
        yield from self.visit_next_product()
    
    # Visit each non food category, as defined in the non_food_category dictionary (usually saved as a JSON file)
    def parse_non_food(self, response):
        driver = response.request.meta['driver']
        base_path = 'div[data-testid="iceberg-root-layout"] > section[data-testid="iceberg-layout-header"] > div > div > header > div[data-testid="iceberg-nav-desktop"] > nav > div > div[data-testid="iceberg-masthead-left"] > div > ul > li'
        wait = WebDriverWait(driver, timeout=30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_path)))

        buttons = driver.find_elements(By.CSS_SELECTOR, f'{base_path}')
        non_food_button = [item for item in buttons if Selector(text=item.get_attribute('innerHTML')).xpath('//span//text()').extract()[0] == 'Home, Beauty & Baby'][0]
        non_food_button = non_food_button.find_element(By.CSS_SELECTOR, 'button')
    
        button_main = wait.until(EC.element_to_be_clickable(non_food_button))
        driver.execute_script("arguments[0].click();", button_main)

        # There is no all encompassing page for non-food items, so we must go by category instead
        base_tab_path = 'div > div[data-testid="iceberg-main-nav-l1-popover-content"] > div[data-testid="iceberg-main-nav-l2-tabs"] > div[role="tablist"]'
        tabs = driver.find_elements(By.CSS_SELECTOR, f'{base_tab_path} > button')
        
        if self.current_category_index < len(self.non_food_categories_keys):
            self.header = self.non_food_categories_keys[self.current_category_index]
            tabs_href = self.baseURL + self.non_food_categories[self.header]['url_to_scrape']
            yield SeleniumRequest(
                wait_time=15,
                url=tabs_href,
                callback=self.parse_non_food_page,
                meta={'nested': False}
            )
            time.sleep(5)

    # Parse non food only 
    def parse_non_food_page(self, response):
        driver = response.request.meta['driver']
        base_path = 'div[data-testid="listing-page-container"]'
        wait = WebDriverWait(driver, timeout=30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, base_path)))

        base_categories = driver.find_element(By.CSS_SELECTOR, f'{base_path} > div.css-0 > div > div > div > div > div')
        all_sublinks = []

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div > div.chakra-collapse > div > div[data-testid="link-list"] > div > ul > li > a')))
        all_buttons = base_categories.find_elements(By.CSS_SELECTOR, 'div > div.chakra-collapse > div > div[data-testid="link-list"] > div > ul > li')
        elem_list = [a for a in all_buttons if Selector(text=a.get_attribute('innerHTML')).xpath('//text()').extract()[0] == 'See All']
        headers = base_categories.find_elements(By.CSS_SELECTOR, 'p')
        for i, elem in enumerate(elem_list):
            # Check to see if the categories we want inside the page exist or not
            if self.non_food_categories[self.header]['categories'] == 'all' or headers[i].text in self.non_food_categories[self.header]['categories']:
                all_sublinks.append((headers[i].text, self.baseURL + Selector(text=elem.get_attribute('innerHTML')).css('a::attr(href)').get()))
            elif response.meta['nested']:
                all_sublinks.append((headers[i].text, self.baseURL + Selector(text=elem.get_attribute('innerHTML')).css('a::attr(href)').get()))
        
        self.all_sublinks = all_sublinks
        self.current_sublink_index = 0
        
        category, self.current_sublink = self.all_sublinks[self.current_sublink_index]
        self.current_category = category
        yield from self.visit_next_product()

    def correct_file(self, path):
        for root, _, curdir in os.walk(path):
            if len(curdir) == 0:
                continue
            print("FILES:", root, curdir)
            for file in curdir:
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
                        if data["details"].get("productNumber") is None or data.get("category") == []:
                            print("AAAAA")
                            lines_to_correct.append(line)
                    
                if len(lines_to_correct) > 0:
                    file_to_correct = os.path.join(root, file)
                    self.all_sublinks.append((file_to_correct, lines_to_correct))

        print("ALL SUBLINKS:", self.all_sublinks)
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
        # For correct mode only
        if self.correct_mode:
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
        # Normal food parsing functions
        # Keep visiting all the products until the end is reached, then go to the next page
        elif self.current_product_index < len(self.product_links):
            url, data = self.product_links[self.current_product_index]
            self.current_product_index += 1

            yield SeleniumRequest(
                url=url,
                callback=self.get_details,
                wait_time=45,
                dont_filter=True,
                meta={
                    'product_data': data,
                    'page': self.current_page,
                    'overwrite': False
                }
            )
        # Logic for going to the next page
        elif self.pages_to_scrape == 'all' or self.current_page < self.pages_to_scrape:
            self.current_product_index = 0
            self.current_page += 1
            if self.scrape_non_food_only is False:
                yield SeleniumRequest(
                    url=f'{self.baseURL}/en/food/c/27985?page={self.current_page}',
                    callback=self.parse,
                    wait_time=5,
                    meta={'page': self.current_page}
                )
            else:
                print("PARSING NOW!!")
                print(self.current_sublink)
                yield SeleniumRequest(
                    url=f'{self.current_sublink}?page={self.current_page}',
                    callback=self.parse,
                    wait_time=5,
                    meta={'page': self.current_page}
                )
        # NON FOOD SCRAPING FUNCTIONS
        #?????
        # Why does self.scrape_non_food_only not work here if its set to true in the constructor
        elif self.scrape_non_food_only:
            if len(self.all_sublinks) > 0 and self.current_sublink_index < len(self.all_sublinks) - 1:
                try:
                    print("REACHED")
                    self.current_sublink_index += 1
                    category, self.current_sublink = self.all_sublinks[self.current_sublink_index]
                    self.current_category = category
                    
                    self.current_product_index = 0
                    self.current_page = 1
                    self.pages_to_scrape = 'all'
                    yield SeleniumRequest(
                        url=f'{self.current_sublink}?page={self.current_page}',
                        callback=self.parse,
                        wait_time=5,
                        meta={'page': self.current_page}
                    )
                except Exception as e:
                    print(e)
                    print(self.scrape_non_food_only)
                    print(self.all_sublinks)
                    print(self.current_sublink_index)
                    print(self.all_sublinks[0])
            # Reached the end of the category
            elif self.current_sublink_index == len(self.all_sublinks) - 1:
                print("REACHED THE END")
                self.current_category_index += 1
                self.current_page = 0
                yield SeleniumRequest(
                    url=self.baseURL,
                    callback=self.parse_non_food,
                    wait_time=5,
                    meta={'page': self.current_page}
                )
            else:
                # No more sublinks to process, we're done with this category
                print("Finished processing all sublinks for current category")
