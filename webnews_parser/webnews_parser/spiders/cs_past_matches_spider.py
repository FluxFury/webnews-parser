import random
from typing import Any, Iterator
from urllib.parse import urljoin

from scrapy import Request, Spider
from scrapy.http import Response

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSPMatchesItem
from ..loaders import CSPMatchesItemLoader
from ..utils.spider_utils import (
    clean_text,
    css_mutator,
    extract_teams,
    xpath_mutator,
    xpath_mutator_all,
)


class CSpMatchesSpider(Spider):
    """
    A spider to scrape and parse CS:GO past matches data.

    Fetches match details including teams, scores, and dates.
    """

    name: str = "CSpMatchesSpider"
    
    custom_settings: dict[str, Any] = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSPastMatchesPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the spider with provided arguments."""
        super().__init__(*args, **kwargs)
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)
        self.base_url: str = "https://escorenews.com"

    def start_requests(self) -> Iterator[Request]:
        """
        Start the spider by issuing requests to match listing pages.

        Yields:
            Request: Initial requests to start crawling.

        """
        for page_num in range(1, 5):
            url = f"{self.base_url}/en/csgo/matches?s2={page_num}"
            yield Request(url=url, callback=self.parse)

    def parse(self, response: Response, **kwargs: Any) -> Iterator[CSPMatchesItem]:
        """
        Parse match listing pages and extract match data.

        Args:
            response (Response): The response containing the matches listing.
            **kwargs: Additional keyword arguments.

        Yields:
            CSPMatchesItem: Processed match data item.

        """
        for match in response.css("div#matches_s2.flex-table a.article.v_gl704"):
            match_data = self._extract_match_data(match)
            
            loader = CSPMatchesItemLoader(item=CSPMatchesItem())
            for field, value in match_data.items():
                loader.add_value(field, value)
                
            yield loader.load_item()

    def _extract_match_data(self, match: Response) -> dict[str, str]:
        """
        Extract match information from the response.

        Args:
            match (Response): The match section of the response.

        Returns:
            dict: Dictionary containing match data.
            
        """
        score = css_mutator("div.teams div.score span.type0::text", match).split(":")
        full_match_url = urljoin(base=self.base_url, url=match.css("::attr(href)").get())
        team_names = extract_teams(full_match_url)
        match_name = " vs ".join([team.strip() for team in team_names])
        return {
            "date": match.css("i.sct::attr(datetime)").get(),
            "match_name": match_name,
            "external_id": full_match_url.split("-")[-1],
            "team1": match.css("div.teams span:nth-child(1) b::text").get(),
            "team1_score": score[0].strip(),
            "team2_score": score[1].strip(),
            "team2": match.css("div.teams span:nth-child(3) b::text").get(),
            
        }
