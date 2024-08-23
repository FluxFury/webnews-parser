from typing import Any
from urllib.parse import urljoin
from scrapy import Spider, Request
from scrapy.http import Response
from csv import DictReader


class CSPLayersSpider(Spider):
    name = "CSPLayersSpider"
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
        with open('cs_teams.csv', newline='', encoding='utf-8') as csvfile:
            csvreader = DictReader(csvfile)
            for row in csvreader:
                for player_num in range(1, 6):
                    if row['player_' + str(player_num)] != '':
                        yield Request(url=row['player_' + str(player_num) + '_page_link'], callback=self.parse)

    def parse(self, response: Response, **kwargs: Any) -> Any:
        team_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(5) td a::attr(href)').get()
        country_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(4) td::text').get()
        age_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(3) td::text').get()
        games_selector_1 = response.css('table.tinfo.table.table-sm tbody tr:nth-child(7) td::text').get()
        games_selector_2 = response.css('table.tinfo.table.table-sm tbody tr:nth-child(7) td span.text-muted::text').get()
        if response.css('table.tinfo.table.table-sm tbody tr:nth-child(1) th::text').get().strip() != 'Призовые места':
            team_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(4) td a::attr(href)').get()
            country_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(3) td::text').get()
            age_selector = response.css('table.tinfo.table.table-sm tbody tr:nth-child(2) td::text').get()
            games_selector_1 = response.css('table.tinfo.table.table-sm tbody tr:nth-child(6) td::text').get()
            games_selector_2 = response.css('table.tinfo.table.table-sm tbody tr:nth-child(6) td span.text-muted::text').get()
        player_nickname = response.css('div.col-lg-8 h1::text').get().strip()
        player_team = team_selector.split('/')[-1].strip() if team_selector else team_selector
        player_age = age_selector.strip().split(' ')[0] if age_selector else age_selector
        player_country = country_selector.strip() if country_selector else country_selector
        player_played_games_last_year = games_selector_1.split('/')[0].strip() \
            if games_selector_1 else games_selector_1
        player_played_games_overall = games_selector_2.strip() if games_selector_2 else games_selector_2
        yield {
            'player_nickname': player_nickname,
            'player_team': player_team,
            'player_age': player_age,
            'player_country': player_country,
            'player_played_games_last_year': player_played_games_last_year,
            'player_played_games_overall': player_played_games_overall,

        }
