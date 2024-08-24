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
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 401,
            'MainParserDirectory.middlewares.SeleniumMiddleware': 543,
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        }
    }

    def start_requests(self):
        teams_url = 'https://escorenews.com/ru/csgo/team'
        # with open('cs_matchups.csv', newline='', encoding='utf-8') as csvfile:
        #     csvreader = DictReader(csvfile)
        #     for row in csvreader:
        #         if row['team1_page_link'] != 'TBD':
        #             yield Request(url=row['team1_page_link'], callback=self.parse)
        #         if row['team2_page_link'] != 'TBD':
        #             yield Request(url=row['team2_page_link'], callback=self.parse)

        for page_num in range(1, 2):
            url = teams_url + '?s=' + str(page_num)
            yield Request(url=url, callback=self.parse_teams_page_for_links)

    def parse_teams_page_for_links(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        for team_page in response.css('td.tnm a'):
            yield Request(url=urljoin(base=base_url, url=team_page.css('::attr(href)').get()), callback=self.parse)

    def parse(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        data_dict = {'team_name': response.css('div.hblock h1::text').get().strip().lower().replace(' ', '-')}
        for accomp_num, tournament in enumerate(response.css('section.team-ach tr')):
            data_dict['accomplishment_' + str(accomp_num + 1)] = tournament.css('a.tourNemaIco span::text').get().strip()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_place'] = tournament.css('td.tplc::text').get().strip()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_prize_pool'] = \
                tournament.css('span.scm::attr(data-value)').get()
            data_dict['accomplishment_' + str(accomp_num + 1) + '_end_time'] = \
                tournament.css('span.sct::attr(datetime)').get().strip()

        for player_num, player in enumerate(response.css('a.playerName')[:5]):
            data_dict['player_' + str(player_num + 1)] = player.css('span::text').get().strip()
            data_dict['player_' + str(player_num + 1) + '_page_link'] = \
                urljoin(base=base_url, url=player.css('::attr(href)').get().strip())

        data_dict['team_region'] = GoogleTranslator(source='ru', target='en').\
            translate(response.css('table.tinfo.table.table-sm tr:nth-child(3) td::text').get().strip())

        data_dict['matches_played_in_the_last_year'] = \
            response.css('table.tinfo.table.table-sm tr:nth-child(6) td::text').get().split('/')[0].strip()

        data_dict['matches_played_overall'] = \
            response.css('table.tinfo.table.table-sm tr:nth-child(6) td span.text-muted::text').get().strip()

        data_dict['winstreak'] = \
            response.css('table.tinfo.table.table-sm tr:nth-child(8) td::text').get().split(' ')[0].strip()

        yield data_dict
