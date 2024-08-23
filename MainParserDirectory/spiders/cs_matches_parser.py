from typing import Any
from urllib.parse import urljoin
from scrapy import Spider, Request
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
            yield Request(url=url, callback=self.parse)

    def parse_match_page(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        tournament_link = urljoin(base=base_url, url=response.xpath('//h1//a/@href').get())
        tournament_logo_link = urljoin(base=base_url,
                                       url=response.css('div.header picture img::attr(src)').get())
        tournament_name = response.xpath('//h1//a//text()').get()
        tournament_info = response.xpath('//div[contains(@class,"hh")]/span/text()').get().split('•')
        print(tournament_info)
        tournament_format = tournament_info[-2].strip()
        tournament_stage = tournament_info[-3].strip()
        teams = response.xpath('//div[contains(@class, "teams-on-live")]//h2/text()').getall()
        teams_logo_links = tuple(urljoin(base=base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]//picture//img/@src').getall())
        teams_page_links = tuple(urljoin(base=base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]/span/a/@href').getall())
        match_format = response.xpath('//div[contains(@class, "score")]/h3/text()').get()
        match_format = match_format.strip()[match_format.find('B'):]
        match_status = response.xpath('//div[contains(@class, "score")]//b/text()').get()
        match_url = urljoin(base=base_url, url=response.meta.get('match_url'))
        match_score = response.xpath('//div[contains(@class, "score")]/span[contains(@class, "live")]/text()').getall()
        def TBD_team_page_boolean(team: int) -> bool:
            TBD_team_page_linkv1 = 'https://escorenews.com/ru/csgo/team/players'
            TBD_team_page_linkv2 = 'javascript:;'
            return teams_page_links[team] != TBD_team_page_linkv1 and teams_page_links[team] != TBD_team_page_linkv2

        def TBD_team_logo_boolean(team: int) -> bool:
            TBD_team_logo_link = 'https://escorenews.com/media/logo/not.svg'
            return teams_logo_links[team] != TBD_team_logo_link

        yield {'tournament_name': tournament_name,
               'tournament_page_link': tournament_link,
               'tournament_logo_link': tournament_logo_link,
               'tournament_format': tournament_format,
               'tournament_stage': tournament_stage,
               'match_format': match_format,
               'match_status': match_status,

               'team1_page_link': teams_page_links[0]
               if TBD_team_page_boolean(0) or TBD_team_logo_boolean(0) else 'TBD',

               'team1_logo_link': teams_logo_links[0]
               if TBD_team_logo_boolean(0) or TBD_team_page_boolean(0) else 'TBD',

               'team1': teams[0] if teams[0] != 'players' else 'TBD',
               'team1_score': match_score[0],
               'team2_score:': match_score[1],
               'team2': teams[1] if teams[1] != 'players' else 'TBD',

               'team2_logo_link': teams_logo_links[1]
               if TBD_team_logo_boolean(1) or TBD_team_page_boolean(1) else 'TBD',

               'team2_page_link': teams_page_links[1]
               if TBD_team_page_boolean(1) or TBD_team_logo_boolean(1) else 'TBD',

               'match_begin_time_UTC+0': response.meta.get('match_begin_time'),
               'match_url': match_url,
               }

    def parse(self, response: Response, **kwargs: Any) -> Any:
        table_1 = response.css("div#matches_s1.flex-table")
        matches = table_1.css('a.article')
        for match in matches:
            scheduled_match_url = match.css('::attr(href)').get()
            scheduled_match_begin_time = match.css('div.time i.sct::attr(datetime)').get()
            if scheduled_match_url.count("tbd") < 2:
                placeholder_dict = {'match_begin_time': scheduled_match_begin_time,
                                    'match_url': scheduled_match_url}
                yield Request(url=urljoin(base='https://escorenews.com/', url=scheduled_match_url),
                                      callback=self.parse_match_page,
                                      meta=placeholder_dict,
                                      )
