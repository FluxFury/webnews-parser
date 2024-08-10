from scrapy import Spider
from scrapy_splash import SplashRequest


class BooksToScrapeComSpider(Spider):
    name = "pc_enjoyer"

    def start_requests(self):
        urls = [
            "https://turbopypip.github.io/pc-enjoyer2.0/"
        ]
        yield SplashRequest(urls, callback=self.parse, args={'wait': 0.5})

    def parse(self, response):
        for paragraph in response.css('div.p'):
            yield{
            "text" : paragraph.css('p::text').get()
            }


