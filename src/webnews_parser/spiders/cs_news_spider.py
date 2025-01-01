import os
import random
from html import unescape
from typing import Any, Iterator

from dotenv import load_dotenv
from scrapy import Request, Spider
from scrapy.http import Response

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSNewsItem
from ..loaders import CSNewsItemLoader
from ..utils.spider_utils import clean_text


class CSNewsSpider(Spider):
    """
    A spider to scrape and parse CS:GO news articles.

    Fetches news articles including headers, text content, and metadata.
    """

    name: str = "CSNewsSpider"
    load_dotenv()
    
    custom_settings: dict[str, Any] = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "webnews_parser.middlewares.FilterCSNewsURLMiddleware": 1,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSNewsPostgresPipeline": 100,
        },
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "USER_AGENT": None,
        "DOWNLOAD_TIMEOUT": 120,
        "DB_URL": os.getenv("DB_URL"),
        "HTTPCACHE_ENABLED": True,
        "CONCURRENT_REQUESTS": 8,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)

    def start_requests(self) -> Iterator[Request]:
        """
        Start the spider by issuing requests to news archive pages.

        Yields:
            Request: Initial requests to start crawling.

        """
        url_array = ["https://www.hltv.org/news/archive/2024/december"]
        for url in url_array:
            yield Request(url=url, callback=self.parse, meta={"no_wait_until_networkidle": True})

    def parse(self, response: Response, **kwargs: Any) -> Iterator[Request]:
        """
        Parse the news archive page and generate requests for individual news articles.

        Args:
            response (Response): The response containing the news archive.
            **kwargs: Additional keyword arguments.

        Yields:
            Request: Requests for individual news articles.

        """
        for paragraph in response.css("a.newsline.article"):
            next_url = response.urljoin(url=paragraph.css("::attr(href)").get())
            if next_url:
                rel_url = paragraph.css("::attr(href)").get()
                yield Request(
                    url=next_url,
                    callback=self.parse_news,
                    cb_kwargs={"rel_url": rel_url},
                    meta={"no_wait_until_networkidle": True}
                )

    def parse_news(self, response: Response, **kwargs: Any) -> Iterator[CSNewsItem]:
        """
        Parse individual news articles and extract content.

        Args:
            response (Response): The response containing the news article.
            **kwargs: Additional keyword arguments.

        Yields:
            CSNewsItem: Processed news article item.

        """
        # Extract header text
        news_string = (
            clean_text(response.css("p.headertext::text").get())
            if response.css("p.headertext::text")
            else ""
        )

        # Extract article paragraphs
        paragraph_list = [
            clean_text(piece.xpath("string()").get())
            for piece in response.css("p.news-block")
        ]

        # Create and populate the item loader
        loader = CSNewsItemLoader(item=CSNewsItem())
        loader.add_value("header", news_string)
        loader.add_value("text", paragraph_list)
        loader.add_value("url", response.cb_kwargs.get("rel_url"))
        loader.add_value(
            "news_creation_time",
            response.xpath('//div[@class="date"]/@data-unix').get()
            or response.xpath('//div[@class="news-with-frag-date"]/@data-unix').get()
        )

        if paragraph_list:
            yield loader.load_item()
