import os
import random
import re
from html import unescape
from typing import Any
from unicodedata import normalize
from urllib.parse import urljoin

from dotenv import load_dotenv
from scrapy import Request, Spider
from scrapy.http import Response

from webnews_parser.settings import PLAYWRIGHT_ARGS, PLAYWRIGHT_USER_AGENTS

from ..items import CSLSMatchesTournamentsItem
from ..utils.spider_utils import (
    clean_text,
    css_mutator,
    xpath_mutator,
    xpath_mutator_all,
)


class CSlsMatchesTournamentsSpider(Spider):
    name = "CSlsMatchesTournamentsSpider"
    base_url = "https://escorenews.com"
    load_dotenv(".env", override=True)
    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "webnews_parser.middlewares.PatchrightMiddleware": 542,
            "webnews_parser.middlewares.TooManyRequestsRetryMiddleware": 543,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
        },
        "ITEM_PIPELINES": {
            "webnews_parser.pipelines.CSLSMLiveMatchesAndTournamentPostgresPipeline": 100,
        },
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 0.5,
        "HTTPCACHE_ENABLED": False,
        "USER_AGENT": None,
        "LOG_LEVEL": "INFO",
        "COOKIES_ENABLED": False,
        "REACTOR_THREADPOOL_MAXSIZE": 20,
        "DB_URL": os.getenv("DB_URL"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_tournament_urls = set()
        self.blocked_resources = ["image", "font", "stylesheet"]
        self.browser_args = PLAYWRIGHT_ARGS
        self.user_agent = random.choice(PLAYWRIGHT_USER_AGENTS)

    def start_requests(self):
        url_array = ["https://escorenews.com/en/csgo/matches?s1=" + str(page_num) for page_num in range(1, 3)]
        for url in url_array:
            yield Request(url, callback=self.parse)

    def parse(self, response: Response, **kwargs: Any) -> Any:
        table_1 = response.css("div#matches_s1.flex-table")
        matches = table_1.css("a.article.type1") + table_1.css("a.article") + table_1.css("a.article.v_gl704.type1") \
                  + table_1.css("a.article.type0.v_gl704")
        for match in matches:
            scheduled_match_url = match.css("::attr(href)").get()
            scheduled_match_begin_time = css_mutator("div.time i.sct::attr(datetime)", match)
            if scheduled_match_url.count("tbd") < 2:
                placeholder_dict = {"match_begin_time": scheduled_match_begin_time,
                                    "match_url": scheduled_match_url}
                yield Request(url=urljoin(base="https://escorenews.com/", url=scheduled_match_url),
                              callback=self.parse_match_page,
                              cb_kwargs=placeholder_dict,
                              )

    def parse_match_page(self, response: Response, **kwargs: Any) -> Any:

        tournament_link = urljoin(base=self.base_url, url=response.xpath("//h1//a/@href").get())
        tournament_info = xpath_mutator('//div[contains(@class,"hh")]/span/text()', response).split("•")
        tournament_format = tournament_info[-2].strip() if tournament_info != [""] else ""
        tournament_stage = tournament_info[-3].strip() if tournament_info != [""] else ""
        pretty_teams = response.xpath('//div[contains(@class, "teams-on-live")]//h2/text()').getall()
        pretty_match_name = " - ".join([team.strip() for team in pretty_teams])
        teams = response.xpath('//div[contains(@class, "teams-on-live")]/span/a/@href').getall()
        teams = [team.split("/")[-1] for team in teams]
        teams_logo_links = tuple(urljoin(base=self.base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]//picture//img/@src').getall())
        teams_page_links = tuple(urljoin(base=self.base_url, url=_) for _ in
                                 response.xpath('//div[contains(@class, "teams-on-live")]/span/a/@href').getall())
        if not teams_logo_links:
            teams_logo_links = ("", "")
        if not teams_page_links:
            teams_page_links = ("", "")
        if not teams:
            teams = ("", "")
        match_format = xpath_mutator('//div[contains(@class, "score")]/h3/text()', response)
        match_format = match_format.strip()[match_format.find("B"):]
        match_status = response.xpath('//div[contains(@class, "score")]//b/text()').get()
        if match_status == "Match did not start":
            match_status = "scheduled"
        elif match_status == "Match started":
            match_status = "live"
        match_score = response.xpath('//div[contains(@class, "score")]/span[contains(@class, "live")]/text()').getall()
        if not match_score:
            match_score = ("", "")

        def TBD_team_page_boolean(team_pos: int) -> bool:
            TBD_team_page_linkv1 = "https://escorenews.com/en/csgo/team/players"
            TBD_team_page_linkv2 = "javascript:;"
            return (teams_page_links[team_pos] != TBD_team_page_linkv1
                    and teams_page_links[team_pos] != TBD_team_page_linkv2)

        def TBD_team_logo_boolean(team_pos: int) -> bool:
            TBD_team_logo_link = "https://escorenews.com/media/logo/not.svg"
            return teams_logo_links[team_pos] != TBD_team_logo_link

        match_streams = {}
        twitch_url = "https://www.twitch.tv/"
        for stream_info in response.css("div.os-padding div.si"):
            stream_name = css_mutator("b::text", stream_info).strip()
            stream_author_and_language = css_mutator("u::text", stream_info).strip().split()
            stream_author = stream_author_and_language[-1]
            stream_language = stream_author_and_language[-2]
            stream_viewers = stream_info.css("u i::text").get()
            streamer_twitch_name = stream_info.css("::attr(data-eng)").get()
            stream_link = urljoin(base=twitch_url, url=streamer_twitch_name) if streamer_twitch_name else ""
            match_streams[stream_name] = (stream_author, stream_language, stream_viewers, stream_link)

        placeholder_dict = {"match_info": {
            "tournament_format": tournament_format,
            "tournament_stage": tournament_stage,
            "match_format": match_format,
            "match_status": match_status,

            "team1_page_link": teams_page_links[0]
            if TBD_team_page_boolean(0) or TBD_team_logo_boolean(0) else "TBD",

            "team1_logo_link": teams_logo_links[0]
            if TBD_team_logo_boolean(0) or TBD_team_page_boolean(0) else "TBD",

            "team1": teams[0] if teams[0] not in ("javascript:;", "") else "TBD",
            "team1_score": match_score[0],
            "team2_score": match_score[1],
            "team2": teams[-1] if teams[1] not in ("javascript:;", "") else "TBD",

            "team2_logo_link": teams_logo_links[-1]
            if TBD_team_logo_boolean(1) or TBD_team_page_boolean(1) else "TBD",

            "team2_page_link": teams_page_links[-1]
            if TBD_team_page_boolean(1) or TBD_team_logo_boolean(1) else "TBD",

            "pretty_match_name": pretty_match_name,

            "match_begin_time": response.cb_kwargs.get("match_begin_time"),
            "match_streams": match_streams}
        }

        if placeholder_dict.get("match_info").get("team1") != "TBD" and placeholder_dict.get("match_info").get("team2") != "TBD":
            if tournament_link != self.base_url:
                if response.url in self.visited_tournament_urls:
                    data = CSLSMatchesTournamentsItem()
                    data.update(placeholder_dict.get("match_info"))
                    data["has_tournament_info"] = False
                    yield data
                else:
                    yield Request(url=tournament_link,
                                  callback=self.parse_tournament_page,
                                  cb_kwargs=placeholder_dict,
                                  dont_filter=True)
            else:
                data = CSLSMatchesTournamentsItem()
                data.update(placeholder_dict.get("match_info"))
                data["has_tournament_info"] = False
                yield data

    def parse_tournament_page(self, response: Response, **kwargs: Any) -> Any:
        self.visited_tournament_urls.add(response.url)
        bool_location_identifier = response.xpath(
            '//table[contains(@class, "tinfo table table-sm")]/tbody/tr[6]/td/span').get()
        tournament_name = response.css("div.hh h1::text").get()
        tournament_location = xpath_mutator(
            '//table[contains(@class, "tinfo table table-sm")]/tbody/tr[6]/td/text()', response).strip()
        tournament_logo_link = urljoin(self.base_url, response.css("div.tourlogo picture img::attr(src)").get())
        tournmaent_description_raw = (
            xpath_mutator_all("//div[@class='tourdescription']//text()", response))
        tournament_description_fixed = ""
        for text in tournmaent_description_raw:
            stripped_text = text.strip()
            if stripped_text[0] != ".":
                tournament_description_fixed += " " + stripped_text
            else:
                tournament_description_fixed += stripped_text
        tournmaent_description = clean_text(unescape(tournament_description_fixed))
        tournament_start_date = xpath_mutator('//table[contains(@class, "tinfo table table-sm")]'
                                                    '/tbody/tr[3]/td[contains(@class, "sct")]/@datetime',
                                                    response).split(" ")[0]
        tournament_prize_pool = xpath_mutator(
            '//table[contains(@class, "tinfo table table-sm")]/tbody/tr[4]/td[contains(@class, "scm")]/text()',
            response)
        if not tournament_location:
            tournament_location_alt = xpath_mutator(
                "/html/body/div[1]/main/div[3]/div/div/div[1]/div/table/tbody/tr[5]/td/text()", response).strip()
            pattern = re.compile(r"x\d$")
            if not pattern.search(tournament_location_alt):
                tournament_location = tournament_location_alt
        if not tournament_prize_pool:
            tournament_prize_pool = css_mutator(
                "body > div.wrap > main > div.page-topper > div > div > div.col-lg-4.order-last > div > table > tbody > tr:nth-child(3) > td::text", response)
            tournament_location = css_mutator(
                "body > div.wrap > main > div.page-topper > div > div > div.col-lg-4.order-last > div > table > tbody > tr:nth-child(5) > td::text", response)

        data_to_save = {"tournament_name": tournament_name,
                        "tournament_location": tournament_location if not bool_location_identifier else "",
                        "tournament_logo_link": tournament_logo_link
                        if tournament_logo_link != self.base_url else "",
                        "tournament_description": tournmaent_description,
                        "tournament_start_date": tournament_start_date,
                        "tournament_prize_pool": tournament_prize_pool,
                        }
        data_ls_matches = CSLSMatchesTournamentsItem()
        data_ls_matches.update(data_to_save)
        data_ls_matches.update(response.cb_kwargs.get("match_info"))
        data_ls_matches["has_tournament_info"] = True if tournament_name else False
        yield data_ls_matches

