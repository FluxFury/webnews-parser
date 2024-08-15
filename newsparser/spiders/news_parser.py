from scrapy import Spider
from scrapy_splash import SplashRequest
import warnings
from scrapy.utils.deprecate import ScrapyDeprecationWarning

warnings.filterwarnings("ignore", category=ScrapyDeprecationWarning)

lua_script_start = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(1))
  return {
    html = splash:html()
  }
end"""


class NewsSpider(Spider):
    name = "NewsSpider"

    def start_requests(self):

        url_array = ["https://www.hltv.org/news/archive/2024/august", "https://www.hltv.org/news/archive/2024/july"]
        for url in url_array:
            yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                            args={'wait': 1, 'lua_source': lua_script_start})

    def parse_news(self, response):
        news_string = response.css('p.headertext::text').get().strip() + ' ' \
            if response.css("p.headertext::text") else ""
        for piece in response.css('p.news-block').xpath('string()').getall():
            news_string += ' ' + piece.strip()
        yield {
            "header": response.meta.get('header'),
            "url": response.meta.get('rel_url'),
            "text": news_string
        }

    def parse(self, response):
        for paragraph in response.css('a.newsline.article'):
            yield SplashRequest(url=response.urljoin(url=paragraph.css('a.newsline.article::attr(href)').get()),
                                callback=self.parse_news,
                                meta={'header': paragraph.css('div.newstext::text').get(),
                                'rel_url': response.urljoin(url=paragraph.css('a.newsline.article::attr(href)').get())},
                                endpoint='execute',
                                args={'wait': 2, 'lua_source': lua_script_start})
