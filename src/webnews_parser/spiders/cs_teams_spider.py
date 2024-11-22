from typing import Any
from urllib.parse import urljoin

from flux_orm.database import new_session
from flux_orm.models.models import TeamLink
from scrapy import Request, Spider
from scrapy.http import Response
from sqlalchemy import select

from ..items import CSTeamsItem


class CSTeamsSpider(Spider):
    name = "CSTeamsSpider"
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.StealthMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSTeamsPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "DEBUG",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_team_links_fetched = False

    @staticmethod
    async def get_team_links():
        async with new_session() as session:
            stmt = select(TeamLink)
            result = await session.execute(stmt)
            team_links = result.scalars().all()
            return team_links

    def start_requests(self):
        teams_url = "https://escorenews.com/en/csgo/team"

        for page_num in range(1, 3):
            url = teams_url + "?s=" + str(page_num)
            yield Request(url=url, callback=self.parse_teams_page_for_links)

    def parse_teams_page_for_links(self, response: Response):
        base_url = "https://escorenews.com"
        for team_page in response.css("td.tnm a"):
            yield Request(url=urljoin(base=base_url, url=team_page.css("::attr(href)").get()), callback=self.parse)

    @staticmethod
    def _xpath_mutator(selector: str, response: Response) -> str:
        placeholder = response.xpath(selector).get()
        return placeholder or ""

    @staticmethod
    def _css_mutator(selector: str, response: Response) -> str:
        placeholder = response.css(selector).get()
        return placeholder or ""

    async def parse(self, response: Response, **kwargs) -> Any:
        if not self.is_team_links_fetched:
            team_links = await self.get_team_links()
            self.is_team_links_fetched = True
            for team_link in team_links:
                yield Request(url=team_link.link, callback=self.parse)
        if response.css("section.team-ach tr").get() is None:
            return
        base_url = "https://escorenews.com"
        team_pretty_name = self._css_mutator \
            ("div.hblock h1::text", response).strip()
        team_name = response.url.split("/")[-1]
        team_logo_link = self._css_mutator("div.tourlogo img::attr(img)", response)
        data_dict = {"team_pretty_name": team_pretty_name, "team_name": team_name, "team_page_link": response.url,
                     'team_logo_link': team_logo_link, "stats": {},
                     "players": {}, "regalia": {}}

        for tournament in response.css("section.team-ach tr"):
            accomp_name = self._css_mutator("a.tourNemaIco span::text", tournament).strip()
            accomp_place = self._css_mutator("td.tplc::text", tournament).strip()
            accomp_earnings = tournament.css("span.scm::attr(data-value)").get()
            accomp_date = self._css_mutator("span.sct::attr(datetime)", tournament).strip()
            placeholder_tuple = (accomp_place, accomp_earnings, accomp_date)
            data_dict["regalia"][accomp_name] = placeholder_tuple

        for player in response.css("a.playerName")[:5]:
            nickname = self._css_mutator("span::text", player).strip()
            status = self._css_mutator("span u::text", player).strip()
            player_photo_link = self._css_mutator("picture img::attr(src)", player)
            if player_photo_link == "https://escorenews.com/media/logo/nop.svg":
                player_photo_link = None
            player_country = self._css_mutator("img.flag.tt::attr(title)", player).strip()
            player_link = urljoin(base=base_url, url=self._css_mutator("::attr(href)", player).strip())
            placeholder_tuple = (status or "active player", player_link, player_country, player_photo_link)
            data_dict["players"][nickname] = placeholder_tuple

        team_region = (self._css_mutator("table.tinfo.table.table-sm tr:nth-child(3) td::text", response).strip())
        data_dict["team_region"] = team_region

        data_dict["stats"]["matches_played_in_the_last_year"] = self._css_mutator \
            ("table.tinfo.table.table-sm tr:nth-child(6) td::text", response).split("/")[0].strip()

        data_dict["stats"]["matches_played_overall"] = self._css_mutator \
            ("table.tinfo.table.table-sm tr:nth-child(6) td span.text-muted::text", response).strip()

        data_dict["stats"]["winstreak"] = self._css_mutator \
            ("table.tinfo.table.table-sm tr:nth-child(8) td::text", response).split(" ")[0].strip()
        data_item = CSTeamsItem()
        data_item.update(data_dict)
        yield data_item
