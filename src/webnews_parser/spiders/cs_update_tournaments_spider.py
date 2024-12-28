import random

from scrapy import Request, Spider

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS
from webnews_parser.utils.db_utils import get_matches_with_empty_tournaments

from ..items import CSUpdateTournamentsItem
from ..loaders import CSUpdateTournamentsLoader


class CSUpdateTournamentsSpider(Spider):
    name = "CSUpdateTournamentsSpider"
    custom_settings = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSUpdateTournamentsPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://escorenews.com"
        self.blocked_resources = ["image", "font", "stylesheet"]
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)

    def start_requests(self):
        matches = get_matches_with_empty_tournaments()
        for match in matches:
            if match.tournament_url:
                yield Request(match.tournament_url, 
                            callback=self.parse_tournament,
                            cb_kwargs={"match_id": match.match_id},
                            meta={"delay": 4})

    def parse_tournament(self, response, match_id):
        """Parse tournament details and yield data for updating."""
        loader = CSUpdateTournamentsLoader(
            item=CSUpdateTournamentsItem(),
            response=response
        )
        
        loader.add_value("match_id", match_id)
        loader.add_css("tournament_name", "div.hh h1::text")
        loader.add_xpath(
            "tournament_location",
            "//th[contains(text(),'Dates')]/parent::*/td/text()"
        )
        loader.add_css("tournament_logo_link", "div.tourlogo picture img::attr(src)")
        
        # Handle description
        description_texts = response.xpath("//div[@class='tourdescription']//text()").getall()
        description = " ".join(text.strip() for text in description_texts if text.strip())
        loader.add_value("tournament_description", description)
        
        # Add start date and prize pool
        loader.add_xpath(
            "tournament_start_date",
            "//th[contains(text(),'Dates')]/parent::*/td/@datetime"
        )
        loader.add_xpath(
            "tournament_prize_pool",
            "//th[contains(text(),'Prize Pool')]/parent::*/td/text()"
        )
        
        yield loader.load_item()
