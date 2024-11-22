from typing import Any

from scrapy import Request, Spider
from scrapy.http import Response

from ..items import CSPMatchesItem


class CSpMatchesSpider(Spider):
    name = "CSpMatchesSpider"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.StealthMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSPastMatchesPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20
    }

    def start_requests(self):
        url_array = []
        for page_num in range(1, 5):
            url_array.append("https://escorenews.com/en/csgo/matches?s2=" + str(page_num))
        for url in url_array:
            yield Request(url=url, callback=self.parse)

    @staticmethod
    def _css_mutator(selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder or ""
    def parse(self, response: Response, **kwargs: Any) -> Any:
        for match in response.css("div#matches_s2.flex-table a.article.v_gl704"):
            score = self._css_mutator("div.teams div.score span.type0::text", match).split(":")
            data_dict = {
                "date": match.css("i.sct::attr(datetime)").get(),
                "team1": match.css("div.teams span:nth-child(1) b::text").get(),
                "team1_score": score[0].strip(),
                "team2_score": score[1].strip(),
                "team2": match.css("div.teams span:nth-child(3) b::text").get(),}
            data_item = CSPMatchesItem()
            data_item.update(data_dict)
            yield data_item
