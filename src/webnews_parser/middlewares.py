import asyncio
from random import choice

from flux_orm.database import new_session
from flux_orm.models.models import RawNews
from patchright._impl import _errors
from patchright.async_api import async_playwright
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.exceptions import IgnoreRequest
from scrapy.http import HtmlResponse
from scrapy.utils.response import response_status_message
from sqlalchemy import select


async def block_images_and_unnecessary_elements(route, spider):
    """
    Asynchronously block certain resource types based on spider configuration.

    Args:
        route: The route object from Playwright.
        spider: The spider instance containing blocked_resources configuration.

    Returns:
        None

    """
    blocked_resources = spider.blocked_resources
    if "hltv.org" in route.request.url:
        blocked_resources = []
    if route.request.resource_type in blocked_resources:
        await route.abort()
    else:
        await route.continue_()


async def start_playwright(
    spider,
    headless=True,
    channel="chromium",
    enable_js=True,
    wait_for_storage_state=True,
):
    """
    Asynchronously start a Playwright browser with the given spider configuration.

    Args:
        spider: The spider instance containing credentials and configuration.
        headless (bool): Whether to start the browser in headless mode.
        channel (str): Browser channel to use (e.g., "chromium").
        enable_js (bool): Whether to enable JavaScript in the browser context.
        wait_for_storage_state (bool): Whether to use spider.playwright_storage if available.

    Returns:
        (p, browser, context, page): The created Playwright instances

    """
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=headless, channel=channel, args=spider.browser_args
    )

    context = await browser.new_context(
        user_agent=spider.user_agent,
        locale="en-US",
        storage_state=spider.playwright_storage if wait_for_storage_state else None,
        java_script_enabled=enable_js,
        no_viewport=True,
    )
    context.set_default_timeout(100000)
    page = await context.new_page()
    return p, browser, context, page


async def shutdown_playwright(p_inst, browser, context):
    """
    Asynchronously close the Playwright browser, context, and page instances.

    Args:
        p_inst: The Playwright instance.
        browser: The Playwright browser instance.
        context: The Playwright context instance.

    """
    await context.close()
    await browser.close()
    await p_inst.stop()


async def get_content_with_playwright(request, p, browser, context, page, spider):
    """
    Asynchronously navigate to a URL using Playwright and return page content.

    Args:
        request: The Scrapy request object.
        p: The Playwright instance.
        browser: The Playwright browser instance.
        context: The Playwright context instance.
        page: The Playwright page instance.
        spider: The spider instance.

    Returns:
        str: The HTML content of the loaded page.

    """
    await page.route(
        "**/*", lambda route: block_images_and_unnecessary_elements(route, spider)
    )
    await page.goto(request.url)
    content = await page.content()
    await shutdown_playwright(p, browser, context)
    return content


async def async_sleep(delay, return_value=None):
    await asyncio.sleep(delay)
    return return_value


class TooManyRequestsRetryMiddleware(RetryMiddleware):
    """Modifies RetryMiddleware to delay retries on status 429."""

    DEFAULT_DELAY = 60  # Delay in seconds.
    MAX_DELAY = 600  # Sometimes, RETRY-AFTER has absurd values

    async def process_response(self, request, response, spider):
        """
        Like RetryMiddleware.process_response, but, if response status is 429.

        Retry the request only after waiting at most self.MAX_DELAY seconds.
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


class PatchrightMiddleware:
    async def _fetch(self, request, spider):
        """Fetch content using Playwright with stealth settings."""
        p, browser, context, page = await start_playwright(
            spider,
            headless=True,
            channel="chromium",
            enable_js=True,
            wait_for_storage_state=False,
        )

        try:
            await page.goto(request.url, wait_until="networkidle")
            await asyncio.sleep(request.meta.get("delay", 0))
            return await page.content()
        except _errors.TimeoutError as e:
            spider.logger.error(f"Timeout error: {e}")
            return None
        finally:
            await shutdown_playwright(p, browser, context)

    async def process_request(self, request, spider):
        content = await self._fetch(request, spider)
        if not content:
            return None

        return HtmlResponse(
            url=request.url, body=content, encoding="utf-8", request=request
        )


class FilterCSNewsURLMiddleware:
    async def process_request(self, request, spider):
        async with new_session() as session:
            short_url = request.url.split("https://www.hltv.org")[-1]
            stmt = select(RawNews).filter_by(url=short_url)
            news = await session.execute(stmt)
            news = news.scalars().first()
            if news and news.text:
                spider.logger.info(
                    f"URL {request.url} already in the database. Skipping."
                )
                raise IgnoreRequest
