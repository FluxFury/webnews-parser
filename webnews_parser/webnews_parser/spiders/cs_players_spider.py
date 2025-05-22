import random
from typing import Any, Iterator
from urllib.parse import urljoin

from flux_orm.database import new_sync_session
from flux_orm.models.models import Team
from scrapy import Request, Spider
from scrapy.http import Response
from sqlalchemy import select

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSPlayersItem
from ..loaders import CSPlayersItemLoader
from ..utils.spider_utils import css_mutator, xpath_mutator, xpath_mutator_all


class CSPlayersSpider(Spider):
    """
    A spider to scrape and parse CS:GO player data.

    Fetches player details including their team, statistics, and personal information.
    """

    name: str = "CSPlayersSpider"

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
            "webnews_parser.pipelines.CSPlayersPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the spider with provided arguments."""
        super().__init__(*args, **kwargs)
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)
        self.base_url: str = "https://escorenews.com"
        self.team_urls = self._get_team_urls_from_db()

    def _get_team_urls_from_db(self) -> list[str]:
        """
        Get team URLs from the database.

        Returns:
            list[str]: List of team URLs to scrape.
        """
        with new_sync_session() as session:
            stmt = select(Team)
            teams = session.execute(stmt).scalars().all()

            team_urls = set()
            for team in teams:
                if team.team_url:
                    team_url = urljoin(self.base_url, team.team_url)
                    team_urls.add(team_url)

            return list(team_urls)

    def start_requests(self) -> Iterator[Request]:
        """
        Start the spider by issuing requests to team pages.

        Yields:
            Request: Requests for team pages.
        """
        for team_url in self.team_urls:
            yield Request(url=team_url, callback=self.parse_team_page)

    def parse_team_page(self, response: Response) -> Iterator[Request]:
        """
        Parse team page and extract player links.

        Args:
            response: The response containing the team page.

        Yields:
            Request: Requests for individual player pages.
        """
        players = response.xpath(
            '//div[contains(@class,"hblock")]/h2[contains(text(),"Roster")]'
            "/parent::*/parent::*/table/tbody/tr/td"
        )

        for player in players.xpath(".//a"):
            player_status = self._get_player_status(
                player.xpath(".//span/u/text()").get()
            )
            full_url = urljoin(self.base_url, player.xpath(".//@href").get())
            yield Request(
                url=full_url,
                callback=self.parse_player,
                meta={"delay": 10},
                cb_kwargs={
                    "player_status": player_status,
                    "player_team": response.url.split("/")[-1],
                    "team_page_link": response.url,
                },
            )

    def parse_player(
        self, response: Response, **kwargs: Any
    ) -> Iterator[CSPlayersItem]:
        """
        Parse individual player pages and extract player data.

        Args:
            response: The response containing the player page.
            **kwargs: Additional keyword arguments.

        Yields:
            CSPlayersItem: Processed player data item.
        """
        retry_times = response.meta.get("retry_times", 0)
        max_retries = 3

        player_nickname = css_mutator("div.col-lg-8 h1::text", response)

        if not player_nickname and retry_times < max_retries:
            yield Request(
                url=response.url,
                callback=self.parse_player,
                meta={"delay": 10, "retry_times": retry_times + 1},
                cb_kwargs=kwargs,
                dont_filter=True,
            )
            return

        table_selector = response.css("table.tinfo.table.table-sm tbody")

        is_standard_layout = (
            css_mutator("tr:nth-child(1) th::text", table_selector).strip()
            == "Top places"
        )

        player_data = self._extract_player_data(
            response, table_selector, is_standard_layout
        )

        loader = CSPlayersItemLoader(item=CSPlayersItem())
        for field, value in player_data.items():
            loader.add_value(field, value)

        loader.add_value("player_team", kwargs.get("player_team"))
        loader.add_value("team_page_link", kwargs.get("team_page_link"))
        item = loader.load_item()
        yield item

    def _extract_player_data(
        self, response: Response, table_selector: Response, is_standard_layout: bool
    ) -> dict[str, str]:
        """
        Extract player information from the response.

        Args:
            response: The full response object.
            table_selector: The table section of the response.
            is_standard_layout: Whether the page uses standard layout.

        Returns:
            dict: Dictionary containing player data.
        """
        indices = {
            "team": 5 if is_standard_layout else 4,
            "country": 4 if is_standard_layout else 3,
            "age": 3 if is_standard_layout else 2,
            "games": 7 if is_standard_layout else 6,
        }

        team_selector = css_mutator(
            f"tr:nth-child({indices["team"]}) td a::attr(href)", table_selector
        )
        country_selector = css_mutator(
            f"tr:nth-child({indices["country"]}) td::text", table_selector
        )
        age_selector = css_mutator(
            f"tr:nth-child({indices["age"]}) td::text", table_selector
        )
        games_selector_1 = css_mutator(
            f"tr:nth-child({indices["games"]}) td::text", table_selector
        )
        games_selector_2 = css_mutator(
            f"tr:nth-child({indices["games"]}) td span.text-muted::text", table_selector
        )

        return {
            "player_nickname": css_mutator("div.col-lg-8 h1::text", response).strip(),
            "player_name": css_mutator("div.col-lg-8 h1 small::text", response).strip(),
            "player_age": age_selector.strip().split(" ")[0],
            "player_country": country_selector.strip(),
            "player_played_games_last_year": games_selector_1.split("/")[0].strip(),
            "player_played_games_overall": games_selector_2.strip(),
            "player_status": response.cb_kwargs.get("player_status"),
            "team_member_url": urljoin(self.base_url, response.url),
            "image_url": response.css("div.col-lg-4 img::attr(src)").get(),
        }

    @staticmethod
    def _get_player_status(player_status: str) -> str:
        """
        Extract player statistics from the response.
        """

        if player_status == "stand-in":
            return "stand-in"
        return "active player"
