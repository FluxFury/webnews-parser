import random
from collections.abc import AsyncGenerator
from re import A
from typing import Any
from urllib.parse import urljoin

import scrapy
from scrapy.exceptions import CloseSpider

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSCreateLiveScheduledMatchesItem
from ..loaders import CSCreateLiveScheduledMatchesLoader
from ..utils.db_utils import sync_poll_latest_match
from ..utils.spider_utils import css_mutator, extract_teams


class CSCreateLiveScheduledMatchesSpider(scrapy.Spider):
    name = "CSCreateLiveScheduledMatchesSpider"
    custom_settings = {  # noqa: RUF012
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSCreateLiveScheduledMatchesPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_match = None
        self.blocked_resources = ["image", "font", "stylesheet"]
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)

    def start_requests(self):
        self.last_match = sync_poll_latest_match()
        last_page_num = 3
        urls = [
            f"https://escorenews.com/en/csgo/matches?s1={page_num}"
            for page_num in range(last_page_num, 0, -1)
        ]
        page_num = 3
        for url in urls:
            yield scrapy.Request(url, callback=self.parse, meta={"page_num": page_num})
            page_num -= 1

    async def parse(self, response: scrapy.http.TextResponse) -> AsyncGenerator[Any]:
        table = response.css("div#matches_s1.flex-table")
        matches = table.css("a.article.type1") + table.css("a.article")

        for match_element in matches:
            match_url = match_element.css("::attr(href)").get()
            full_match_url = urljoin(base="https://escorenews.com", url=match_url)
            external_id = match_url.split("-")[-1]

            team_names = extract_teams(full_match_url)
            match_name = " vs ".join([team.strip() for team in team_names])
            match_status = self._get_match_status(match_element)

            if match_url and match_url.count("tbd") < 2:
                loader = CSCreateLiveScheduledMatchesLoader(
                    item=CSCreateLiveScheduledMatchesItem(),
                    selector=match_element,
                    response=response,
                )

                loader.add_value("match_url", full_match_url)
                loader.add_css(
                    "planned_start_datetime", "div.time i.sct::attr(datetime)"
                )
                loader.add_value("match_name", match_name)
                loader.add_value("external_id", external_id)
                loader.add_value("match_status", match_status)
                yield loader.load_item()

    def _get_match_status(self, response):
        status = response.xpath('//a[contains(@class, "article type1")]').get()
        status_alt = response.xpath(
            '//a[contains(@class, "article v_gl704 type1")]'
        ).get()
        if status or status_alt:
            return "live"
        return "scheduled"
