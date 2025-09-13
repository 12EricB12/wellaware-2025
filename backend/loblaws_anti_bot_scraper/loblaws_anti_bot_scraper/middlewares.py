# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy_selenium import SeleniumMiddleware
import undetected_chromedriver as uc
from scrapy.http import HtmlResponse
from scrapy import signals
from scrapy_selenium import SeleniumMiddleware
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from scrapy_selenium.http import SeleniumRequest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from scrapy.exceptions import CloseSpider
import random
import time
import tempfile
import logging

class LoblawsAntiBotScraperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # maching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class LoblawsAntiBotScraperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)

class UndetectedSeleniumMiddleware:
    def __init__(self, driver_arguments=None, headless=False, version_main=None):
        print("UndetectedSeleniumMiddleware initialized")
        options = uc.ChromeOptions()
        self.version_main = version_main

        for arg in driver_arguments or []:
            options.add_argument(arg)

        # Initialize undetected-chromedriver
        self.driver = uc.Chrome(
            options=options,
            headless=headless,
            version_main=version_main  # match your Chrome version if needed
        )

    @classmethod
    def from_crawler(cls, crawler):
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS', [])
        headless = crawler.settings.getbool('HEADLESS', False)
        version_main = crawler.settings.getint("CHROME_VERSION_MAIN", None)

        return cls(
            driver_arguments=driver_arguments,
            headless=headless,
            version_main=version_main
        )

    def process_request(self, request, spider):
        logging.info(f"UndetectedSeleniumMiddleware: Processing URL {request.url}")
        # Only handle SeleniumRequest
        if not isinstance(request, SeleniumRequest):
            return None

        try:
            logging.info("Opening page in undetected ChromeDriver")
            self.driver.get(request.url)
            logging.info("Page opened, waiting if necessary...")

            # Attach driver so spider can interact with it
            request.meta['driver'] = self.driver

            # Rotate user agents
            with open("user-agents.txt", 'r') as f:
                user_agents = f.readlines()

            request.headers['User-Agent'] = random.choice(user_agents)

            # Handle waits if defined in the request
            if request.wait_until:
                WebDriverWait(self.driver, request.wait_time).until(
                    request.wait_until
                    if callable(request.wait_until)
                    else EC.presence_of_element_located(request.wait_until)
                )
            elif request.wait_time:
                self.driver.implicitly_wait(request.wait_time)

            body = self.driver.page_source.encode('utf-8')
            return HtmlResponse(
                self.driver.current_url,
                body=body,
                encoding='utf-8',
                request=request
            )
        except (TimeoutException, WebDriverException) as e:
            logging.error(f"Selenium failed on {request.url}: {e}")
            raise CloseSpider(f"Selenium fatal error: {e}")

    def spider_closed(self):
        self.driver.quit()
