import os
from html import unescape
from typing import Any

from dotenv import load_dotenv
from scrapy import Request, Spider
from scrapy.http import Response

from ..items import CSNewsItem


class CSNewsSpider(Spider):
    name = "CSNewsSpider"
    load_dotenv()
    custom_settings = {"DOWNLOADER_MIDDLEWARES": {"scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
                                                  "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
                                                  "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
                                                  "webnews_parser.middlewares.FilterCSNewsURLMiddleware": 1,
                                                  "webnews_parser.middlewares.StealthMiddleware": 542,
                                                  "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
                                                  "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810, },
                       "ITEM_PIPELINES": {
                           "webnews_parser.pipelines.CSNewsPostgresPipeline": 100,
                       },
                       "LOG_LEVEL": "INFO",
                       "COOKIES_ENABLED": False,
                       "USER_AGENT": None,
                       "DOWNLOAD_TIMEOUT": 120,
                       "REACTOR_THREADPOOL_MAXSIZE": 20,
                       "DB_URL": os.getenv("DB_URL"),
                       "HTTPCACHE_ENABLED": True,
                       }

    def start_requests(self):

        url_array = [
            "https://www.hltv.org/news/archive/2024/november"]
        for url in url_array:
            yield Request(url=url, callback=self.parse)

    @staticmethod
    def _clean_text(text):
        return unescape(text).replace("\u2060", "").replace("\\\\", "").replace("\\", "") \
            .replace("]", "").replace("[", "").replace("\\\\u2019", "'").strip()  # Removal of \u2060, \, [, ]

    def parse(self, response: Response, **kwargs: Any) -> Any:
        for paragraph in response.css("a.newsline.article"):
            next_url = response.urljoin(url=paragraph.css("::attr(href)").get())
            if next_url:
                rel_url = paragraph.css("::attr(href)").get()
                yield Request(url=next_url,
                              callback=self.parse_news,
                              cb_kwargs={"rel_url": rel_url}
                              )

    def parse_news(self, response, **kwargs):
        news_string = self._clean_text(response.css("p.headertext::text").get()) \
            if response.css("p.headertext::text") else ""
        paragraph_list = []
        for piece in response.css("p.news-block"):
            paragraph_list.append(self._clean_text(piece.xpath("string()").get()))
        data_dict = {"header": news_string, "text": paragraph_list, "url": response.cb_kwargs.get("rel_url"),
                     "unix_time": response.xpath('//div[@class="date"]/@data-unix').get() \
                         if response.xpath('//div[@class="date"]/@data-unix').get() \
                         else response.xpath('//div[@class="news-with-frag-date"]/@data-unix').get()}
        data_item = CSNewsItem()
        data_item.update(data_dict)
        if paragraph_list:
            yield data_item
