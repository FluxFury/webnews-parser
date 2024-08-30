from typing import Any
from scrapy import Spider, Request
from scrapy.http import Response


class CSpMatchesSpider(Spider):
    name = "CSpMatchesSpider"
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': None,
            'MainParserDirectory.middlewares.StealthMiddleware': 542,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'MainParserDirectory.middlewares.TooManyRequestsRetryMiddleware': 543,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'HTTPCACHE_ENABLED': False,
        'USER_AGENT': None,
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        'REACTOR_THREADPOOL_MAXSIZE': 20
    }

    def start_requests(self):
        url_array = []
        for page_num in range(1, 5):
            url_array.append("https://escorenews.com/ru/csgo/matches?s2=" + str(page_num))
        for url in url_array:
            yield Request(url=url, callback=self.parse)

    def _css_mutator(self, selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder if placeholder else ''
    def parse(self, response: Response, **kwargs: Any) -> Any:
        for match in response.css('div#matches_s2.flex-table a.article'):
            score = self._css_mutator('div.teams div.score span.type0::text', match).split(':')
            yield {
                'date': match.css('i.sct::attr(datetime)').get(),
                'team1': match.css('div.teams span:nth-child(1) b::text').get(),
                'team1_score': score[0].strip(),
                'team2_score': score[1].strip(),
                'team2': match.css('div.teams span:nth-child(3) b::text').get(),
            }
