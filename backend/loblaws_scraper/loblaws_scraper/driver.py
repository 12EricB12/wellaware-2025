from scrapy.crawler import CrawlerProcess
from spiders import loblaws_spider

companies = ["loblaws", "nofrills", "realcanadiansuperstore"]

process = CrawlerProcess(settings={
    "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
    "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    "SELENIUM_DRIVER_NAME": 'chrome',
    "SELENIUM_DRIVER_EXECUTABLE_PATH": 'C:/Users/Ericb/Documents/wellaware/backend/loblaws_scraper/loblaws_scraper/chromedriver.exe',
    "LOG_LEVEL": 'WARNING',
    "AUTOTHROTTLE_ENABLED": True,
    "SELENIUM_DRIVER_ARGUMENTS": ['--headless']
})
process.crawl(loblaws_spider.LoblawsSpider, store='realcanadiansuperstore')
process.start()

# Command line script:
# scrapy crawl loblaws -a store='realcanadiansuperstore' -a non_food_categories='{'Baby': ['Diapers, Wipes & Training Pants', 'Nursing & Feeding Accessories', 'Baby Toiletries', 'Baby Food & Snacks', 'Baby Formula'], 'Pet Food & Supplies': 'all', 'Personal Care & Beauty': 'all', 'Health & Wellness': 'all'}' -a scrape_non_food_only=True 
