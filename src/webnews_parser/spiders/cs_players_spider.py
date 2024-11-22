from typing import Any
from urllib.parse import urljoin

from flux_orm.database import new_session
from flux_orm.models.models import PlayerLink
from scrapy import Request, Spider
from scrapy.http import Response
from sqlalchemy import select

from ..items import CSPlayersItem


class CSPlayersSpider(Spider):
    name = "CSPlayersSpider"
    base_url = "https://escorenews.com"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "webnews_parser.middlewares.StealthMiddleware": 542,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSPlayersPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_player_links_fetched = False

    @staticmethod
    def _css_mutator(selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder or ""

    def start_requests(self):
        url = 'https://escorenews.com/en/csgo/player'
        yield Request(url=url, callback=self.get_first_link)

    def get_first_link(self, response: Response):
        first_player_link = urljoin(base=self.base_url, url=response.css("a.playername::attr(href)").get())
        yield Request(url=first_player_link, callback=self.parse)

    @staticmethod
    async def get_player_links():
        async with new_session() as session:
            stmt = select(PlayerLink)
            result = await session.execute(stmt)
            player_links = result.scalars().all()
            return player_links
    async def parse(self, response: Response, **kwargs: Any) -> Any:
        if not self.is_player_links_fetched:
            self.is_player_links_fetched = True
            player_links = await self.get_player_links()
            for player_link in player_links:
                yield Request(url=player_link.link, callback=self.parse)
        table_selector = response.css("table.tinfo.table.table-sm tbody")
        team_selector = self._css_mutator("tr:nth-child(5) td a::attr(href)", table_selector)

        country_selector = self._css_mutator("tr:nth-child(4) td::text", table_selector)

        age_selector = self._css_mutator("tr:nth-child(3) td::text", table_selector)

        games_selector_1 = self._css_mutator("tr:nth-child(7) td::text", table_selector)

        games_selector_2 = self._css_mutator("tr:nth-child(7) td span.text-muted::text", table_selector)

        if self._css_mutator("tr:nth-child(1) th::text", table_selector).strip() \
                != "Top places":
            team_selector = self._css_mutator("tr:nth-child(4) td a::attr(href)", table_selector)
            country_selector = self._css_mutator("tr:nth-child(3) td::text", table_selector)
            age_selector = self._css_mutator("tr:nth-child(2) td::text", table_selector)
            games_selector_1 = self._css_mutator("tr:nth-child(6) td::text", table_selector)
            games_selector_2 = self._css_mutator("tr:nth-child(6) td span.text-muted::text", table_selector)
        player_nickname = self._css_mutator("div.col-lg-8 h1::text", response).strip()
        player_name = self._css_mutator("div.col-lg-8 h1 small::text", response).strip()
        player_team = team_selector.split("/")[-1].strip()
        player_age = age_selector.strip().split(" ")[0]
        player_country = country_selector.strip()
        player_played_games_last_year = games_selector_1.split("/")[0].strip()
        player_played_games_overall = games_selector_2.strip()
        data_dict = {
            "player_nickname": player_nickname,
            "player_name": player_name,
            "player_team": player_team,
            "player_age": player_age,
            "player_country": player_country,
            "player_played_games_last_year": player_played_games_last_year,
            "player_played_games_overall": player_played_games_overall,
        }
        data_item = CSPlayersItem()
        data_item.update(data_dict)
        yield data_item
