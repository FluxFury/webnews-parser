# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import time
from scrapy import signals
from scrapy.http import HtmlResponse
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import asyncio
from undetected_playwright.async_api import async_playwright, Playwright
from random import choice
from .spiders.cs_live_scheduled_matches_tournaments_parser import USER_AGENT


class DownloaderMiddleware:
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


# class SeleniumMiddleware:
#     def __init__(self):
#         self.driver = Driver(uc=True, headless=True)
#
#     def process_request(self, request, spider):
#         self.driver.get(request.url)
#         time.sleep(0.5)
#         return HtmlResponse(self.driver.current_url, body=self.driver.page_source, encoding='utf-8', request=request)
#
#     def spider_closed(self):
#         self.driver.close()
#         self.driver.quit()


async def async_sleep(delay, return_value=None):
    await asyncio.sleep(delay)
    return return_value


class TooManyRequestsRetryMiddleware(RetryMiddleware):
    """
    Modifies RetryMiddleware to delay retries on status 429.
    """

    DEFAULT_DELAY = 60  # Delay in seconds.
    MAX_DELAY = 600  # Sometimes, RETRY-AFTER has absurd values

    async def process_response(self, request, response, spider):
        """
        Like RetryMiddleware.process_response, but, if response status is 429,
        retry the request only after waiting at most self.MAX_DELAY seconds.
        Respect the Retry-After header if it's less than self.MAX_DELAY.
        If Retry-After is absent/invalid, wait only self.DEFAULT_DELAY seconds.
        """

        if request.meta.get('dont_retry', False):
            return response

        if response.status in self.retry_http_codes:
            if response.status == 429:
                retry_after = response.headers.get('retry-after')
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    delay = self.DEFAULT_DELAY
                else:
                    delay = min(self.MAX_DELAY, retry_after)
                spider.logger.info(f'Retrying {request} in {delay} seconds.')

                await async_sleep(delay)

            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response

        return response


class StealthMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    async def _fetch(self, request):
        async with async_playwright() as p:
            args = ["--disable-blink-features=AutomationControlled"]
            browser = await p.chromium.launch(headless=True, args=args)
            context = await browser.new_context(
                user_agent=choice(USER_AGENT),
                locale='en-US',
                timezone_id='Europe/Helsinki'
            )

            page = await context.new_page()
            page.set_default_timeout(60000)
            await page.goto(request.url, wait_until='domcontentloaded')
            await asyncio.sleep(6)
            # await page.screenshot(path='screenshot.png')
            # await asyncio.sleep(2)
            #
            # await page.mouse.move(0, 0)
            # await page.mouse.move(340, 285)
            # await page.mouse.down()
            # await asyncio.sleep(0.1)
            # await page.mouse.up()
            # await asyncio.sleep(6)
            content = await page.content()
            await browser.close()
            return content

    async def process_request(self, request, spider):
        content = await self._fetch(request)

        return HtmlResponse(
            url=request.url,
            body=content,
            encoding='utf-8',
            request=request
        )