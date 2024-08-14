from scrapy import Spider
from scrapy_splash import SplashRequest
import warnings
from scrapy.utils.deprecate import ScrapyDeprecationWarning

warnings.filterwarnings("ignore", category=ScrapyDeprecationWarning)




lua_script_start = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(0.5))
  return {
    html = splash:html()
  }
end"""
class NewsSpider(Spider):
    name = "NewsSpider"

    def start_requests(self):

        url = "https://www.hltv.org/news/archive/2024/august"
        yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                            args={'wait': 1, 'lua_source': lua_script_start})

    def parse_news(self, response):
        #response.css('h1.headline::text').get() + ' ' + response.css('p.headertext::text').get()
        news_string=[response.css('h1.headline::text').get()] + \
                    response.css('p.news-block::text').getall() + \
                    [response.css('p.headertext::text').get()]
        yield {
            "header":response.meta.get('header'),
            "url":response.meta.get('url'),
            "text":news_string
        }
    def parse(self, response):
        for paragraph in response.css('a.newsline.article'):
            yield SplashRequest(url=response.urljoin(url=paragraph.css('a.newsline.article::attr(href)').get()),
                                callback=self.parse_news,
                                meta={'header': paragraph.css('div.newstext::text').get(),
                                      'url': response.urljoin(url=paragraph.css('a.newsline.article::attr(href)').get())},
                                endpoint='execute', args={'wait': 0.5, 'lua_source': lua_script_start})
