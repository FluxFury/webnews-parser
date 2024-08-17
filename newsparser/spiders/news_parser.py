from logging import getLogger, ERROR
from typing import Any
from scrapy import Spider
from scrapy.exceptions import ScrapyDeprecationWarning
from scrapy_splash import SplashRequest
from scrapy.http import Response
from warnings import filterwarnings

filterwarnings("ignore", category=ScrapyDeprecationWarning)
getLogger('scrapy_user_agents.user_agent_picker').setLevel(ERROR)

lua_script_start = """
function main(splash, args)
  assert(splash:go(args.url))
  local scroll = splash:jsfunc([[
    function scrollWithDelay() {
        for (let i = 0; i < 5; ++i) {
            setTimeout(() => window.scrollTo(0, document.body.scrollHeight), i * 2000);
        }
    }
  ]])
  scroll()
  assert(splash:wait(1))
  return {
    html = splash:html()
  }
end"""


class NewsSpider(Spider):
    name = "NewsSpider"

    def start_requests(self):

        url_array = ["https://www.hltv.org/news/archive/2024/august",
                     "https://www.hltv.org/news/archive/2024/july"]
        for url in url_array:
            yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                                args={'wait': 0.5, 'lua_source': lua_script_start})

    def parse_news(self, response):
        news_string = response.css('p.headertext::text').get().strip() + ' ' \
            if response.css("p.headertext::text") else ""
        for piece in response.css('p.news-block').xpath('string()').getall():
            news_string += ' ' + piece.strip()
        yield {
            "header": response.meta.get('header'),
            "url": response.meta.get('rel_url'),
            "text": news_string,
            "date_time": response.css("div.date::text").get()
            if response.css("div.date::text").get()
            else response.css("div.news-with-frag-date::text").get(),
            "unix_time": response.xpath('//div[@class="date"]/@data-unix').get()
            if response.xpath('//div[@class="date"]/@data-unix').get()
            else response.xpath('//div[@class="news-with-frag-date"]/@data-unix').get(),
        }

    def parse(self, response: Response, **kwargs: Any) -> Any:
        for paragraph in response.css('a.newsline.article'):
            yield SplashRequest(url=response.urljoin(url=paragraph.css('a.newsline.article::attr(href)').get()),
                                callback=self.parse_news,
                                meta={'header': paragraph.css('div.newstext::text').get(),
                                      'rel_url': response.urljoin(
                                          url=paragraph.css('a.newsline.article::attr(href)').get())},
                                endpoint='execute',
                                args={'wait': 0.5, 'lua_source': lua_script_start})
