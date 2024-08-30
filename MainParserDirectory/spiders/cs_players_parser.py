from typing import Any
from scrapy import Spider, Request
from scrapy.http import Response
from csv import DictReader
from deep_translator import GoogleTranslator


class CSPLayersSpider(Spider):
    name = "CSPLayersSpider"
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': None,
            'MainParserDirectory.middlewares.StealthMiddleware': 542,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'MainParserDirectory.middlewares.TooManyRequestsRetryMiddleware': 543,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'HTTPCACHE_ENABLED': False,
        'USER_AGENT': None,
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        'REACTOR_THREADPOOL_MAXSIZE': 20
    }

    def start_requests(self):
        with open('cs_teams.csv', newline='', encoding='utf-8') as csvfile:
            csvreader = DictReader(csvfile)
            for row in csvreader:
                for player_num in range(1, 6):
                    if row['player_' + str(player_num)] != '':
                        yield Request(url=row['player_' + str(player_num) + '_page_link'], callback=self.parse)
    def _css_mutator(self, selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder if placeholder else ''
    def parse(self, response: Response, **kwargs: Any) -> Any:
        table_selector = response.css('table.tinfo.table.table-sm tbody')
        team_selector = self._css_mutator('tr:nth-child(5) td a::attr(href)', table_selector)

        country_selector = self._css_mutator('tr:nth-child(4) td::text', table_selector)

        age_selector = self._css_mutator('tr:nth-child(3) td::text', table_selector)

        games_selector_1 = self._css_mutator('tr:nth-child(7) td::text', table_selector)

        games_selector_2 = self._css_mutator('tr:nth-child(7) td span.text-muted::text', table_selector)

        if self._css_mutator('tr:nth-child(1) th::text', table_selector).strip() \
                != 'Призовые места':
            team_selector = self._css_mutator('tr:nth-child(4) td a::attr(href)', table_selector)
            country_selector = self._css_mutator('tr:nth-child(3) td::text', table_selector)
            age_selector = self._css_mutator('tr:nth-child(2) td::text', table_selector)
            games_selector_1 = self._css_mutator('tr:nth-child(6) td::text', table_selector)
            games_selector_2 = self._css_mutator('tr:nth-child(6) td span.text-muted::text', table_selector)
        player_nickname = self._css_mutator('div.col-lg-8 h1::text', response).strip()
        player_team = team_selector.split('/')[-1].strip()
        player_age = age_selector.strip().split(' ')[0]
        player_country = country_selector.strip()
        player_played_games_last_year = games_selector_1.split('/')[0].strip()
        player_played_games_overall = games_selector_2.strip()
        yield {
            'player_nickname': player_nickname,
            'player_team': player_team,
            'player_age': player_age,
            'player_country': GoogleTranslator(source='ru', target='en').translate(player_country),
            'player_played_games_last_year': player_played_games_last_year,
            'player_played_games_overall': player_played_games_overall,
        }
