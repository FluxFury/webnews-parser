import warnings
from logging import getLogger, ERROR
from typing import Any
from scrapy import Spider
from scrapy_splash import SplashRequest
from scrapy.http import Response
from scrapy.utils.deprecate import ScrapyDeprecationWarning
import json
warnings.filterwarnings("ignore", category=ScrapyDeprecationWarning)

getLogger('scrapy_user_agents.user_agent_picker').setLevel(ERROR)

lua_script = """
function main(splash, args)
    splash.images_enabled = false
    assert(splash:go(args.url))
    assert(splash:wait(1.0))
    return {
    html = splash:html()
  }
end"""


class CSNewsSpider(Spider):
    name = "CSNewsSpider"
    custom_settings = {'LOG_LEVEL': "INFO",
                       'COOKIES_ENABLED': False,
                       'DOWNLOAD_TIMEOUT': 120,
                       'REACTOR_THREADPOOL_MAXSIZE': 20
                       }

    def start_requests(self):

        url_array = ["https://www.hltv.org/news/archive/2024/august",
                     "https://www.hltv.org/news/archive/2024/july"]
        for url in url_array:
            yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                                args={'lua_source': lua_script, 'timeout': 60, 'wait': 2})

    def _clean_text(self, text: str) -> str:
        return text.replace('\u2060', '').replace('\\', '') \
            .replace(']', '').replace('[', '').strip()  # Удаление \u2060, \, [, ]

    def parse_news(self, response):
        news_string = self._clean_text(response.css('p.headertext::text').get()) \
            if response.css("p.headertext::text") else ""
        paragraph_list = []
        data_dict = {'header': news_string, 'text': paragraph_list}
        for piece in response.css('p.news-block'):
            paragraph_list.append(self._clean_text(piece.xpath('string()').get()))
        yield {
            "article": json.dumps(data_dict),
            "url": response.meta.get('rel_url'),
            "unix_time": response.xpath('//div[@class="date"]/@data-unix').get()
            if response.xpath('//div[@class="date"]/@data-unix').get()
            else response.xpath('//div[@class="news-with-frag-date"]/@data-unix').get()
        }

    def parse(self, response: Response, **kwargs: Any) -> Any:
        for paragraph in response.css('a.newsline.article'):
            yield SplashRequest(url=response.urljoin(url=paragraph.css('::attr(href)').get()),
                                callback=self.parse_news,
                                meta={'header': paragraph.css('div.newstext::text').get(),
                                      'rel_url': response.urljoin(url=paragraph.css('::attr(href)').get())},
                                endpoint='execute',
                                args={'lua_source': lua_script})
