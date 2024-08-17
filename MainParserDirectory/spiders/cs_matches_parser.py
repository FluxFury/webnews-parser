from typing import Any

from scrapy import Spider
from scrapy_splash import SplashRequest
from scrapy.http import Response
from .news_parser import lua_script_start


class CSMatchesSpider(Spider):
    name = "CSMatchesSpider"

    def start_requests(self):
        url_array=[]
        for page_num in range(1, 10):
            url_array.append("https://escorenews.com/ru/csgo/matches?s1=" + str(page_num))
        for url in url_array:
            yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                                args={'wait': 2, 'lua_source': lua_script_start,
                                      'cookies': 1, 'timeout': 90})

    def parse(self, response: Response, **kwargs: Any) -> Any:
        for match in response.css('div#matches_s1.flex-table.a.article.type1::attr(href)'):
            yield {'match_url': match.get()}
