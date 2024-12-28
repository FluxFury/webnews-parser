import random
from typing import Any, Iterator
from urllib.parse import urljoin

from flux_orm import Competition, Sport, Team
from flux_orm.database import new_session
from scrapy import Request, Spider
from scrapy.http import Response
from sqlalchemy import select

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSTeamsItem
from ..loaders import CSTeamsItemLoader
from ..utils.spider_utils import css_mutator


class CSTeamsSpider(Spider):
    """
    A spider to scrape and parse CS:GO team data.

    Fetches team details including players, statistics, and achievements.
    """

    name: str = "CSTeamsSpider"
    
    custom_settings: dict[str, Any] = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSTeamsPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the spider with provided arguments."""
        super().__init__(*args, **kwargs)
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)
        self.is_team_links_fetched: bool = False
        self.base_url: str = "https://escorenews.com"


    def start_requests(self) -> Iterator[Request]:
        """
        Start the spider by issuing requests to team listing pages.

        Yields:
            Request: Initial requests to start crawling.

        """
        teams_url = f"{self.base_url}/en/csgo/team"
        for page_num in range(1, 3):
            url = f"{teams_url}?s={page_num}"
            yield Request(url=url, callback=self.parse_teams_page_for_links)

    def parse_teams_page_for_links(self, response: Response) -> Iterator[Request]:
        """
        Parse the teams listing page and generate requests for individual team pages.

        Args:
            response (Response): The response containing the teams listing.

        Yields:
            Request: Requests for individual team pages.

        """
        for team_page in response.css("td.tnm a"):
            yield Request(
                url=urljoin(base=self.base_url, url=team_page.css("::attr(href)").get()),
                callback=self.parse
            )

    async def parse(self, response: Response, **kwargs: Any) -> Iterator[CSTeamsItem]:
        """Parse individual team pages and extract team data."""
        if not self.is_team_links_fetched:
            teams = await self.get_cs2_teams()
            team_links = []
            for team in teams:
                team_links.append(team.team_url)
            self.is_team_links_fetched = True
            for team_link in team_links:
                yield Request(url=team_link, callback=self.parse)

        team_name = response.url.split("/")[-1]
        if response.css("section.team-ach tr").get() is None or team_name == "javascript:;":
            return

        # Initialize loader with item and response
        loader = CSTeamsItemLoader(
            item=CSTeamsItem(),
            response=response
        )
        
        loader.add_css("team_pretty_name", "div.hblock h1::text")
        loader.add_value("team_name", team_name)
        loader.add_value("team_page_link", response.url)
        loader.add_css("team_logo_link", "div.tourlogo img::attr(img)")
        loader.add_css("team_region", "table.tinfo.table.table-sm tr:nth-child(3) td::text")
        
        # Extract and add data
        stats = self._extract_stats(response)
        players = self._extract_players(response)
        regalia = self._extract_regalia(response)
        
        loader.add_value("stats", stats)
        loader.add_value("players", players)
        loader.add_value("regalia", regalia)

        yield loader.load_item()

    def _extract_stats(self, response: Response) -> dict[str, str]:
        """Extract team statistics from the response."""
        return {
            "matches_played_in_the_last_year": css_mutator(
                "table.tinfo.table.table-sm tr:nth-child(6) td::text", response
            ).split("/")[0].strip(),
            "matches_played_overall": css_mutator(
                "table.tinfo.table.table-sm tr:nth-child(6) td span.text-muted::text", response
            ).strip(),
            "winstreak": css_mutator(
                "table.tinfo.table.table-sm tr:nth-child(8) td::text", response
            ).split(" ")[0].strip()
        }

    def _extract_players(self, response: Response) -> dict[str, tuple]:
        """Extract player information from the response."""
        players = {}
        for player in response.css("a.playerName")[:5]:
            nickname = css_mutator("span::text", player).strip()
            status = css_mutator("span u::text", player).strip() or "active player"
            player_photo_link = css_mutator("picture img::attr(src)", player)
            if player_photo_link == f"{self.base_url}/media/logo/nop.svg":
                player_photo_link = None
            player_country = css_mutator("img.flag.tt::attr(title)", player).strip()
            player_link = urljoin(
                base=self.base_url,
                url=css_mutator("::attr(href)", player).strip()
            )
            players[nickname] = (status, player_link, player_country, player_photo_link)
        return players

    def _extract_regalia(self, response: Response) -> dict[str, tuple]:
        """Extract team achievements from the response."""
        regalia = {}
        for tournament in response.css("section.team-ach tr"):
            name = css_mutator("a.tourNemaIco span::text", tournament).strip()
            place = css_mutator("td.tplc::text", tournament).strip()
            earnings = tournament.css("span.scm::attr(data-value)").get()
            date = css_mutator("span.sct::attr(datetime)", tournament).strip()
            regalia[name] = (place, earnings, date)
        return regalia

    async def get_cs2_teams(self) -> list[Team]:
        """Get all CS2 teams from the database."""
        async with new_session() as session:
            stmt = (
                select(Team)
                .join(Team.competitions)
                .join(Competition.sport)
                .filter(Sport.name == "CS2")
            )
            result = await session.execute(stmt)
            return result.scalars().all()

