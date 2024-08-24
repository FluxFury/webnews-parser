from typing import Any
from scrapy import Spider, Request
from scrapy.http import Response


class CSpMatchesSpider(Spider):
    name = "CSpMatchesSpider"
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
        for page_num in range(1, 5):
            url_array.append("https://escorenews.com/ru/csgo/matches?s2=" + str(page_num))
        for url in url_array:
            yield Request(url=url, callback=self.parse)


    def parse(self, response: Response, **kwargs: Any) -> Any:
        for match in response.css('div#matches_s2.flex-table a.article'):
            score = match.css('div.teams div.score span.type0::text').get().split(':')
            yield {
                'date': match.css('i.sct::attr(datetime)').get(),
                'team1': match.css('div.teams span:nth-child(1) b::text').get(),
                'team1_score': score[0].strip(),
                'team2_score': score[1].strip(),
                'team2': match.css('div.teams span:nth-child(3) b::text').get(),
            }
