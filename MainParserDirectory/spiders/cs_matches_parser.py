from typing import Any

from scrapy import Spider
from scrapy_selenium import SeleniumRequest
from scrapy.http import Response


class CSMatchesSpider(Spider):
    name = "CSMatchesSpider"
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 401,
            'MainParserDirectory.middlewares.SeleniumMiddleware': 543,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        }
    }

    def start_requests(self):
        url_array = []
        for page_num in range(1, 10):
            url_array.append("https://escorenews.com/ru/csgo/matches?s1=" + str(page_num))
        for url in url_array:
            yield SeleniumRequest(url=url, callback=self.parse, wait_time=5)

    def parse(self, response: Response, **kwargs: Any) -> Any:
        matches_type1 = response.css('a.article.type1[data-test-id="matches-block-item"]')
        matches = response.css('a.article[data-test-id="matches-block-item"]')
        if not matches_type1 or not matches:
            self.logger.warning("No matches found with the provided selector.")

        for match_type1 in matches_type1:
            match_url = match_type1.css('::attr(href)').get()

            if match_url.count("tbd") < 2:
                yield {'match_url': match_url}

        for match in matches:
            match_url = match.css('::attr(href)').get()

            if match_url.count("tbd") < 2:
                yield {'match_url': match_url}
