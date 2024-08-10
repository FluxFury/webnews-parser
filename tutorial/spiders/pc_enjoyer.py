from scrapy import Spider
from scrapy_splash import SplashRequest


class NewsSpider(Spider):
    name = "NewsSpider"

    def start_requests(self):
        lua_script = """
        function main(splash, args)
          assert(splash:go(args.url))
          assert(splash:wait(0.5))
          return {
            html = splash:html()
          }
        end"""
        url = "https://www.hltv.org/"
        yield SplashRequest(url=url, callback=self.parse, endpoint='execute',
                            args={'wait': 1, 'lua_source': lua_script, url: "https://www.hltv.org/"})

    def parse(self, response):
        for paragraph in response.css('div.standard-box.standard-list'):
            yield {
                "text": paragraph.css('div.newstext::text').get(),
                "url": paragraph.css('a.newsline.article::attr(href)').get()
            }
