from typing import Any, Optional
from urllib.parse import urljoin
from scrapy import Spider, Request
from scrapy.http import Response
from csv import DictWriter

USER_AGENT = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15']


class CSlsMatchesTournamentsSpider(Spider):
    name = "CSlsMatchesTournamentsSpider"
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': None,
            'MainParserDirectory.middlewares.StealthMiddleware': 542,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            'MainParserDirectory.middlewares.TooManyRequestsRetryMiddleware': 543,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'HTTPCACHE_ENABLED': False,
        'USER_AGENT': None,
        'LOG_LEVEL': 'INFO',
        'COOKIES_ENABLED': False,
        'REACTOR_THREADPOOL_MAXSIZE': 20
    }

    def _xpath_mutator(self, selector: str, response: Response) -> str:
        placeholder = response.xpath(selector).get()
        return placeholder if placeholder else ''

    def start_requests(self):
        url_array = []
        for page_num in range(1, 10):
            url_array.append("https://escorenews.com/ru/csgo/matches?s1=" + str(page_num))
        for url in url_array:
            yield Request(url, callback=self.parse)

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

    def parse_match_page(self, response: Response, **kwargs: Any) -> Any:
        base_url = 'https://escorenews.com'
        tournament_link = urljoin(base=base_url, url=response.xpath('//h1//a/@href').get())
        tournament_logo_link = urljoin(base=base_url,
                                       url=response.css('div.header picture img::attr(src)').get())
        tournament_info = self._xpath_mutator('//div[contains(@class,"hh")]/span/text()', response).split('•')
        tournament_format = tournament_info[-2].strip() if tournament_info != [''] else ''
        tournament_stage = tournament_info[-3].strip() if tournament_info != [''] else ''
        teams = response.xpath('//div[contains(@class, "teams-on-live")]//h2/text()').getall()
        teams_logo_links = tuple(urljoin(base=base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]//picture//img/@src').getall())
        teams_page_links = tuple(urljoin(base=base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]/span/a/@href').getall())
        if not (teams_logo_links):
            teams_logo_links = ("", "")
        if not (teams_page_links):
            teams_page_links = ("", "")
        if not (teams):
            teams = ("", "")
        match_format = self._xpath_mutator('//div[contains(@class, "score")]/h3/text()', response)
        match_format = match_format.strip()[match_format.find('B'):]
        match_status = response.xpath('//div[contains(@class, "score")]//b/text()').get()
        if match_status == 'Матч не начался':
            match_status = 'scheduled'
        elif match_status == 'Матч начался':
            match_status = 'live'
        match_url = urljoin(base=base_url, url=response.meta.get('match_url'))
        match_score = response.xpath('//div[contains(@class, "score")]/span[contains(@class, "live")]/text()').getall()

        def TBD_team_page_boolean(team_pos: int) -> bool:
            TBD_team_page_linkv1 = 'https://escorenews.com/ru/csgo/team/players'
            TBD_team_page_linkv2 = 'javascript:;'
            return (teams_page_links[team_pos] != TBD_team_page_linkv1
                    and teams_page_links[team_pos] != TBD_team_page_linkv2)

        def TBD_team_logo_boolean(team_pos: int) -> bool:
            TBD_team_logo_link = 'https://escorenews.com/media/logo/not.svg'
            return teams_logo_links[team_pos] != TBD_team_logo_link

        placeholder_dict = {'match_info': {
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
            'team2_score': match_score[1],
            'team2': teams[-1] if teams[-1] != 'players' else 'TBD',

            'team2_logo_link': teams_logo_links[-1]
            if TBD_team_logo_boolean(1) or TBD_team_page_boolean(1) else 'TBD',

            'team2_page_link': teams_page_links[-1]
            if TBD_team_page_boolean(1) or TBD_team_logo_boolean(1) else 'TBD',

            'match_begin_time_UTC+0': response.meta.get('match_begin_time')}
        }
        if tournament_logo_link != base_url:
            yield Request(url=tournament_link, callback=self.parse_tournament_page, meta=placeholder_dict)
        else:
            pass

    def parse_tournament_page(self, response: Response, **kwargs: Any) -> Any:
        tournament_name = response.css('div.hh::text').get()
        tournament_start_date = response.xpath(
            '//table[contains(@class, "tinfo table table-sm")]/tbody/tr[3]/td[contains(@class, "sct")]/@datetime').get()

        data_to_save = {'tournament_name': tournament_name, 'tournament_start_date': tournament_start_date}
