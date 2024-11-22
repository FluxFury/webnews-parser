# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import asyncio
import logging
from random import choice

from flux_orm.models.models import RawNews
from flux_orm.database import new_session
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.exceptions import IgnoreRequest
from scrapy.http import HtmlResponse
from scrapy.utils.response import response_status_message
from sqlalchemy import select
from undetected_playwright.async_api import async_playwright


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
        if request.meta.get("dont_retry", False):
            return response

        if response.status in self.retry_http_codes:
            if response.status == 429:
                retry_after = response.headers.get("retry-after")
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    delay = self.DEFAULT_DELAY
                else:
                    delay = min(self.MAX_DELAY, retry_after)
                spider.logger.info(f"Retrying {request} in {delay} seconds.")

                await async_sleep(delay)

            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response

        return response


class StealthMiddleware:

    async def block_images_and_unnecessary_elements(self, route, blocked_resources):
        if route.request.resource_type in self.blocked_resources:
            await route.abort()
        else:
            await route.continue_()
    async def _fetch(self, request, blocked_resources):
        async with async_playwright() as p:
            USER_AGENT = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"]
            args = ["--disable-blink-features=AutomationControlled"]
            browser = await p.chromium.launch(headless=True, args=args)
            context = await browser.new_context(
                user_agent=choice(USER_AGENT),
                locale="en-US",
            )

            page = await context.new_page()
            page.set_default_timeout(120000)
            #await page.route("**/*", block_images_and_unnecessary_elements(blocked_resources))
            await page.goto(request.url)
            await asyncio.sleep(10)
            content = await page.content()
            await browser.close()
            return content

    async def process_request(self, request, spider):
        blocked_resources = ["image", "font", "stylesheet"]
        if "hltv.org" in request.url:
            blocked_resources = []
        content = await self._fetch(request, blocked_resources)
        return HtmlResponse(
            url=request.url,
            body=content,
            encoding="utf-8",
            request=request
        )


class FilterCSNewsURLMiddleware:

    async def process_request(self, request, spider):
        async with new_session() as session:
            short_url = request.url.split("https://www.hltv.org")[-1]
            stmt = select(RawNews).filter_by(url=short_url)
            news = await session.execute(stmt)
            news = news.scalars().first()
            if news and news.text:
                spider.logger.info(f"URL {request.url} already in the database. Skipping.")
                raise IgnoreRequest
        return None