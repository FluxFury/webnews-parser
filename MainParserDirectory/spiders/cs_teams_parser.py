from typing import Any
from urllib.parse import urljoin
from scrapy import Spider, Request
from scrapy.http import Response
from csv import DictReader
from deep_translator import GoogleTranslator


class CSTeamsSpider(Spider):
    name = "CSTeamsSpider"
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
        'REACTOR_THREADPOOL_MAXSIZE': 20,
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4
    }

    def start_requests(self):
        teams_url = 'https://escorenews.com/ru/csgo/team'
        with open('cs_matchups.csv', newline='', encoding='utf-8') as csvfile:
            csvreader = DictReader(csvfile)
            for row in csvreader:
                if row['team1_page_link'] != 'TBD':
                    yield Request(url=row['team1_page_link'], callback=self.parse)
                if row['team2_page_link'] != 'TBD':
                    yield Request(url=row['team2_page_link'], callback=self.parse)

        for page_num in range(1, 3):
            url = teams_url + '?s=' + str(page_num)
            yield Request(url=url, callback=self.parse_teams_page_for_links)

    def parse_teams_page_for_links(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        for team_page in response.css('td.tnm a'):
            yield Request(url=urljoin(base=base_url, url=team_page.css('::attr(href)').get()), callback=self.parse)

    def _css_mutator(self, selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder if placeholder else ''

    def parse(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        data_dict = {'team_name': self._css_mutator \
            ('div.hblock h1::text', response).strip().lower().replace(' ', '-'),
                     'team_page_link': response.url}
        for accomp_num, tournament in enumerate(response.css('section.team-ach tr')):
            data_dict['accomplishment_' + str(accomp_num + 1)] = self._css_mutator('a.tourNemaIco span::text',
                                                                                   tournament).strip()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_place'] = self._css_mutator('td.tplc::text',
                                                                                              tournament).strip()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_prize_pool'] = \
                tournament.css('span.scm::attr(data-value)').get()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_end_time'] = \
                self._css_mutator('span.sct::attr(datetime)', tournament).strip()

        for player_num, player in enumerate(response.css('a.playerName')[:5]):

            data_dict['player_' + str(player_num + 1)] = self._css_mutator('span::text', player).strip()
            status = self._css_mutator('span u::text', player).strip()
            data_dict['player_' + str(player_num + 1) + '_status'] = status if status else 'active player'
            data_dict['player_' + str(player_num + 1) + '_page_link'] = \
                urljoin(base=base_url, url=self._css_mutator('::attr(href)', player).strip())

        data_dict['team_region'] = GoogleTranslator(source='ru', target='en').translate \
            (self._css_mutator('table.tinfo.table.table-sm tr:nth-child(3) td::text', response).strip())

        data_dict['matches_played_in_the_last_year'] = self._css_mutator \
            ('table.tinfo.table.table-sm tr:nth-child(6) td::text', response).split('/')[0].strip()

        data_dict['matches_played_overall'] = self._css_mutator \
            ('table.tinfo.table.table-sm tr:nth-child(6) td span.text-muted::text', response).strip()

        data_dict['winstreak'] = self._css_mutator \
            ('table.tinfo.table.table-sm tr:nth-child(8) td::text', response).split(' ')[0].strip()
        yield data_dict
